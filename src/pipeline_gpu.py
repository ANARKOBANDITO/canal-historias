"""
pipeline_gpu.py

Orquestador del pipeline completo para ejecutar en el Pod con GPU
(RunPod, RTX 3060 o superior). Toma un guion o lote de guiones
desde output/guiones_listos/ y ejecuta en secuencia:

  1. Audio (Chatterbox, voice cloning)
  2. Division del audio en episodios de ~5 min
  3. Subtitulos ASS karaoke (whisper CUDA, 16:9 + 9:16)
  4. Videos finales (ffmpeg NVENC, 16:9 + 9:16)
  5. Shorts/Reels/TikTok

Los parametros se auto-detectan del guion ([IDIOMA: ...],
[GENERO: ...]) sin intervencion manual. Soporta multiples idiomas
en el mismo lote (cambia el language_id de Chatterbox por guion).

Uso (desde la raiz del proyecto, dentro del Pod):
    python src/pipeline_gpu.py --cantidad 1
    python src/pipeline_gpu.py output/guiones_listos/mi_historia.txt
    python src/pipeline_gpu.py --procesar --segundos 60   # prueba rapida
"""

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

from utilidades import normalizar_nombre

CARPETA_GUIONES = Path("output/guiones_listos")
CARPETA_AUDIO = Path("output/audio")
CARPETA_ASS = Path("output/subtitulos_ass")
CARPETA_VIDEO = Path("output/videos")
CARPETA_SHORTS = Path("output/shorts")
CARPETA_EPISODIOS = Path("output/audio/episodios")
CARPETA_GAMEPLAY = Path("storage/raw_gameplay")


def _hay_gpu() -> bool:
    try:
        out = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=5
        ).stdout
        return "h264_nvenc" in out
    except Exception:
        return False


def _gameplay_aleatorio() -> Path | None:
    if not CARPETA_GAMEPLAY.exists():
        return None
    videos = list(CARPETA_GAMEPLAY.glob("*.mp4"))
    if not videos:
        return None
    import random
    return random.choice(videos)


