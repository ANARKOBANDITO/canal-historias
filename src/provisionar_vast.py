"""
provisionar_vast.py

Orquestador del ciclo completo de vida de una instancia GPU en Vast.ai:
buscar -> alquilar -> esperar boot -> smoke test CUDA -> instalar deps
-> probar Chatterbox -> reportar. Y al terminar: destruir (o conservar).

Regla de oro (aprendida con RunPod): el smoke test de CUDA es OBLIGATORIO
antes de instalar nada. Si cuInit != 0, la instancia se destruye al instante
y se pierde solo ~$0.01 + unos minutos, no horas.

Requisitos:
    - VAST_AI_API_KEY en el entorno (cuenta con credito cargado)
    - Clave SSH publica registrada en la cuenta de Vast.ai (Account Settings)
      para poder conectarse por SSH. La clave privada se pasa con --clave.

Uso (desde la raiz del proyecto):
    python src/provisionar_vast.py --buscar
    python src/provisionar_vast.py --alquilar 32302041 --clave "$HOME/.ssh/id_ed25519"
    python src/provisionar_vast.py --esperar 12345678
    python src/provisionar_vast.py --smoke-test 12345678 --clave "..."
    python src/provisionar_vast.py --instalar 12345678 --clave "..."
    python src/provisionar_vast.py --probar-chatterbox 12345678 --clave "..."
    python src/provisionar_vast.py --provisionar --clave "..."   # todo en uno
    python src/provisionar_vast.py --destruir 12345678
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

URL_API = "https://console.vast.ai"

# Imagen con torch 2.6.0 preinstalado (requisito de chatterbox-tts 0.1.7)
IMAGEN = "pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime"
DISCO_GB = 60  # margen para modelos + salidas

GPUS_DEFECTO = [
    "RTX 3090", "RTX 3090 Ti", "RTX 4090", "RTX A5000", "RTX A6000",
    "RTX 4000 Ada Generation", "RTX 4080",
]

DEPENDENCIAS = (
    "pip install --no-cache-dir chatterbox-tts faster-whisper "
    "edge-tts soundfile pillow sentence-transformers "
    "qwen-vl-utils bitsandbytes diffusers transformers"
)

SMOKE_TEST = (
    "python3 -c \"import ctypes; c=ctypes.CDLL('libcuda.so.1'); "
    "r=c.cuInit(0); print('CUINIT_RESULT=' + str(r)); raise SystemExit(r)\""
)

TEST_CHATTERBOX = r"""
set -e
export HF_HUB_DISABLE_XET=1
python3 - <<'PY'
import torch
print("TORCH_CUDA_AVAILABLE=", torch.cuda.is_available())
print("GPU=", torch.cuda.get_device_name(0))
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
print("cargando modelo...")
model = ChatterboxMultilingualTTS.from_pretrained(device=torch.device("cuda"))
for idioma, frase in [
    ("es", "Esta es una prueba de la voz del canal en espanol."),
    ("en", "This is a channel voice test in English."),
    ("pt", "Este e um teste de voz do canal em portugues."),
]:
    wav = model.generate(text=frase, language_id=idioma)
    print(f"OK idioma={idioma} tipo={type(wav).__name__}")
