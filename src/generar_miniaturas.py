"""
generar_miniaturas.py

Genera la miniatura para cada video segun el tema del guion usando
Qwen-Image-Edit-2511 (Apache 2.0, uso comercial) en GPU (Vast.ai)
o por API si se provee. Compone escena + avatar con expresion + titulo
con Pillow para la miniatura final de YouTube.

Uso (desde la raiz del proyecto):
    python src/generar_miniaturas.py "output/guiones_listos/guion.txt"
    python src/generar_miniaturas.py --procesar
"""

import argparse
import random
import subprocess
from pathlib import Path

from utilidades import normalizar_nombre

CARPETA_GUIONES = Path("output/guiones_listos")
CARPETA_MINIATURAS = Path("output/miniaturas")
CARPETA_AVATAR = Path("storage/avatar")
CARPETA_ESCENAS = Path("output/miniaturas/_escenas")

# Backend de generacion de escena.
# "local" -> Qwen-Image-Edit en GPU local (Vast.ai). Requiere el modelo instalado.
# "api"   -> endpoint remoto (se configurara con la API de Qwen).
BACKEND = "local"

# Mapeo expresion -> archivo avatar (si se detecta el tono del guion)
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
    """Heuristica simple para elegir expresion segun el texto del guion."""
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


def generar_escena(ruta_guion: Path, ruta_png: Path, backend: str = BACKEND) -> None:
    """Genera la escena de fondo con Qwen-Image-Edit segun el tema del guion."""
    ruta_png.parent.mkdir(exist_ok=True, parents=True)
    titulo = ruta_guion.stem.replace("_", " ").title()
    prompt = f"Escena cinematografica dramatica para video de historia de terror/confesion sobre: {titulo}. Estilo YouTube thumbnail, alta calidad, iluminacion dramatica."

    if backend == "api":
        # TODO: conectar con la API de Qwen cuando el usuario la provea.
        print("  [INFO] Backend API no configurado aun. Se usara fondo generico.")
        _fondo_generico(ruta_png)
        return

    # Backend local (Vast.ai): Qwen-Image-Edit con diffusers
    try:
        import torch
        from diffusers import QwenImageEditPipeline
        from diffusers.utils import load_image
        from PIL import Image

        pipe = QwenImageEditPipeline.from_pretrained(
            "Qwen/Qwen-Image-Edit-2511", torch_dtype=torch.bfloat16
        )
        pipe.to("cuda" if torch.cuda.is_available() else "cpu")

        # imagen base negra (edit tool no requiere imagen si se usa mask opcional)
        base = Image.new("RGB", (1344, 768), (20, 20, 20))
        img = pipe(prompt=prompt, image=base, guidance_scale=4.0).images[0]
        img.save(str(ruta_png))
        print(f"  Escena generada (Qwen local): {ruta_png}")
    except ImportError as e:
        print(f"  [INFO] diffusers no disponible ({e}). Se usara fondo generico.")
        _fondo_generico(ruta_png)
    except Exception as e:
        print(f"  [INFO] No se pudo generar con Qwen ({e}). Se usara fondo generico.")
        _fondo_generico(ruta_png)


def _fondo_generico(ruta_png: Path) -> None:
    """Fondo de relleno mientras no hay GPU/API: gradiente simple."""
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (1344, 768), (30, 30, 45))
        draw = ImageDraw.Draw(img)
        for i in range(768):
            color = (30 + i // 20, 30, 45 + i // 30)
            draw.line([(0, i), (1344, i)], fill=color)
        img.save(str(ruta_png))
    except Exception:
        pass


def componer_miniatura(ruta_escena: Path, ruta_guion: Path, ruta_out: Path) -> None:
    """Compone escena + avatar con expresion + titulo usando Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  Pillow no instalado.")
        return

    expr = _detectar_expresion(ruta_guion)
    ruta_avatar = CARPETA_AVATAR / EXPRESION_POR_TONO.get(expr, "avatar_neutral.png")

    img = Image.open(ruta_escena).convert("RGB")
    ancho, alto = img.size

    # Avatar redondeado (derecha-abajo)
    if ruta_avatar.exists():
        try:
            avatar = Image.open(ruta_avatar).convert("RGBA").resize((int(ancho * 0.4), int(alto * 0.7)), Image.LANCZOS)
            pos = (ancho - avatar.width - 60, alto - avatar.height - 30)
            img.paste(avatar, pos, avatar)
        except Exception as e:
            print(f"  [AVISO] Avatar: {e}")

    # Titulo
    draw = ImageDraw.Draw(img)
    try:
        fuente = ImageFont.truetype("storage/Montserrat-Bold.ttf", 96)
    except Exception:
        fuente = ImageFont.load_default()
    titulo = ruta_guion.stem.replace("_", " ")[:42]
    import textwrap
    lineas = textwrap.wrap(titulo, width=18)
    y = 40
    for linea in lineas[:3]:
        draw.text((50, y), linea, fill=(255, 255, 255), font=fuente,
                  stroke_width=6, stroke_fill=(0, 0, 0))
        y += 110

    ruta_out.parent.mkdir(exist_ok=True, parents=True)
    img.save(str(ruta_out))
    print(f"  Miniatura: {ruta_out} (expresion: {expr})")


def procesar_guion(ruta_guion: Path, backend: str) -> None:
    nombre_base = normalizar_nombre(ruta_guion.stem, max_largo=60)
    ruta_escena = CARPETA_ESCENAS / f"{nombre_base}.png"
    ruta_out = CARPETA_MINIATURAS / f"{nombre_base}_miniatura.png"

    if not ruta_escena.exists():
        generar_escena(ruta_guion, ruta_escena, backend)
    componer_miniatura(ruta_escena, ruta_guion, ruta_out)


def main():
    parser = argparse.ArgumentParser(description="Genera miniaturas para cada video segun el tema del guion.")
    parser.add_argument("guion", nargs="?", help="Ruta a un guion especifico")
    parser.add_argument("--procesar", action="store_true", help="Procesar todos los guiones")
    parser.add_argument("--backend", choices=["local", "api"], default=BACKEND,
                        help="Backend para generar la escena (default: local)")
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
        procesar_guion(guion, args.backend)

    print("\nListo. Miniaturas en output/miniaturas/.")


if __name__ == "__main__":
    main()
