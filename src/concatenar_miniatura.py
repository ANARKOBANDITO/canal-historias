"""
concatenar_miniatura.py

Compone la miniatura final: escena + avatar con expresion + texto de
titulo. Es la fase de composicion (Pillow, CPU) posterior a la
generacion de la escena con Qwen-Image-Edit. Puede ejecutarse de
forma independiente si ya existen las escenas generadas.

Uso (desde la raiz del proyecto):
    python src/concatenar_miniatura.py "output/guiones_listos/guion.txt"
    python src/concatenar_miniatura.py --procesar
"""

import argparse
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from utilidades import normalizar_nombre

CARPETA_GUIONES = Path("output/guiones_listos")
CARPETA_MINIATURAS = Path("output/miniaturas")
CARPETA_ESCENAS = Path("output/miniaturas/_escenas")
CARPETA_AVATAR = Path("storage/avatar")
FUENTE = Path("storage/Montserrat-Bold.ttf")

EXPRESION_POR_TONO = {
    "triste": "avatar_triste.png",
    "enojado": "avatar_enojado.png",
    "feliz": "avatar_feliz.png",
    "sorprendido": "avatar_sorprendido.png",
    "asustado": "avatar_asustado.png",
    "decepcionado": "avatar_decepcionado.png",
    "emocionado": "avatar_emocionado.png",
    "pensativo": "avatar_pensativo.png",
    "sospechoso": "avatar_sospechoso.png",
    "neutral": "avatar_neutral.png",
}


def _detectar_expresion(ruta_guion: Path) -> str:
    texto = ruta_guion.read_text(encoding="utf-8").lower()
    palabras = {
        "triste": ["triste", "llor", "perd", "muri", "solo", "abandon"],
        "enojado": ["enoj", "furios", "ira", "rabi", "odio", "venganza"],
        "sorprendido": ["sorprend", "increibl", "no podia creer", "descubri"],
        "asustado": ["miedo", "terror", "helo", "peligro", "amenaza"],
        "feliz": ["feliz", "alegre", "contento", "recuper"],
        "emocionado": ["emocion", "fascin", "alegria"],
        "sospechoso": ["sospech", "paranoi", "duda", "mentir"],
    }
    for expr, claves in palabras.items():
        if any(c in texto for c in claves):
            return expr
    return "neutral"


def componer(ruta_escena: Path, ruta_guion: Path, ruta_out: Path) -> None:
    expr = _detectar_expresion(ruta_guion)
    ruta_avatar = CARPETA_AVATAR / EXPRESION_POR_TONO.get(expr, "avatar_neutral.png")

    img = Image.open(ruta_escena).convert("RGB")
    ancho, alto = img.size

    if ruta_avatar.exists():
        try:
            avatar = Image.open(ruta_avatar).convert("RGBA")
            avatar = avatar.resize((int(ancho * 0.4), int(alto * 0.7)), Image.LANCZOS)
            pos = (ancho - avatar.width - 60, alto - avatar.height - 30)
            img.paste(avatar, pos, avatar)
        except Exception as e:
            print(f"  [AVISO] Avatar: {e}")

    draw = ImageDraw.Draw(img)
    try:
        fuente = ImageFont.truetype(str(FUENTE), 96)
    except Exception:
        fuente = ImageFont.load_default()

    titulo = ruta_guion.stem.replace("_", " ")[:42]
    y = 40
    for linea in textwrap.wrap(titulo, width=18)[:3]:
        draw.text((50, y), linea, fill=(255, 255, 255), font=fuente,
                  stroke_width=6, stroke_fill=(0, 0, 0))
        y += 110

    ruta_out.parent.mkdir(exist_ok=True, parents=True)
    img.save(str(ruta_out))
    print(f"  Miniatura: {ruta_out} (expresion: {expr})")


def main():
    parser = argparse.ArgumentParser(description="Compone miniatura final (escena + avatar + titulo).")
    parser.add_argument("guion", nargs="?", help="Ruta a un guion especifico")
    parser.add_argument("--procesar", action="store_true", help="Procesar todos los guiones")
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
        nombre_base = normalizar_nombre(guion.stem, max_largo=60)
        ruta_escena = CARPETA_ESCENAS / f"{nombre_base}.png"
        ruta_out = CARPETA_MINIATURAS / f"{nombre_base}_miniatura.png"
        if not ruta_escena.exists():
            print(f"  [AVISO] No existe escena para {nombre_base}. Genera con generar_miniaturas.py.")
            continue
        print(f"Procesando {guion.name}...")
        componer(ruta_escena, guion, ruta_out)

    print("\nListo. Miniaturas en output/miniaturas/.")


if __name__ == "__main__":
    main()
