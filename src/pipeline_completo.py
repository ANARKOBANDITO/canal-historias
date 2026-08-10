"""
pipeline_completo.py

Ejecuta el flujo completo del proyecto en cascada:
guiones -> audio -> subtitulos ASS (16:9 y 9:16) -> video (16:9 y 9:16) -> shorts.

Requiere que ya existan los guiones en output/guiones_listos/ y gameplay
en storage/raw_gameplay/.

Uso (desde la raiz del proyecto):
    python src/pipeline_completo.py --cantidad 5 --genero hombre
    python src/pipeline_completo.py --cantidad 3 --motor edge  (pruebas rapidas)
"""

import argparse
import subprocess
import sys
from pathlib import Path

FFMPEG_BIN = Path(os.environ.get("LOCALAPPDATA", "")) / "ffmpeg"


def _path_con_ffmpeg() -> str:
    """Devuelve el PATH incluyendo la ruta de ffmpeg de Windows."""
    actual = os.environ.get("PATH", "")
    bin_dir = FFMPEG_BIN / "ffmpeg-9.0-essentials_build" / "bin"
    if bin_dir.exists():
        return f"{actual};{bin_dir}"
    return actual


def _correr(script: str, args: list[str]) -> bool:
    comando = [sys.executable, f"src/{script}"] + args
    print(f"\n>>> {' '.join(comando)}\n")
    proc = subprocess.run(comando, env={**os.environ, "PATH": _path_con_ffmpeg()})
    return proc.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Ejecuta el pipeline completo guion->video->shorts.")
    parser.add_argument("--cantidad", type=int, default=None, help="Cantidad de items a procesar en cada etapa")
    parser.add_argument("--genero", choices=["hombre", "mujer"], default="mujer")
    parser.add_argument("--motor", choices=["kokoro", "edge"], default="kokoro")
    args = parser.parse_args()

    extra = []
    if args.cantidad:
        extra = ["--cantidad", str(args.cantidad)]

    pasos = [
        ("generar_audio.py", ["--genero", args.genero, "--motor", args.motor] + extra),
        ("generar_subtitulos_ass.py", ["--procesar"]),
        ("generar_subtitulos_ass.py", ["--procesar", "--vertical"]),
        ("ensamblar_video.py", ["--procesar", "--tambien-vertical"]),
        ("cortar_shorts.py", ["--procesar"]),
    ]

    for i, (script, args_list) in enumerate(pasos, 1):
        print(f"\n=== Paso {i}/{len(pasos)}: {script} ===")
        if not _correr(script, args_list):
            print(f"\n[ERROR] El pipeline se detuvo en: {script}")
            sys.exit(1)

    print("\nPipeline completo ejecutado con exito.")


if __name__ == "__main__":
    import os
    main()
