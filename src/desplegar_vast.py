"""
desplegar_vast.py

Sube el codigo del proyecto y los datos necesarios a una instancia Vast.ai
ya provisionada, para ejecutar el pipeline GPU alli. Usa scp sobre SSH.

Sube:
    src/                          (todo el codigo)
    output/guiones_listos/        (los guiones)
    storage/voces/                (referencias de voz para Chatterbox)
    storage/raw_gameplay/         (gameplay para el fondo de video)

Uso (desde la raiz del proyecto):
    python src/desplegar_vast.py --instancia 47425120 --clave "ruta\\a\\la\\clave"
    python src/desplegar_vast.py --instancia 47425120 --clave "ruta\\a\\la\\clave" --solo-codigo
"""

import argparse
import subprocess
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src"))
from provisionar_vast import _datos_instancia  # noqa: E402

# Directorios locales -> remoto
RUTAS = [
    ("src", "/root/canal-historias/src"),
    ("output/guiones_listos", "/root/canal-historias/output/guiones_listos"),
    ("storage/voces", "/root/canal-historias/storage/voces"),
    ("storage/gameplay_lite", "/root/canal-historias/storage/gameplay_lite"),
    ("storage/fotos", "/root/canal-historias/storage/fotos"),
    ("storage/avatar", "/root/canal-historias/storage/avatar"),
]

RUTAS_CODIGO = [
    ("src", "/root/canal-historias/src"),
]


def _scp(clave: str, host: str, port: int, local: str, remoto: str) -> int:
    cmd = [
        "scp", "-r", "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-i", clave, "-P", str(port),
        local, f"root@{host}:{remoto}",
    ]
    print(f"  scp {local} -> {remoto}")
    return subprocess.call(cmd)


def main():
    parser = argparse.ArgumentParser(description="Despliega codigo y datos a una instancia Vast.ai.")
    parser.add_argument("--instancia", type=int, required=True, help="ID de la instancia")
    parser.add_argument("--clave", required=True, help="Clave privada SSH")
    parser.add_argument("--solo-codigo", action="store_true", help="Subir solo src/")
    args = parser.parse_args()

    inst = _datos_instancia(args.instancia)
    host, port = inst["ssh_host"], inst["ssh_port"]
    print(f"Desplegando a {host}:{port} (instancia {args.instancia})...")

    rutas = RUTAS_CODIGO if args.solo_codigo else RUTAS
    ok = True
    for local, remoto in rutas:
        rc = _scp(args.clave, host, port, local, remoto)
        if rc != 0:
            ok = False
            print(f"  [X] fallo: {local}")
        else:
            print(f"  [OK] {local}")

    if not ok:
        raise SystemExit("Hubo errores en el despliegue.")

    print("\nDespliegue completado. Siguiente paso en el pod:")
    print("  cd /root/canal-historias && python src/pipeline_gpu.py <guion> --motor chatterbox --idioma es")


if __name__ == "__main__":
    main()
