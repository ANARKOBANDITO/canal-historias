"""
descargar_gameplay.py

Descarga videos de gameplay por URL usando yt-dlp y los guarda en
storage/raw_gameplay/. Soporta dos modos de entrada:
  - URL directa:  python src/descargar_gameplay.py "url"
  - Archivo .txt: python src/descargar_gameplay.py data/gameplay_urls.txt
    (una URL por linea, lineas con # son comentarios)

Usa aria2c (descargas paralelas) si esta disponible para acelerar la
descarga. Limita la resolucion a 1080p por defecto. Opcionalmente recorta
a N segundos con muestreo aleatorio.

Requisitos:
    pip install yt-dlp
    (opcional, para descarga rapida) aria2c instalado y en el PATH
"""

import argparse
import random
import re
import shutil
import subprocess
from pathlib import Path

import yt_dlp

from utilidades import normalizar_nombre

CARPETA_GAMEPLAY = Path("storage/raw_gameplay")
DURACION_OBJETIVO = 120  # segundos
UMBRAL_RECORTE = 300     # > 5 min = recortar
PREFIJO = "gameplay"
RESOLUCION_MAXIMA = 1080


def _tiene_aria2c() -> bool:
    return shutil.which("aria2c") is not None


def _opciones_ytdlp(calidad: int, nombre_salida: str) -> dict:
    """Construye las opciones de yt-dlp, con aria2c si esta disponible."""
    opciones = {
        "format": f"bestvideo[height<={calidad}]+bestaudio/best[height<={calidad}]",
        "merge_output_format": "mp4",
        "outtmpl": str(nombre_salida),
        "sponsorblock_remove": ["intro", "outro"],
        "ignoreerrors": True,
        "quiet": False,
        "noplaylist": True,
    }
    if _tiene_aria2c():
        opciones["external_downloader"] = "aria2c"
        opciones["external_downloader_args"] = {
            "aria2c": ["-x", "16", "-s", "16", "-k", "1M"]
        }
        print("  [aria2c] Descarga paralela activada (16 conexiones).")
    return opciones


def _obtener_duracion(ruta: Path) -> float:
    """Obtiene la duracion del video en segundos via ffprobe."""
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(ruta)],
        capture_output=True, text=True,
    )
    return float(proc.stdout.strip()) if proc.stdout.strip() else 0


def _siguiente_nombre() -> str:
    """Determina el siguiente nombre secuencial disponible."""
    CARPETA_GAMEPLAY.mkdir(exist_ok=True, parents=True)
    existentes = list(CARPETA_GAMEPLAY.glob(f"{PREFIJO}_*.mp4"))
    if not existentes:
        return f"{PREFIJO}_001.mp4"
    numeros = []
    for f in existentes:
        m = re.search(rf"{PREFIJO}_(\d+)\.mp4", f.name)
        if m:
            numeros.append(int(m[1]))
    return f"{PREFIJO}_{max(numeros) + 1:03d}.mp4"


def descargar(url: str, duracion: int = DURACION_OBJETIVO, calidad: int = 1080, sin_recorte: bool = False) -> Path:
    nombre_temp = CARPETA_GAMEPLAY / "_temp_download.mp4"
    nombre_final = CARPETA_GAMEPLAY / _siguiente_nombre()

    CARPETA_GAMEPLAY.mkdir(exist_ok=True, parents=True)

    print(f"  Descargando: {url[:80]}...")
    opciones = _opciones_ytdlp(calidad, nombre_temp)

    with yt_dlp.YoutubeDL(opciones) as ydl:
        ydl.download([url])

    if not nombre_temp.exists():
        raise RuntimeError("La descarga no produjo archivo")

    duracion_real = _obtener_duracion(nombre_temp)
    print(f"  Duracion: {duracion_real:.0f}s")

    if not sin_recorte and duracion_real > UMBRAL_RECORTE:
        inicio = random.uniform(duracion_real * 0.05, duracion_real * 0.85)
        print(f"  Recortando: inicio={inicio:.0f}s, duracion={duracion}s")
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(inicio), "-i", str(nombre_temp),
            "-t", str(duracion), "-c", "copy", str(nombre_final),
        ], check=True, capture_output=True)

        if nombre_temp.exists():
            nombre_temp.unlink()
    else:
        nombre_temp.rename(nombre_final)

    print(f"  Guardado: {nombre_final} ({nombre_final.stat().st_size / 1024:.0f} KB)")
    return nombre_final


def _leer_urls_desde_archivo(ruta_txt: Path) -> list[str]:
    """Lee URLs de un archivo .txt (una por linea, # = comentario)."""
    contenido = ruta_txt.read_text(encoding="utf-8")
    return [
        linea.strip()
        for linea in contenido.splitlines()
        if linea.strip() and not linea.strip().startswith("#")
    ]


def _resolver_entradas(argumentos: list[str]) -> list[str]:
    """Convierte los argumentos en lista de URLs. Si un argumento es un
    .txt existente, lee las URLs de ahi. Si no, se trata como URL directa."""
    urls = []
    for arg in argumentos:
        ruta = Path(arg)
        if ruta.exists() and arg.endswith(".txt"):
            urls.extend(_leer_urls_desde_archivo(ruta))
            print(f"  [{len(urls)} URL(s) leidas de {ruta}]")
        else:
            urls.append(arg)
    return urls


def main():
    parser = argparse.ArgumentParser(description="Descarga gameplays por URL o archivo .txt con recorte opcional.")
    parser.add_argument("entradas", nargs="+", help="URL(s) directa(s) o ruta(s) a archivo .txt con URLs")
    parser.add_argument("--cortar", type=int, default=None, help="Recortar a N segundos automaticamente (muestreo aleatorio)")
    parser.add_argument("--calidad", type=int, default=RESOLUCION_MAXIMA, choices=[480, 720, 1080, 2160], help="Altura maxima")
    args = parser.parse_args()

    urls = _resolver_entradas(args.entradas)
    if not urls:
        print("No hay URLs para descargar.")
        return

    descargados = []
    for url in urls:
        try:
            ruta = descargar(url, duracion=args.cortar or DURACION_OBJETIVO, calidad=args.calidad, sin_recorte=(args.cortar is None))
            descargados.append(ruta)
        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\nListo. {len(descargados)}/{len(urls)} gameplays en {CARPETA_GAMEPLAY}/")
    todos = sorted(CARPETA_GAMEPLAY.glob("*.mp4"))
    if todos:
        print("Gameplays disponibles:")
        for f in todos:
            print(f"  {f.name} ({f.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
