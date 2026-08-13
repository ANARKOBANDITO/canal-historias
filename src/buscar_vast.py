"""
buscar_vast.py

Busca instancias GPU disponibles en Vast.ai usando la API publica de ofertas,
aplicando los filtros criticos del proyecto para evitar el bug de CUDA que
rompio RunPod (driver >= 580 + nvidia-uvm roto):

    - driver_version < 580   (elimina la causa raiz del fallo)
    - cuda_max_good  >= 12.8 (compatible con torch 2.6.0 + CUDA 12.4)

No requiere API key ni credito: la busqueda es publica. Se ejecuta ANTES de
alquilar nada para confirmar que hay instancias validas disponibles.

Uso (desde la raiz del proyecto):
    python src/buscar_vast.py                          # 3090/4090/A6000 validas
    python src/buscar_vast.py --gpu "RTX 4090"         # una GPU especifica
    python src/buscar_vast.py --max-precio 0.20        # tope de $/hr
    python src/buscar_vast.py --top 10                 # cuantas mostrar
"""

import argparse
import json
import urllib.parse
import urllib.request

URL_BUNDLES = "https://console.vast.ai/api/v0/bundles/"

# GPUs razonables para el pipeline (24GB+ para chatterbox/whisper/video)
GPUS_DEFECTO = [
    "RTX 3090",
    "RTX 3090 Ti",
    "RTX 4090",
    "RTX A5000",
    "RTX A6000",
    "RTX 4000 Ada Generation",
    "RTX 4080",
]


def _escape_valor(v):
    """Escapa el valor de un query de la API de Vast (el JSON va URL-encoded)."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return json.dumps(str(v))


def _query_string(filtros: dict, limit: int) -> str:
    """Construye la parte ?q=... a partir de un dict de filtros."""
    return urllib.parse.urlencode({"q": json.dumps(filtros)})


def buscar_instancias(gpus: list[str], max_precio: float, tipo: str = "on-demand",
                      limit: int = 50) -> list[dict]:
    """Consulta la API publica de ofertas con los filtros del proyecto.

    Devuelve una lista de ofertas con los campos utiles para decidir.
    """
    filtros = {
        "verified": {"eq": True},
        "rentable": {"eq": True},
        "type": tipo,
        "gpu_name": {"in": gpus},
        "num_gpus": {"gte": 1},
        "driver_version": {"lt": "580.0.0"},   # causa raiz del fallo RunPod
        "cuda_max_good": {"gte": "12.8"},
        "direct_port_count": {"gte": 1},
        "dph_total": {"lte": max_precio},
        "order": [["dph_total", "asc"]],
        "limit": limit,
    }
    url = URL_BUNDLES + "?" + _query_string(filtros, limit)
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("offers", [])


def _formatear_oferta(o: dict) -> str:
    precio = o.get("dph_total", 0) or 0
    vram = (o.get("gpu_ram", 0) or 0) / 1024 if o.get("gpu_ram") else 0
    host = o.get("host_id", "?")
    datacenter = o.get("geolocation", "?")
    return (
        f"  #{o['id']:<10} {o.get('gpu_name','?'):<10} "
        f"${precio:.3f}/hr | driver={o.get('driver_version','?')} "
        f"cuda={o.get('cuda_max_good','?')} | {vram:.0f}GB | {datacenter}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Busca instancias GPU en Vast.ai con driver < 580 y cuda >= 12.8.")
    parser.add_argument("--gpu", help="Filtrar por GPU especifica (ej. 'RTX 4090')")
    parser.add_argument("--max-precio", type=float, default=0.30,
                        help="Tope de precio en $/hr (default 0.30)")
    parser.add_argument("--top", type=int, default=15, help="Cuantas ofertas mostrar")
    parser.add_argument("--tipo", choices=["on-demand", "interruptible"],
                        default="on-demand", help="Tipo de instancia")
    parser.add_argument("--json", action="store_true",
                        help="Salida JSON completa (para consumo por otro script)")
    args = parser.parse_args()

    gpus = [args.gpu] if args.gpu else GPUS_DEFECTO

    print(f"Buscando instancias en Vast.ai...")
    print(f"  GPUs: {', '.join(gpus)}")
    print(f"  Filtros: driver < 580, cuda_max_good >= 12.8, max ${args.max_precio:.2f}/hr")
    print()

    ofertas = buscar_instancias(gpus, args.max_precio, tipo=args.tipo)
    if not ofertas:
        print("No se encontraron ofertas validas con esos filtros.")
        print("Sugerencias: subir --max-precio, ampliar la lista de GPUs, o")
        print("usar --tipo interruptible (mas baratas, pueden pausarse).")
        return

    validas = [o for o in ofertas if o.get("driver_version") < "580.0.0"]
    print(f"Ofertas encontradas: {len(ofertas)} (driver < 580: {len(validas)})")
    print()

    if args.json:
        campos = [
            "id", "gpu_name", "gpu_ram", "driver_version", "cuda_max_good",
            "dph_total", "dph_disk", "disk_space", "geolocation", "num_gpus",
            "inet_down", "inet_up", "reliability",
        ]
        resumen = []
        for o in ofertas[: args.top]:
            resumen.append({c: o.get(c) for c in campos})
        print(json.dumps(resumen, ensure_ascii=False, indent=2))
        return

    for o in ofertas[: args.top]:
        print(_formatear_oferta(o))

    print()
    print(f"\nPara alquilar una: python src/provisionar_vast.py --alquilar <ID>")
    print("(requiere VAST_AI_API_KEY configurada y credito en la cuenta)")


if __name__ == "__main__":
    main()
