"""
cortar_shorts.py

Divide un video 9:16 pre-renderizado en clips para Shorts/Reels/TikTok.
Detecta pausas naturales entre subtitulos como puntos de corte para no
cortar a mitad de palabra ni de frase.

IMPORTANTE: los videos deben estar pre-renderizados en 9:16 por
ensamblar_video.py --tambien-vertical. Este script solo recorta
segmentos de tiempo, no hace conversion de formato.

Uso (desde la raiz del proyecto):
    python src/cortar_shorts.py output/videos/mi_video_9x16.mp4
    python src/cortar_shorts.py --procesar
"""

import argparse
import re
import subprocess
from pathlib import Path

from utilidades import normalizar_nombre

FFMPEG = "ffmpeg"
CARPETA_VIDEOS = Path("output/videos")
CARPETA_SHORTS = Path("output/shorts")
CARPETA_ASS = Path("output/subtitulos_ass")

DURACION_CLIP = 120  # duracion objetivo de cada short en segundos (~2 min)


def _obtener_duracion_video(ruta_video: Path) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(ruta_video)],
        capture_output=True, text=True,
    )
    return float(proc.stdout.strip())


def _leer_tiempos_ass(ruta_ass: Path) -> list[float]:
    tiempos = []
    if not ruta_ass.exists():
        return tiempos
    texto = ruta_ass.read_text(encoding="utf-8")
    for linea in texto.split("\n"):
        if linea.startswith("Dialogue:"):
            partes = linea.split(",")
            if len(partes) >= 3:
                end_str = partes[2]
                match = re.match(r"(\d+):(\d+):(\d+)\.(\d+)", end_str)
                if match:
                    h, m, s, c = int(match[1]), int(match[2]), int(match[3]), int(match[4])
                    segundos = h * 3600 + m * 60 + s + c / 100.0
                    tiempos.append(segundos)
    return sorted(tiempos)


def _puntos_corte(duration: float, tiempos_sub: list[float], duracion_objetivo: float = DURACION_CLIP) -> list[float]:
    if duration <= duracion_objetivo * 1.5:
        return []

    cortes = []
    cursor = duracion_objetivo

    while cursor < duration - 30:
        mejor = None
        for t in tiempos_sub:
            if abs(t - cursor) < 15:
                if mejor is None or abs(t - cursor) < abs(mejor - cursor):
                    mejor = t
        if mejor:
            cortes.append(mejor)
        else:
            cortes.append(cursor)
        cursor = cortes[-1] + duracion_objetivo

    return cortes


def _extraer_clip(ruta_video: Path, ruta_out: Path, inicio: float, duracion: float) -> None:
    args = [
        FFMPEG, "-y",
        "-ss", str(inicio), "-i", str(ruta_video),
        "-t", str(duracion),
        "-c:v", "copy", "-c:a", "copy",
        str(ruta_out),
    ]
    subprocess.run(args, capture_output=True, check=True)


def _cortar_shorts(ruta_video: Path, ruta_ass: Path) -> None:
    nombre_base = ruta_video.stem.replace("_9x16", "")

    duration = _obtener_duracion_video(ruta_video)
    tiempos_sub = _leer_tiempos_ass(ruta_ass) if ruta_ass.exists() else []
    cortes = _puntos_corte(duration, tiempos_sub)

    if not cortes:
        ruta_out = CARPETA_SHORTS / f"{nombre_base}_shorts_001.mp4"
        _extraer_clip(ruta_video, ruta_out, 0, duration)
        print(f"  1 clip (sin dividir, {duration:.0f}s) -> {ruta_out}")
        return

    cortes_completos = [0.0] + cortes + [duration]

    for i in range(len(cortes_completos) - 1):
        inicio = cortes_completos[i]
        fin = cortes_completos[i + 1]

        ruta_out = CARPETA_SHORTS / f"{nombre_base}_shorts_{i + 1:03d}.mp4"
        _extraer_clip(ruta_video, ruta_out, inicio, fin - inicio)
        print(f"  Clip {i+1}: {inicio:.0f}s - {fin:.0f}s ({fin-inicio:.0f}s) -> {ruta_out}")


def main():
    parser = argparse.ArgumentParser(description="Divide video 9:16 en clips para Shorts.")
    parser.add_argument("video", nargs="?", help="Ruta a un video 9:16")
    parser.add_argument("--procesar", action="store_true", help="Procesar todos los videos 9:16 en output/videos/")
    parser.add_argument("--cantidad", type=int, default=None, help="Cantidad a procesar")
    args = parser.parse_args()

    videos: list[Path] = []
    if args.video:
        videos = [Path(args.video)]
    elif args.procesar or args.cantidad:
        if not CARPETA_VIDEOS.exists():
            print(f"No existe {CARPETA_VIDEOS}/")
            return
        todos = sorted(CARPETA_VIDEOS.glob("*_9x16.mp4"))
        videos = todos[: args.cantidad] if args.cantidad else todos
    else:
        print("Especifica un archivo de video o usa --procesar.")
        return

    if not videos:
        print("No se encontraron videos 9:16 (_9x16.mp4) para cortar.")
        return

    CARPETA_SHORTS.mkdir(exist_ok=True)

    for i, video in enumerate(videos, 1):
        print(f"[{i}/{len(videos)}] {video.name}")
        nombre_base = normalizar_nombre(video.stem.replace("_9x16", ""), max_largo=60)
        ruta_ass = CARPETA_ASS / f"{nombre_base}_9x16.ass"
        _cortar_shorts(video, ruta_ass)

    print(f"\nListo. Shorts generados en {CARPETA_SHORTS}/.")


if __name__ == "__main__":
    main()
