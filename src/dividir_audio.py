"""
dividir_audio.py

Parte un archivo de audio MP3 en episodios de ~5 minutos usando ffmpeg
con copia de stream (sin re-encode, instantaneo). Util para convertir
una historia larga de 20-30 min en partes aptas para Shorts/TikTok.

Uso (desde la raiz del proyecto):
    python src/dividir_audio.py output/audio/mi_historia.mp3
    python src/dividir_audio.py output/audio/mi_historia.mp3 --segundos 300
    python src/dividir_audio.py output/audio/mi_historia.mp3 --procesar
"""

import argparse
import subprocess
from pathlib import Path

from utilidades import normalizar_nombre

CARPETA_AUDIO = Path("output/audio")
CARPETA_EPISODIOS = Path("output/audio/episodios")
SEGUNDOS_EPISODIO = 300  # 5 minutos


def dividir(ruta_audio: Path, segundos: int = SEGUNDOS_EPISODIO, carpeta_salida: Path = CARPETA_EPISODIOS) -> list[Path]:
    nombre_base = normalizar_nombre(ruta_audio.stem, max_largo=50)
    carpeta_salida.mkdir(exist_ok=True, parents=True)
    patron = carpeta_salida / f"{nombre_base}_parte_%03d.mp3"

    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(ruta_audio),
        "-f", "segment",
        "-segment_time", str(segundos),
        "-c", "copy",
        str(patron),
    ], check=True, capture_output=True)

    episodios = sorted(carpeta_salida.glob(f"{nombre_base}_parte_*.mp3"))
    duracion_total = sum(_duracion_audio(e) for e in episodios)
    print(f"  {ruta_audio.name}: {len(episodios)} episodios de ~{segundos}s (total {duracion_total:.0f}s)")

    return episodios


def _duracion_audio(ruta: Path) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(ruta)],
        capture_output=True, text=True,
    )
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return 0.0


def main():
    parser = argparse.ArgumentParser(description="Parte un audio MP3 en episodios de ~5 min (ffmpeg copy, instantaneo).")
    parser.add_argument("audio", nargs="?", help="Ruta al archivo de audio")
    parser.add_argument("--procesar", action="store_true", help="Procesar todos los audios en output/audio/")
    parser.add_argument("--segundos", type=int, default=SEGUNDOS_EPISODIO, help="Duracion de cada episodio")
    parser.add_argument("--salida", type=Path, default=CARPETA_EPISODIOS, help="Carpeta de salida")
    args = parser.parse_args()

    audios: list[Path] = []
    if args.audio:
        audios = [Path(args.audio)]
    elif args.procesar:
        if not CARPETA_AUDIO.exists():
            print(f"No existe {CARPETA_AUDIO}/")
            return
        audios = sorted([a for a in CARPETA_AUDIO.glob("*.mp3") if "parte_" not in a.name])
    else:
        print("Especifica un archivo de audio o usa --procesar.")
        return

    if not audios:
        print("No se encontraron archivos de audio para dividir.")
        return

    for audio in audios:
        dividir(audio, segundos=args.segundos, carpeta_salida=args.salida)

    print(f"\nListo. Episodios guardados en {args.salida}/")


if __name__ == "__main__":
    main()
