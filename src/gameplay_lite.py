"""
gameplay_lite.py

Prepara gameplays para subida confiable al pod Vast.ai comprimiendo los
archivos crudos (que pueden pesar 300MB-1GB y se cortan en scp) a loops
ligeros de ~60-80MB. Recorta a una duracion maxima y reescala a 1080p
con bitrate moderado.

Salida en storage/gameplay_lite/ con nombres gameplay_lite_001.mp4, etc.

Uso (desde la raiz del proyecto):
    python src/gameplay_lite.py --duracion 600
    python src/gameplay_lite.py --duracion 600 --crudo "storage/raw_gameplay/gameplay_001.mp4"
"""

import argparse
import subprocess
from pathlib import Path

CARPETA_CRUDO = Path("storage/raw_gameplay")
CARPETA_LITE = Path("storage/gameplay_lite")

FFMPEG = "ffmpeg"


def _ffmpeg() -> str:
    import os
    candidatos = [
        "ffmpeg",
        os.path.expandvars(r"%LOCALAPPDATA%\ffmpeg\ffmpeg-9.0-essentials_build\bin\ffmpeg.exe"),
    ]
    for c in candidatos:
        try:
            subprocess.run([c, "-version"], capture_output=True, timeout=5)
            return c
        except Exception:
            continue
    return "ffmpeg"


def comprimir(ruta_crudo: Path, ruta_lite: Path, duracion: int) -> None:
    """Comprime a loop ligero: -t duracion, scale 1080p, bitrate video 2M, audio AAC 96k."""
    cmd = [
        _ffmpeg(), "-y", "-i", str(ruta_crudo),
        "-t", str(duracion),
        "-vf", "scale='min(1920,iw)':-2:force_original_aspect_ratio=decrease",
        "-c:v", "libx264", "-preset", "fast", "-crf", "28", "-maxrate", "2M", "-bufsize", "4M",
        "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart",
        str(ruta_lite),
    ]
    print(f"  {ruta_crudo.name} ({ruta_crudo.stat().st_size/1048576:.0f}MB) -> {ruta_lite.name}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"  ERROR: {proc.stderr[-300:]}")
        raise RuntimeError(f"ffmpeg fallo en {ruta_crudo.name}")
    print(f"  OK {ruta_lite.stat().st_size/1048576:.0f}MB")


def main():
    parser = argparse.ArgumentParser(description="Comprime gameplay crudo a loops ligeros para el pod.")
    parser.add_argument("--duracion", type=int, default=600, help="Duracion maxima en segundos (default 600 = 10 min)")
    parser.add_argument("--crudo", default=None, help="Ruta a un archivo crudo especifico (si no, todos en raw_gameplay/)")
    args = parser.parse_args()

    CARPETA_LITE.mkdir(exist_ok=True, parents=True)

    crudos: list[Path] = []
    if args.crudo:
        crudos = [Path(args.crudo)]
    elif CARPETA_CRUDO.exists():
        crudos = sorted(CARPETA_CRUDO.glob("*.mp4"))
    else:
        print(f"No existe {CARPETA_CRUDO}/")
        return

    if not crudos:
        print("No se encontraron gameplays crudos.")
        return

    for i, c in enumerate(crudos, 1):
        salida = CARPETA_LITE / f"gameplay_lite_{i:03d}.mp4"
        comprimir(c, salida, args.duracion)

    print(f"\nListo. {len(crudos)} loops ligeros en {CARPETA_LITE}/")
    total = sum(f.stat().st_size for f in CARPETA_LITE.glob("*.mp4"))
    print(f"Total: {total/1048576:.0f}MB")


if __name__ == "__main__":
    main()