def _formatear_tiempo(segundos: float) -> str:
    m, s = divmod(int(segundos), 60)
    return f"{m}m{s:02d}s"


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline GPU completo: guion -> audio -> episodios -> subs -> videos -> shorts.")
    parser.add_argument("guion", nargs="?", help="Ruta a un guion especifico")
    parser.add_argument("--cantidad", type=int, default=None, help="Cantidad de guiones a procesar")
    parser.add_argument("--procesar", action="store_true", help="Procesar todos los guiones en output/guiones_listos/")
    parser.add_argument("--segundos", type=int, default=None, help="Renderizar solo N segundos (pruebas rapidas)")
    parser.add_argument("--sin-shorts", action="store_true", help="No generar shorts al final")
    parser.add_argument("--motor", choices=["chatterbox", "kokoro"], default="chatterbox",
                        help="Motor TTS (default: chatterbox)")
    parser.add_argument("--idioma", choices=["es", "en", "pt"], default=None,
                        help="Forzar idioma (por defecto se lee de [IDIOMA:] en el guion)")
    args = parser.parse_args()

    # ── Resolver entrada ─────────────────────────────────────
    guiones: list[Path] = []
    if args.guion:
        guiones = [Path(args.guion)]
    elif args.cantidad:
        if not CARPETA_GUIONES.exists():
            print(f"No existe {CARPETA_GUIONES}/")
            return
        guiones = sorted(CARPETA_GUIONES.glob("*.txt"))[: args.cantidad]
    elif args.procesar:
        if not CARPETA_GUIONES.exists():
            print(f"No existe {CARPETA_GUIONES}/")
            return
        guiones = sorted(CARPETA_GUIONES.glob("*.txt"))
    else:
        print("Especifica un guion, --cantidad o --procesar.")
        return

    if not guiones:
        print("No se encontraron guiones.")
        return

    # ── Info del entorno ─────────────────────────────────────
    gpu_disponible = _hay_gpu()
    print(f"GPU (NVENC): {'SI' if gpu_disponible else 'NO (usando libx264)'}")
    game = _gameplay_aleatorio()
    print(f"Gameplay:   {game.name if game else 'NO (fondo negro)'}")
    print(f"Guiones:    {len(guiones)}\n")

    t_inicio = time.time()

    # ── Limpiar episodios previos ────────────────────────────
    if CARPETA_EPISODIOS.exists():
        shutil.rmtree(CARPETA_EPISODIOS)
    CARPETA_EPISODIOS.mkdir(exist_ok=True, parents=True)

    for idx, guion in enumerate(guiones, 1):
        nombre_base = normalizar_nombre(guion.stem, max_largo=60)
        ido = args.idioma or _leer_idioma(guion) or "es"
        print(f"\n{'='*60}")
        print(f" [{idx}/{len(guiones)}] {guion.name}  (idioma: {ido})")
        print(f"{'='*60}")

        # ── 1. Audio ─────────────────────────────────────────
        t_audio = time.time()
        print("\n1. Generando audio...")
        subprocess.run([
            sys.executable, "src/generar_audio.py", str(guion),
            "--motor", args.motor, "--idioma", ido,
        ], check=True)
        ruta_audio = CARPETA_AUDIO / f"{nombre_base}.mp3"
        if not ruta_audio.exists():
            print(f"  ERROR: no se genero {ruta_audio}")
            continue
        print(f"  Audio: {_formatear_tiempo(time.time() - t_audio)}")

        # ── 2. Dividir en episodios ───────────────────────────
        t_div = time.time()
        print("\n2. Dividiendo en episodios...")
        subprocess.run([
            sys.executable, "src/dividir_audio.py", str(ruta_audio),
        ], check=True)
        episodios = sorted(CARPETA_EPISODIOS.glob(f"{nombre_base}_parte_*.mp3"))
        print(f"  Episodios: {len(episodios)}  ({_formatear_tiempo(time.time() - t_div)})")

        # ── 3. Subtitulos ASS 16:9 ────────────────────────────
        t_ass16 = time.time()
        print("\n3. Subtitulos ASS 16:9...")
        subprocess.run([
            sys.executable, "src/generar_subtitulos_ass.py", str(ruta_audio),
            "--idioma", ido,
        ], check=True)
        print(f"  ASS 16:9: {_formatear_tiempo(time.time() - t_ass16)}")

        # ── 4. Subtitulos ASS 9:16 ────────────────────────────
        t_ass91 = time.time()
        print("\n4. Subtitulos ASS 9:16...")
        subprocess.run([
            sys.executable, "src/generar_subtitulos_ass.py", str(ruta_audio),
            "--vertical", "--idioma", ido,
        ], check=True)
        print(f"  ASS 9:16: {_formatear_tiempo(time.time() - t_ass91)}")

        # ── 5. Videos (16:9 y 9:16) ──────────────────────────
        t_vid = time.time()
        print(f"\n5. Renderizando {len(episodios)} episodios (16:9 + 9:16)...")

        for ep in episodios:
            ep_audio = ep
            ep_base = normalizar_nombre(ep.stem, max_largo=70)
            ass_169 = CARPETA_ASS / f"{nombre_base}.ass"
            ass_916 = CARPETA_ASS / f"{nombre_base}_9x16.ass"

            cmd = [
                sys.executable, "src/ensamblar_video.py", str(ep_audio),
                "--tambien-vertical",
            ]
            if game:
                cmd += ["--gameplay", str(game)]
            if args.segundos:
                cmd += ["--segundos", str(args.segundos)]

            print(f"    {ep.name}...")
            subprocess.run(cmd, check=True)

        print(f"  Videos: {_formatear_tiempo(time.time() - t_vid)}")

        # ── 6. Shorts ────────────────────────────────────────
        if not args.sin_shorts:
            t_sh = time.time()
            print("\n6. Cortando shorts...")
            subprocess.run([
                sys.executable, "src/cortar_shorts.py", "--procesar",
            ], check=True)
            print(f"  Shorts: {_formatear_tiempo(time.time() - t_sh)}")

    t_total = time.time() - t_inicio
    print(f"\n{'='*60}")
    print(f" Pipeline completo: {_formatear_tiempo(t_total)}")
    print(f" Resultados en: {CARPETA_VIDEO}/ y {CARPETA_SHORTS}/")
    print(f"{'='*60}")


def _leer_idioma(ruta: Path) -> str | None:
    try:
        for linea in ruta.read_text(encoding="utf-8").split("\n"):
            if linea.startswith("[IDIOMA:"):
                return linea.split(":", 1)[1].strip().rstrip("]").strip()
    except Exception:
        pass
    return None


if __name__ == "__main__":
    main()
