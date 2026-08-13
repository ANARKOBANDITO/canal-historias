"""
ensamblar_video.py

Une audio narrado, subtitulos ASS karaoke y un gameplay de fondo
para producir el video final. Formato principal: 16:9 (horizontal)
para YouTube. Opcionalmente genera version 9:16 (vertical) para Shorts.

Uso (desde la raiz del proyecto):
    python src/ensamblar_video.py output/audio/mi_guion.mp3
    python src/ensamblar_video.py --audio output/audio/ --procesar
    python src/ensamblar_video.py output/audio/mi_guion.mp3 --tambien-vertical
"""

import argparse
import random
import subprocess
from pathlib import Path

from utilidades import normalizar_nombre

CARPETA_AUDIO = Path("output/audio")
CARPETA_ASS = Path("output/subtitulos_ass")
CARPETA_VIDEO = Path("output/videos")
CARPETA_GAMEPLAY = Path("storage/raw_gameplay")

FFMPEG = "ffmpeg"

# Codec de video: NVENC si hay GPU NVIDIA disponible, sino libx264
def _detectar_codec() -> str:
    """Prueba NVENC con un encode de 1 frame. Si falla, usa libx264."""
    import os
    try:
        proc = subprocess.run(
            [FFMPEG, "-hide_banner", "-y",
             "-f", "lavfi", "-i", "color=black:s=64x64:r=1",
             "-frames:v", "1",
             "-c:v", "h264_nvenc", "-f", "null", os.devnull],
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode == 0:
            return "h264_nvenc"
    except Exception:
        pass
    return "libx264"

CODEC_VIDEO = _detectar_codec()

if CODEC_VIDEO == "h264_nvenc":
    ARGS_ENCODER = ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "23", "-rc", "vbr"]
else:
    ARGS_ENCODER = ["-c:v", "libx264", "-preset", "medium", "-crf", "23"]

# Configuracion de salida 16:9
ANCHO_16_9 = 1920
ALTO_16_9 = 1080

# Configuracion de salida 9:16
ANCHO_9_16 = 1080
ALTO_9_16 = 1920


def _obtener_gameplay() -> Path | None:
    """Busca un gameplay aleatorio en raw_gameplay/."""
    if not CARPETA_GAMEPLAY.exists():
        return None
    videos = list(CARPETA_GAMEPLAY.glob("*.mp4")) + list(CARPETA_GAMEPLAY.glob("*.mkv")) + list(CARPETA_GAMEPLAY.glob("*.webm"))
    if not videos:
        return None
    return random.choice(videos)


def _generar_video_16_9(ruta_audio: Path, ruta_ass: Path, ruta_video: Path, ruta_gameplay: Path | None, segundos: int | None = None) -> None:
    args = [FFMPEG, "-y"]

    fonts_dir_escaped = str(Path("storage").resolve()).replace("\\", "/").replace(":", "\\:")
    ruta_ass_escaped = str(ruta_ass.resolve()).replace("\\", "/").replace(":", "\\:")

    if ruta_gameplay and ruta_gameplay.exists():
        args += ["-stream_loop", "-1", "-i", str(ruta_gameplay)]
        args += ["-i", str(ruta_audio)]
        args += ["-map", "0:v", "-map", "1:a"]
        args += ["-shortest"]
        vf_texto = (
            f"scale={ANCHO_16_9}:{ALTO_16_9}:force_original_aspect_ratio=increase,"
            f"crop={ANCHO_16_9}:{ALTO_16_9},"
            f"ass=filename='{ruta_ass_escaped}':fontsdir='{fonts_dir_escaped}'"
        )
    else:
        args += ["-f", "lavfi", "-i", f"color=black:s={ANCHO_16_9}x{ALTO_16_9}:r=30"]
        args += ["-i", str(ruta_audio)]
        args += ["-map", "0:v", "-map", "1:a"]
        args += ["-shortest"]
        vf_texto = f"ass=filename='{ruta_ass_escaped}':fontsdir='{fonts_dir_escaped}'"

    if segundos:
        args += ["-t", str(segundos)]

    args += ["-vf", vf_texto]
    args += ARGS_ENCODER
    args += [
        "-pix_fmt", "yuv420p",
        "-c:a", "libmp3lame", "-ar", "44100", "-ac", "2", "-b:a", "128k",
        str(ruta_video),
    ]

    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"  ERROR ffmpeg (16:9): {proc.stderr[-500:]}")
        raise RuntimeError("ffmpeg fallo en 16:9")
    print(f"  Video 16:9 : {ruta_video} ({ruta_video.stat().st_size / 1024 / 1024:.1f} MB)")