print("CHATTERBOX_OK")
PY
"""


# ─────────────────────────────────────────────────────────────
#  API helpers
# ─────────────────────────────────────────────────────────────

def _api_key() -> str:
    key = os.environ.get("VAST_AI_API_KEY")
    if not key:
        raise SystemExit(
            "VAST_AI_API_KEY no configurada.\n"
            "1) Crea la key en https://cloud.vast.ai/manage-keys/\n"
            "2) Configurala como variable de entorno VAST_AI_API_KEY."
        )
    return key


def _api(method: str, path: str, body: dict | None = None) -> dict:
    key = _api_key()
    req = urllib.request.Request(URL_API + path, method=method)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    datos = json.dumps(body).encode("utf-8") if body is not None else None
    try:
        with urllib.request.urlopen(req, data=datos, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"ERROR API {e.code} {path}: {msg}") from e


# ─────────────────────────────────────────────────────────────
#  SSH helpers
# ─────────────────────────────────────────────────────────────

def _ssh(host: str, port: int, clave: str, comando: str, reintentos: int = 6,
         pausa: float = 10.0) -> int:
    """Ejecuta un comando remoto por SSH con la clave privada dada.

    Reintenta mientras SSH siga arrancando ('Connection refused'): Vast reporta
    'running' antes de que sshd este aceptando conexiones. NO reintenta ante
    'Permission denied' (clave mal registrada) ni ante un smoke test que falla.
    """
    base = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ConnectTimeout=15",
        "-i", clave, "-p", str(port),
        f"root@{host}",
    ]
    for intento in range(1, reintentos + 1):
        print(f"  SSH {host}:{port} ({intento}/{reintentos}) -> {comando[:60]}...")
        proc = subprocess.run(
            base + [comando], capture_output=True, text=True,
            encoding="utf-8", errors="replace")
        salida = (proc.stdout or "") + (proc.stderr or "")
        for linea in salida.splitlines():
            try:
                print(f"      {linea}")
            except UnicodeEncodeError:
                print(f"      {linea.encode('ascii', 'replace').decode('ascii')}")
        if proc.returncode == 0:
            return 0
        if "Connection refused" in salida and intento < reintentos:
            time.sleep(pausa)
            continue
        return proc.returncode
    return 1


def _datos_instancia(inst_id: int) -> dict:
    # El detalle individual solo responde en v0; la lista solo en v1.
    data = _api("GET", f"/api/v0/instances/{inst_id}/")
    inst = data.get("instances", {})
    if isinstance(inst, dict) and "actual_status" in inst:
        return inst
    if isinstance(inst, list) and inst:
        return inst[0]
    return {}


# ─────────────────────────────────────────────────────────────
#  Pasos
# ─────────────────────────────────────────────────────────────

def buscar(top: int = 15, max_precio: float = 0.30) -> None:
    filtros = {
        "verified": {"eq": True},
        "rentable": {"eq": True},
        "type": "on-demand",
        "gpu_name": {"in": GPUS_DEFECTO},
        "num_gpus": {"gte": 1},
        "driver_version": {"lt": "580.0.0"},
        "cuda_max_good": {"gte": "12.8"},
        "direct_port_count": {"gte": 1},
        "dph_total": {"lte": max_precio},
        "order": [["dph_total", "asc"]],
        "limit": top,
    }
    url = URL_API + "/api/v0/bundles/?" + urllib.parse.urlencode({"q": json.dumps(filtros)})
    with urllib.request.urlopen(url, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    ofertas = data.get("offers", [])
    print(f"Ofertas validas (driver<580, cuda>=12.8, <=${max_precio}/hr): {len(ofertas)}")
    for o in ofertas:
        vram = (o.get("gpu_ram") or 0) / 1024
        print(f"  #{o['id']:<10} {o.get('gpu_name','?'):<12} "
              f"${o.get('dph_total',0):.3f}/hr | driver={o.get('driver_version')} "
              f"cuda={o.get('cuda_max_good')} | {vram:.0f}GB | {o.get('geolocation','?')}")


def alquilar(offer_id: int) -> int:
    print(f"Alquilando oferta #{offer_id}...")
    body = {
        "image": IMAGEN,
        "disk": DISCO_GB,
    }
    data = _api("PUT", f"/api/v0/asks/{offer_id}/", body)
    if not data.get("success"):
        raise SystemExit(f"No se pudo alquilar: {data}")
    inst_id = data["new_contract"]
    print(f"Instancia creada: {inst_id}")
    print(f"  (este es el ID para --esperar/--smoke-test/... )")
    return inst_id


def esperar(inst_id: int, timeout: int = 600) -> dict:
    print(f"Esperando boot de la instancia {inst_id}...")
    inicio = time.time()
    while time.time() - inicio < timeout:
        inst = _datos_instancia(inst_id)
        estado = inst.get("actual_status")
        if estado == "running":
            print(f"  Instancia RUNNING en {int(time.time()-inicio)}s")
            print(f"  SSH: {inst.get('ssh_host')}:{inst.get('ssh_port')}")
            return inst
        if estado in ("exited", "unknown", "offline"):
            raise SystemExit(f"Instancia en estado malo: {estado}. Destruir y reintentar.")
        time.sleep(10)
    raise SystemExit(f"Timeout esperando boot de {inst_id}. Destruir y reintentar.")


def smoke_test(inst_id: int, clave: str) -> None:
    inst = esperar(inst_id, timeout=300)
    print("\n[1/3] Smoke test CUDA (obligatorio, ~$0.01 si falla)...")
    rc = _ssh(inst["ssh_host"], inst["ssh_port"], clave, SMOKE_TEST)
    if rc != 0:
        print("  [X] El smoke test no paso. Revisa el error de arriba:")
        print("      - 'Permission denied (publickey)' -> la clave SSH no esta")
        print("        registrada en la cuenta Vast.ai (Account > SSH Keys).")
        print("      - 'CUINIT_RESULT != 0' -> instancia rota (mismo sintoma")
        print("        que RunPod). Destruyendo y sugiriendo otra oferta...")
        destruir(inst_id)
        raise SystemExit("Smoke test fallo. Corrige el error y reintenta con otra oferta.")
    print("  [OK] cuInit == 0 -> CUDA funciona en esta instancia.\n")


def instalar(inst_id: int, clave: str) -> None:
    inst = _datos_instancia(inst_id)
    if inst.get("actual_status") != "running":
        inst = esperar(inst_id, timeout=300)
    print("\n[2/3] Instalando dependencias (chatterbox-tts, whisper, ...)...")
    print("  Esto puede tardar 2-5 min en descargar modelos...")
    rc = _ssh(inst["ssh_host"], inst["ssh_port"], clave, DEPENDENCIAS)
    if rc != 0:
        raise SystemExit("Fallo la instalacion de dependencias.")
    print("  [OK] Dependencias instaladas.\n")


def probar_chatterbox(inst_id: int, clave: str) -> None:
    inst = _datos_instancia(inst_id)
    if inst.get("actual_status") != "running":
        inst = esperar(inst_id, timeout=300)
    print("\n[3/3] Probando Chatterbox (1 frase por idioma, voice cloning local)...")
    rc = _ssh(inst["ssh_host"], inst["ssh_port"], clave, TEST_CHATTERBOX)
    if rc != 0:
        raise SystemExit("Fallo la prueba de Chatterbox.")
    print("\n[OK] Chatterbox listo. Instancia lista para el pipeline GPU completo.")


def provisionar(clave: str, max_precio: float, conservar: bool) -> None:
    print("=== PROVISIONAMIENTO COMPLETO DE INSTANCIA GPU ===")
    filtros = {
        "verified": {"eq": True},
        "rentable": {"eq": True},
        "type": "on-demand",
        "gpu_name": {"in": GPUS_DEFECTO},
        "num_gpus": {"gte": 1},
        "driver_version": {"lt": "580.0.0"},
        "cuda_max_good": {"gte": "12.8"},
        "direct_port_count": {"gte": 1},
        "dph_total": {"lte": max_precio},
        "order": [["dph_total", "asc"]],
        "limit": 1,
    }
    url = URL_API + "/api/v0/bundles/?" + urllib.parse.urlencode({"q": json.dumps(filtros)})
    with urllib.request.urlopen(url, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    ofertas = data.get("offers", [])
    if not ofertas:
        raise SystemExit(f"No hay ofertas validas a <=${max_precio}/hr. Usa --buscar.")
    oferta = ofertas[0]
    print(f"Oferta elegida: #{oferta['id']} {oferta.get('gpu_name')} "
          f"${oferta.get('dph_total',0):.3f}/hr")
    inst_id = alquilar(oferta["id"])
    try:
        smoke_test(inst_id, clave)
        instalar(inst_id, clave)
        probar_chatterbox(inst_id, clave)
        print(f"\n=== INSTANCIA {inst_id} LISTA PARA PRODUCCION ===")
        if not conservar:
            print("(--conservar no usado: destruyendo al terminar)")
            destruir(inst_id)
        else:
            print("Conservando instancia (--conservar). No olvides destruirla al terminar.")
    except Exception as e:
        print(f"\nError durante el provisionamiento: {e}")
        print("Destruyendo instancia para no acumular costo...")
        try:
            destruir(inst_id)
        except Exception:
            pass
        raise


def destruir(inst_id: int) -> None:
    print(f"Destruyendo instancia {inst_id}...")
    data = _api("DELETE", f"/api/v0/instances/{inst_id}/")
    print(f"  {data}")


def parar(inst_id: int) -> None:
    print(f"Deteniendo instancia {inst_id} (GPU pausada, disco sigue facturando)...")
    data = _api("PUT", f"/api/v0/instances/{inst_id}/", {"state": "stopped"})
    print(f"  {data}")


# ─────────────────────────────────────────────────────────────

def main():
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    parser = argparse.ArgumentParser(
        description="Orquesta el ciclo de vida de una instancia GPU en Vast.ai.")
    parser.add_argument("--buscar", action="store_true", help="Listar ofertas validas")
    parser.add_argument("--alquilar", type=int, metavar="OFFER_ID",
                        help="Alquilar una oferta por ID")
    parser.add_argument("--esperar", type=int, metavar="INSTANCE_ID",
                        help="Esperar a que la instancia este running")
    parser.add_argument("--smoke-test", type=int, metavar="INSTANCE_ID",
                        help="Correr el smoke test CUDA (cuInit)")
    parser.add_argument("--instalar", type=int, metavar="INSTANCE_ID",
                        help="Instalar dependencias (chatterbox-tts, whisper, ...)")
    parser.add_argument("--probar-chatterbox", type=int, metavar="INSTANCE_ID",
                        help="Probar Chatterbox 1 frase por idioma")
    parser.add_argument("--provisionar", action="store_true",
                        help="Todo en uno: alquilar + smoke + instalar + probar")
    parser.add_argument("--destruir", type=int, metavar="INSTANCE_ID",
                        help="Destruir la instancia (fin de facturacion)")
    parser.add_argument("--parar", type=int, metavar="INSTANCE_ID",
                        help="Pausar la instancia (GPU detenida)")
    parser.add_argument("--clave", help="Ruta a la clave privada SSH")
    parser.add_argument("--max-precio", type=float, default=0.30,
                        help="Tope de $/hr (default 0.30)")
    parser.add_argument("--conservar", action="store_true",
                        help="En --provisionar, no destruir al terminar")
    args = parser.parse_args()

    if args.buscar:
        buscar(top=15, max_precio=args.max_precio)
    elif args.alquilar:
        alquilar(args.alquilar)
    elif args.esperar:
        esperar(args.esperar)
    elif args.smoke_test:
        if not args.clave:
            raise SystemExit("Falta --clave para el smoke test.")
        smoke_test(args.smoke_test, args.clave)
    elif args.instalar:
        if not args.clave:
            raise SystemExit("Falta --clave para instalar.")
        instalar(args.instalar, args.clave)
    elif args.probar_chatterbox:
        if not args.clave:
            raise SystemExit("Falta --clave para probar Chatterbox.")
        probar_chatterbox(args.probar_chatterbox, args.clave)
    elif args.provisionar:
        if not args.clave:
            raise SystemExit("Falta --clave para --provisionar.")
        provisionar(args.clave, args.max_precio, args.conservar)
    elif args.destruir:
        destruir(args.destruir)
    elif args.parar:
        parar(args.parar)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
