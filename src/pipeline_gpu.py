"""
pipeline_gpu.py

Orquestador del pipeline completo para ejecutar en el Pod con GPU
(Vast.ai, RTX 3090). Toma los guiones desde output/guiones_listos/ y
ejecuta en secuencia para CADA UNO:

  1. Audio (Chatterbox, voice cloning)
  2. Subtitulos ASS karaoke (whisper CUDA, 16:9 + 9:16)
  3. Video COMPLETO 16:9 + 9:16 (ffmpeg NVENC)
  4. Tarjeta Reddit (SOLO 16:9)
  5. Miniaturas (Qwen-Image-Edit 4-bit)
  6. Review (Qwen2.5-VL local)
  7. Cortar shorts (9:16 en partes ~5 min con CTA)

Flujo correcto (validado 11/08): el audio NO se divide en episodios.
Se renderiza el video COMPLETO y `cortar_shorts` lo corta en partes,
porque el ASS se genera del audio completo (el enfoque por episodio
causaba un bug de ASS inexistente).

Los parametros se auto-detectan del guion ([IDIOMA: ...], [GENERO: ...]).
Soporta multiples idiomas en el mismo lote (cambia el language_id de
Chatterbox por guion).

Uso (desde la raiz del proyecto, dentro del Pod):
    python src/pipeline_gpu.py --procesar
    python src/pipeline_gpu.py --cantidad 1
    python src/pipeline_gpu.py output/guiones_listos/mi_historia.txt
    python src/pipeline_gpu.py --procesar --sin-shorts     # solo hasta video
    python src/pipeline_gpu.py --procesar --solo-audio     # solo audio
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
    videos = list(CARPETA_GAMEPLAY.glob("*.mp4")) + list(CARPETA_GAMEPLAY.glob("*.mkv"))
    if not videos:
        return None
    import random
    return random.choice(videos)


def _formatear_tiempo(segundos: float) -> str:
    m, s = divmod(int(segundos), 60)
    return f"{m}m{s:02d}s"


def _leer_idioma(ruta: Path) -> str | None:
    try:
        for linea in ruta.read_text(encoding="utf-8").split("\n"):
            if linea.startswith("[IDIOMA:"):
                return linea.split(":", 1)[1].strip().rstrip("]").strip()
    except Exception:
        pass
    return None


def _etapas_audio(guion: Path, args, nombre_base: str, ido: str) -> bool:
    """Etapa 1: audio con Chatterbox."""
    t = time.time()
    print("\n1. Generando audio...")
    subprocess.run([
        sys.executable, "src/generar_audio.py", str(guion),
        "--motor", args.motor, "--idioma", ido,
    ], check=True)
    ruta_audio = CARPETA_AUDIO / f"{nombre_base}.mp3"
    if not ruta_audio.exists():
        print(f"  ERROR: no se genero {ruta_audio}")
        return False
    print(f"  Audio: {_formatear_tiempo(time.time() - t)}")
    return True


def _etapas_subs(guion: Path, args, ruta_audio: Path, ido: str) -> None:
    """Etapas 2-3: ASS 16:9 y 9:16."""
    t = time.time()
    print("\n2. Subtitulos ASS 16:9...")
    subprocess.run([
        sys.executable, "src/generar_subtitulos_ass.py", str(ruta_audio),
        "--idioma", ido,
    ], check=True)
    print(f"  ASS 16:9: {_formatear_tiempo(time.time() - t)}")

    t = time.time()
    print("\n3. Subtitulos ASS 9:16...")
    subprocess.run([
        sys.executable, "src/generar_subtitulos_ass.py", str(ruta_audio),
        "--vertical", "--idioma", ido,
    ], check=True)
    print(f"  ASS 9:16: {_formatear_tiempo(time.time() - t)}")


def _etapas_video(args, nombre_base: str, game: Path | None) -> None:
    """Etapa 4: video COMPLETO 16:9 + 9:16 (NO por episodio)."""
    ruta_audio = CARPETA_AUDIO / f"{nombre_base}.mp3"
    t = time.time()
    print("\n4. Renderizando video completo (16:9 + 9:16)...")
    cmd = [
        sys.executable, "src/ensamblar_video.py", str(ruta_audio),
        "--tambien-vertical",
    ]
    if game:
        cmd += ["--gameplay", str(game)]
    if args.segundos:
        cmd += ["--segundos", str(args.segundos)]
    subprocess.run(cmd, check=True)
    print(f"  Videos: {_formatear_tiempo(time.time() - t)}")


def _etapas_finales(args, nombre_base: str, ido: str) -> None:
    """Etapas 5-7: tarjeta Reddit, miniaturas, review y shorts."""
    if not args.sin_tarjeta:
        print("\n5. Tarjeta Reddit (16:9)...")
        subprocess.run([
            sys.executable, "src/generar_tarjeta_reddit.py", "--procesar",
            "--usuario", "r/HopStories",
        ], check=True)

    if not args.sin_miniaturas:
        print("\n6. Miniaturas (Qwen-Image-Edit)...")
        subprocess.run([
            sys.executable, "src/generar_miniaturas.py", "--procesar",
        ], check=True)
        print("\n   Review (Qwen2.5-VL)...")
        subprocess.run([
            sys.executable, "src/revisar_miniaturas.py", "--procesar",
            "--backend", "local",
        ], check=True)

    if not args.sin_shorts:
        print(f"\n7. Cortando shorts (9:16, ~{args.minutos} min por parte, CTA en {ido})...")
        subprocess.run([
            sys.executable, "src/cortar_shorts.py", "--procesar",
            "--minutos", str(args.minutos), "--idioma", ido,
        ], check=True)


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline GPU completo: guion -> audio -> subs -> video -> tarjeta -> miniaturas -> shorts.")
    parser.add_argument("guion", nargs="?", help="Ruta a un guion especifico")
    parser.add_argument("--cantidad", type=int, default=None, help="Cantidad de guiones a procesar")
    parser.add_argument("--procesar", action="store_true", help="Procesar todos los guiones en output/guiones_listos/")
    parser.add_argument("--segundos", type=int, default=None, help="Renderizar solo N segundos (pruebas rapidas)")
    parser.add_argument("--motor", choices=["chatterbox", "kokoro", "edge"], default="chatterbox",
                        help="Motor TTS (default: chatterbox)")
    parser.add_argument("--idioma", choices=["es", "en", "pt"], default=None,
                        help="Forzar idioma (por defecto se lee de [IDIOMA:] en el guion)")
    parser.add_argument("--minutos", type=int, default=5, help="Minutos por parte de shorts (default 5)")
    parser.add_argument("--sin-shorts", action="store_true", help="No generar shorts al final")
    parser.add_argument("--sin-tarjeta", action="store_true", help="No generar tarjeta Reddit")
    parser.add_argument("--sin-miniaturas", action="store_true", help="No generar miniaturas ni review")
    args = parser.parse_args()

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

    gpu_disponible = _hay_gpu()
    print(f"GPU (NVENC): {'SI' if gpu_disponible else 'NO (usando libx264)'}")
    game = _gameplay_aleatorio()
    print(f"Gameplay:   {game.name if game else 'NO (fondo negro)'}")
    print(f"Guiones:    {len(guiones)}\n")

    t_inicio = time.time()

    for idx, guion in enumerate(guiones, 1):
        nombre_base = normalizar_nombre(guion.stem, max_largo=60)
        ido = args.idioma or _leer_idioma(guion) or "es"
        print(f"\n{'='*60}")
        print(f" [{idx}/{len(guiones)}] {guion.name}  (idioma: {ido})")
        print(f"{'='*60}")

        ruta_audio = CARPETA_AUDIO / f"{nombre_base}.mp3"
        hay_audio = ruta_audio.exists()

        if hay_audio:
            print("  [Audio ya existe, se conserva]")
        else:
            ok = _etapas_audio(guion, args, nombre_base, ido)
            if not ok:
                continue

        if not args.sin_miniaturas or not args.sin_shorts:
            _etapas_subs(guion, args, ruta_audio, ido)
            _etapas_video(args, nombre_base, game)
            _etapas_finales(args, nombre_base, ido)
        else:
            # modo solo-audio
            pass

    t_total = time.time() - t_inicio
    print(f"\n{'='*60}")
    print(f" Pipeline completo: {_formatear_tiempo(t_total)}")
    print(f" Resultados en: {CARPETA_VIDEO}/ y {CARPETA_SHORTS}/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
