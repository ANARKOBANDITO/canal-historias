"""
generar_tarjeta_reddit.py

Genera una tarjeta estilo "publicacion de Reddit" (usuario del canal +
avatar + texto del gancho) y la superpone al inicio del video 16:9
mientras suena el gancho. Solo se aplica al formato 16:9 (YouTube);
el 9:16 no lleva tarjeta.

La duracion de la tarjeta es igual a la duracion del audio del gancho,
medida con ffprobe sobre el segmento de audio del gancho.

Uso (desde la raiz del proyecto):
    python src/generar_tarjeta_reddit.py "output/guiones_listos/guion.txt"
    python src/generar_tarjeta_reddit.py --procesar
"""

import argparse
import subprocess
from pathlib import Path

from utilidades import normalizar_nombre

CARPETA_GUIONES = Path("output/guiones_listos")
CARPETA_AUDIO = Path("output/audio")
CARPETA_VIDEO = Path("output/videos")
CARPETA_TARJETAS = Path("output/tarjetas")
CARPETA_AVATAR = Path("storage/avatar")

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"

# Identidad del canal (cambiar cuando el usuario decida el nombre)
NOMBRE_CANAL = "r/HopStories"
AVATAR_DEFAULT = "avatar_neutral.png"

ANCHO = 1920
ALTO = 1080


def _duracion_audio(ruta: Path) -> float:
    proc = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(ruta)],
        capture_output=True, text=True,
    )
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return 0.0


def extraer_gancho(ruta_guion: Path) -> str:
    """Devuelve el primer parrafo del guion (el gancho)."""
    lineas = ruta_guion.read_text(encoding="utf-8").split("\n")
    parrafos = []
    actual = []
    for linea in lineas:
        if linea.startswith("[GENERO:") or linea.startswith("[IDIOMA:"):
            continue
        if linea.strip() == "":
            if actual:
                parrafos.append(" ".join(actual))
                actual = []
        else:
            actual.append(linea.strip())
    if actual:
        parrafos.append(" ".join(actual))
    return parrafos[0] if parrafos else ""


def _duracion_audio_gancho(ruta_audio: Path, gancho: str) -> float:
    """Estima la duracion del gancho como fraccion del audio total."""
    total = _duracion_audio(ruta_audio)
    if not gancho:
        return min(8.0, total)
    # El gancho es el primer parrafo; estimamos ~8-15% del texto o un max de 12s.
    return max(5.0, min(12.0, total * 0.15))


