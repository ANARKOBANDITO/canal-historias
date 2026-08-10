"""
buscar_gameplay.py

Busca videos de gameplay en YouTube usando yt-dlp (sin descargar) para
poblar data/gameplay_urls.txt con URLs reales y validas. Permite filtrar
por duracion y priorizar contenido de licencia libre ("no copyright"),
deduplicar contra las URLs ya presentes y guardar cada una con un
comentario de referencia (titulo + canal) para revisar antes de usar.

Uso (desde la raiz del proyecto):
    python src/buscar_gameplay.py "no copyright gameplay" "gameplay sin copyright"
    python src/buscar_gameplay.py --libre --guardar "free gameplay footage"
    python src/buscar_gameplay.py --cantidad 8 --min-duracion 300 --max-duracion 1800 "gameplay"

Sin --guardar solo lista candidatos. Con --libre descarta los que no
parecen de licencia libre segun el titulo/canal. IMPORTANTE: el script
solo encuentra candidatos; el usuario debe confirmar la licencia antes
de usarlos en un canal monetizado.
"""

import argparse
import re
import sys
from pathlib import Path

import yt_dlp

RUTA_TXT = Path("data/gameplay_urls.txt")
DURACION_MIN = 180    # 3 min
DURACION_MAX = 1800   # 30 min
PALABRAS_LIBRE = [
    "no copyright", "copyright free", "copyright-free", "royalty free",
    "royalty-free", "free to use", "free gameplay", "free footage",
    "sin copyright", "sin derechos", "libre de", "cc0",
    "creative commons", "stock footage",
]


def _buscar(query: str, cantidad: int) -> list[dict]:
    """Busca en YouTube y devuelve metadatos planos de los resultados."""
    opciones = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "extract_flat": "in_playlist",
    }
    with yt_dlp.YoutubeDL(opciones) as ydl:
        info = ydl.extract_info(f"ytsearch{cantidad}:{query}", download=False)

    resultados = []
    for entrada in info.get("entries", []):
        if not entrada:
            continue
        url = entrada.get("webpage_url") or entrada.get("url")
        duracion = entrada.get("duration")
        resultados.append({
            "titulo": (entrada.get("title") or "sin titulo").strip(),
            "canal": (entrada.get("channel") or entrada.get("uploader") or "desconocido").strip(),
            "duracion": duracion,
            "url": url,
        })
    return resultados


def _es_libre(entrada: dict) -> bool:
    """True si el titulo o canal sugiere contenido de licencia libre."""
    texto = f"{entrada['titulo']} {entrada['canal']}".lower()
    return any(palabra in texto for palabra in PALABRAS_LIBRE)


def _duracion_valida(duracion, min_s, max_s) -> bool:
    """True si la duracion esta dentro del rango pedido (None = desconocida)."""
    if duracion is None:
        return False
    return min_s <= duracion <= max_s


def _formatear_duracion(segundos) -> str:
    if not segundos:
        return "?"
    return f"{int(segundos) // 60}m{int(segundos) % 60:02d}"


def _leer_urls_existentes() -> set[str]:
    """Devuelve las URLs ya anotadas en el archivo .txt (sin comentarios)."""
    if not RUTA_TXT.exists():
        return set()
    urls = set()
    for linea in RUTA_TXT.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#"):
            urls.add(linea)
    return urls


def _agregar_al_txt(entradas: list[dict]) -> tuple[int, int]:
    """Agrega URLs nuevas al .txt con comentario de referencia.
    Devuelve (agregadas, omitidas por duplicado)."""
    existentes = _leer_urls_existentes()
    RUTA_TXT.parent.mkdir(exist_ok=True, parents=True)

    lineas = RUTA_TXT.read_text(encoding="utf-8").splitlines() if RUTA_TXT.exists() else []
    if not lineas:
        lineas = [
            "# Una URL de gameplay por linea (lineas con # son comentarios).",
            "# Las URLs deben ser de videos que tengas autorizacion/licencia para usar.",
            "# Uso: python src/descargar_gameplay.py data/gameplay_urls.txt",
        ]

    agregadas, omitidas = 0, 0
    for entrada in entradas:
        url = entrada["url"]
        if not url:
            omitidas += 1
            continue
        if url in existentes:
            omitidas += 1
            continue
        lineas.append(f"# {entrada['titulo']} - {entrada['canal']}")
        lineas.append(url)
        existentes.add(url)
        agregadas += 1

    lineas.append("")
    RUTA_TXT.write_text("\n".join(lineas), encoding="utf-8")
    return agregadas, omitidas


def main():
    parser = argparse.ArgumentParser(
        description="Busca gameplay en YouTube y opcionalmente lo agrega a data/gameplay_urls.txt.")
    parser.add_argument("consultas", nargs="+", help="Consulta(s) de busqueda (p.ej. 'no copyright gameplay')")
    parser.add_argument("--cantidad", type=int, default=6, help="Resultados por consulta (default 6)")
    parser.add_argument("--min-duracion", type=int, default=DURACION_MIN, help="Duracion minima en segundos")
    parser.add_argument("--max-duracion", type=int, default=DURACION_MAX, help="Duracion maxima en segundos")
    parser.add_argument("--libre", action="store_true",
                        help="Solo conservar resultados con indicios de licencia libre en titulo/canal")
    parser.add_argument("--guardar", action="store_true",
                        help="Agregar los candidatos validos a data/gameplay_urls.txt")
    args = parser.parse_args()

    candidatos = []
    for consulta in args.consultas:
        print(f"\nBuscando: {consulta}")
        try:
            resultados = _buscar(consulta, args.cantidad)
        except Exception as e:
            print(f"  ERROR al buscar '{consulta}': {e}")
            continue

        for entrada in resultados:
            if not entrada["url"]:
                continue
            if not _duracion_valida(entrada["duracion"], args.min_duracion, args.max_duracion):
                continue
            if args.libre and not _es_libre(entrada):
                continue
            candidatos.append(entrada)

    if not candidatos:
        print("\nSin candidatos validos. Probar otra consulta o relajar filtros.")
        sys.exit(1)

    print("\n" + "=" * 90)
    print(f"{len(candidatos)} candidato(s) validos:")
    for i, entrada in enumerate(candidatos, 1):
        etiqueta = "[LIBRE]" if _es_libre(entrada) else "[?]"
        print(f"{i:2d}. {etiqueta} {_formatear_duracion(entrada['duracion']):>6}  "
              f"{entrada['titulo'][:60]:<60} | {entrada['canal'][:24]}")
    print("=" * 90)

    if not args.guardar:
        print("\nPara guardar en data/gameplay_urls.txt: anadir --guardar")
        return

    agregadas, omitidas = _agregar_al_txt(candidatos)
    print(f"\nGuardado en {RUTA_TXT}: {agregadas} agregadas, {omitidas} omitidas (duplicadas/invalidas).")
    print("Revisar licencias antes de usar en canal monetizado.")


if __name__ == "__main__":
    main()