def _generar_video_9_16(ruta_audio: Path, ruta_ass: Path, ruta_video: Path, ruta_gameplay: Path | None, segundos: int | None = None) -> None:
    """Renderiza video 9:16 independiente: center-crop del gameplay + upscale lanczos + ASS vertical."""
    fonts_dir_escaped = str(Path("storage").resolve()).replace("\\", "/").replace(":", "\\:")
    ruta_ass_escaped = str(ruta_ass.resolve()).replace("\\", "/").replace(":", "\\:")

    args = [FFMPEG, "-y"]

    if ruta_gameplay and ruta_gameplay.exists():
        args += ["-stream_loop", "-1", "-i", str(ruta_gameplay)]
        args += ["-i", str(ruta_audio)]
        args += ["-map", "0:v", "-map", "1:a"]
        args += ["-shortest"]
        vf_texto = (
            f"crop=iw*9/16:ih:(iw-iw*9/16)/2:0,"
            f"scale={ANCHO_9_16}:{ALTO_9_16}:flags=lanczos,"
            f"setsar=1,"
            f"ass=filename='{ruta_ass_escaped}':fontsdir='{fonts_dir_escaped}'"
        )
    else:
        args += ["-f", "lavfi", "-i", f"color=black:s={ANCHO_9_16}x{ALTO_9_16}:r=30"]
        args += ["-i", str(ruta_audio)]
        args += ["-map", "0:v", "-map", "1:a"]
        args += ["-shortest"]
        vf_texto = f"ass=filename='{ruta_ass_escaped}':fontsdir='{fonts_dir_escaped}'"

    if segundos:
        args += ["-t", str(segundos)]

    args += ["-vf", vf_texto]
    args += ARGS_ENCODER
    args += [
        "-pix_fmt", "yuv420p",
        "-c:a", "libmp3lame", "-ar", "44100", "-ac", "2", "-b:a", "128k",
        str(ruta_video),
    ]

    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"  ERROR ffmpeg (9:16): {proc.stderr[-500:]}")
        raise RuntimeError("ffmpeg fallo en 9:16")
    print(f"  Video 9:16 : {ruta_video} ({ruta_video.stat().st_size / 1024 / 1024:.1f} MB)")


def _extraer_frames(ruta_video: Path, ruta_imagenes: Path, tiempos: list[float]) -> None:
    """Extrae frames del video en los tiempos dados para verificacion visual."""
    for t in tiempos:
        ruta_out = ruta_imagenes / f"{ruta_video.stem}_t{t:.0f}s.png"
        proc = subprocess.run(
            [FFMPEG, "-y", "-ss", str(t), "-i", str(ruta_video), "-frames:v", "1", str(ruta_out)],
            capture_output=True, text=True,
        )
        if proc.returncode == 0:
            print(f"  Frame en t={t:.0f}s -> {ruta_out}")


def main():
    parser = argparse.ArgumentParser(description="Ensambla video final a partir de audio + subtitulos + gameplay.")
    parser.add_argument("audio", nargs="?", help="Ruta al archivo de audio (MP3/WAV)")
    parser.add_argument("--procesar", action="store_true", help="Procesar todos los audios en output/audio/")
    parser.add_argument("--cantidad", type=int, default=None, help="Cantidad a procesar")
    parser.add_argument("--gameplay", default=None, help="Ruta a un gameplay especifico (aleatorio si no se pasa)")
    parser.add_argument("--segundos", type=int, default=None, help="Limitar el render a N segundos (pruebas rapidas)")
    parser.add_argument("--tambien-vertical", action="store_true", help="Generar tambien version 9:16")
    parser.add_argument("--solo-vertical", action="store_true", help="Generar SOLO version 9:16")
    parser.add_argument("--verificar", action="store_true", help="Extraer frames de control de los videos generados")
    args = parser.parse_args()

    # Determinar lista de audios
    audios: list[Path] = []
    if args.audio:
        audios = [Path(args.audio)]
    elif args.procesar or args.cantidad:
        if not CARPETA_AUDIO.exists():
            print(f"No existe {CARPETA_AUDIO}/")
            return
        todos = sorted(CARPETA_AUDIO.glob("*.mp3")) + sorted(CARPETA_AUDIO.glob("*.wav"))
        audios = todos[: args.cantidad] if args.cantidad else todos
    else:
        print("Especifica un archivo de audio o usa --procesar.")
        return

    if not audios:
        print("No se encontraron archivos de audio.")
        return

    CARPETA_VIDEO.mkdir(exist_ok=True)

    gameplay = Path(args.gameplay) if args.gameplay else _obtener_gameplay()
    if not args.gameplay and not gameplay:
        print("No se encontro gameplay. Se usara fondo negro.")
    else:
        print(f"Gameplay: {gameplay.name}")

    hacer_16_9 = not args.solo_vertical
    hacer_9_16 = args.tambien_vertical or args.solo_vertical

    for i, audio in enumerate(audios, 1):
        print(f"[{i}/{len(audios)}] {audio.name}")
        nombre_base = normalizar_nombre(audio.stem, max_largo=60)

        ass_16_9 = CARPETA_ASS / f"{nombre_base}.ass"
        ass_9_16 = CARPETA_ASS / f"{nombre_base}_9x16.ass"

        if hacer_16_9:
            video_16_9 = CARPETA_VIDEO / f"{nombre_base}_16x9.mp4"
            _generar_video_16_9(audio, ass_16_9, video_16_9, gameplay, args.segundos)

        if hacer_9_16:
            if not ass_9_16.exists():
                print(f"  [AVISO] No se encontro ASS 9:16 para {nombre_base}. Ejecuta generar_subtitulos_ass.py --vertical primero.")
                continue
            video_9_16 = CARPETA_VIDEO / f"{nombre_base}_9x16.mp4"
            _generar_video_9_16(audio, ass_9_16, video_9_16, gameplay, args.segundos)

        if args.verificar:
            carpeta_frames = CARPETA_VIDEO / "_frames"
            carpeta_frames.mkdir(exist_ok=True)
            for ext, t in [("_16x9.mp4", 10), ("_9x16.mp4", 10)]:
                ruta_v = CARPETA_VIDEO / f"{nombre_base}{ext}"
                if ruta_v.exists():
                    _extraer_frames(ruta_v, carpeta_frames, [t, 30, 60])

    print(f"\nListo. {len(audios)} videos generados en {CARPETA_VIDEO}/.")


if __name__ == "__main__":
    main()