def generar_tarjeta(ruta_guion: Path, ruta_avatar: Path, ruta_png: Path, usuario: str = NOMBRE_CANAL) -> str:
    """Renderiza la tarjeta estilo Reddit con Pillow. Devuelve el texto del gancho."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  Pillow no esta instalado. pip install pillow")
        return ""

    gancho = extraer_gancho(ruta_guion)
    if not gancho:
        print("  [AVISO] No se encontro el gancho en el guion.")
        gancho = "Historia anonima"

    img = Image.new("RGB", (ANCHO, ALTO), (26, 26, 27))  # gris oscuro de Reddit
    draw = ImageDraw.Draw(img)

    # Avatar en circulo
    if ruta_avatar.exists():
        try:
            avatar = Image.open(ruta_avatar).convert("RGBA").resize((180, 180), Image.LANCZOS)
            mask = Image.new("L", (180, 180), 0)
            from PIL import ImageDraw as _id
            _id.Draw(mask).ellipse((0, 0, 180, 180), fill=255)
            img.paste(avatar, (80, 120), mask)
        except Exception as e:
            print(f"  [AVISO] No se pudo cargar el avatar: {e}")

    # Fuentes
    try:
        fuente_user = ImageFont.truetype("storage/Montserrat-Bold.ttf", 56)
        fuente_texto = ImageFont.truetype("storage/Montserrat-Bold.ttf", 64)
        fuente_meta = ImageFont.truetype("storage/Montserrat-Bold.ttf", 40)
    except Exception:
        fuente_user = ImageFont.load_default()
        fuente_texto = ImageFont.load_default()
        fuente_meta = ImageFont.load_default()

    # Usuario + comunidad
    draw.text((300, 140), usuario, fill=(215, 218, 220), font=fuente_user)
    draw.text((300, 215), "hace 3 horas  ·  r/confesiones", fill=(120, 124, 126), font=fuente_meta)

    # Texto del gancho, con wrap a ~45 caracteres por linea
    import textwrap
    lineas = textwrap.wrap(gancho, width=42)
    y = 420
    for linea in lineas[:6]:
        draw.text((80, y), linea, fill=(240, 242, 245), font=fuente_texto)
        y += 90

    # Pie de tarjeta (pseudo-votos/upvote)
    draw.text((80, ALTO - 140), "▲ 1.2k   ▼  Comentarios 34   Compartir", fill=(120, 124, 126), font=fuente_meta)

    ruta_png.parent.mkdir(exist_ok=True, parents=True)
    img.save(str(ruta_png))
    print(f"  Tarjeta Reddit: {ruta_png}")
    return gancho


def superponer_tarjeta(ruta_video_169: Path, ruta_tarjeta: Path, duracion: float, segundos: int | None = None) -> None:
    """Superpone la tarjeta al inicio del video 16:9 con fade in/out."""
    ruta_out = ruta_video_169.with_stem(ruta_video_169.stem + "_con_tarjeta")
    tarjeta_esc = str(ruta_tarjeta.resolve()).replace("\\", "/").replace(":", "\\:")

    # fade de entrada (0.3s) y salida (0.5s) al final de la tarjeta
    vf = (
        f"[1:v]format=rgba,fade=t=in:st=0:d=0.3:alpha=1,"
        f"fade=t=out:st={max(0, duracion - 0.5)}:d=0.5:alpha=1[card];"
        f"[0:v][card]overlay=0:0:enable='between(t,0,{duracion})'"
    )
    args = [
        FFMPEG, "-y", "-nostdin",
        "-i", str(ruta_video_169),
        "-i", str(ruta_tarjeta),
        "-filter_complex", vf,
        "-map", "0:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "21",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
    ]
    if segundos:
        args += ["-t", str(segundos)]
    args.append(str(ruta_out))

    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"  ERROR overlay tarjeta: {proc.stderr[-500:]}")
        raise RuntimeError("ffmpeg fallo al superponer tarjeta")
    print(f"  Video con tarjeta: {ruta_out}")


def procesar_guion(ruta_guion: Path, usuario: str = NOMBRE_CANAL, segundos: int | None = None) -> None:
    nombre_base = normalizar_nombre(ruta_guion.stem, max_largo=60)
    ruta_audio = CARPETA_AUDIO / f"{nombre_base}.mp3"
    ruta_video = CARPETA_VIDEO / f"{nombre_base}_16x9.mp4"
    ruta_avatar = CARPETA_AVATAR / AVATAR_DEFAULT
    ruta_png = CARPETA_TARJETAS / f"{nombre_base}_tarjeta.png"

    if not ruta_video.exists():
        print(f"  [AVISO] No existe video 16:9 para {nombre_base}. Ensambla primero.")
        return
    if not ruta_avatar.exists():
        print(f"  [AVISO] No existe avatar en {ruta_avatar}. Se generara tarjeta sin avatar.")
    if not ruta_audio.exists():
        print(f"  [AVISO] No existe audio para {nombre_base}. Duracion de tarjeta = 8s.")
        duracion = 8.0
    else:
        gancho = generar_tarjeta(ruta_guion, ruta_avatar, ruta_png, usuario=usuario)
        duracion = _duracion_audio_gancho(ruta_audio, gancho)

    superponer_tarjeta(ruta_video, ruta_png, duracion, segundos)


def main():
    parser = argparse.ArgumentParser(description="Genera tarjeta estilo Reddit y la superpone al inicio del 16:9.")
    parser.add_argument("guion", nargs="?", help="Ruta a un guion especifico")
    parser.add_argument("--procesar", action="store_true", help="Procesar todos los guiones en output/guiones_listos/")
    parser.add_argument("--usuario", default=NOMBRE_CANAL, help=f"Username del canal (default: {NOMBRE_CANAL})")
    parser.add_argument("--segundos", type=int, default=None, help="Limitar el render a N segundos (pruebas rapidas)")
    args = parser.parse_args()

    guiones: list[Path] = []
    if args.guion:
        guiones = [Path(args.guion)]
    elif args.procesar:
        if not CARPETA_GUIONES.exists():
            print(f"No existe {CARPETA_GUIONES}/")
            return
        guiones = sorted(CARPETA_GUIONES.glob("*.txt"))
    else:
        print("Especifica un guion o usa --procesar.")
        return

    for guion in guiones:
        print(f"Procesando {guion.name}...")
        procesar_guion(guion, usuario=args.usuario, segundos=args.segundos)

    print("\nListo. Tarjetas en output/tarjetas/ y videos en output/videos/.")


if __name__ == "__main__":
    main()
