"""
generar_avatar.py

Genera el avatar del canal (conejito-robot estilo Snoo adaptado) a partir
de una foto de referencia del conejito del usuario, usando Qwen-Image-Edit-2511
por API (Replicate). Genera las 10 expresiones del canal en PNG transparente.

Expresiones: neutral, feliz, triste, enojado, sorprendido, asustado,
decepcionado, emocionado, pensativo, sospechoso.

La foto de referencia se manda como data URL (<= 256 KB). El fondo se pide
blanco liso y se quita en post-proceso (transparencia) con Pillow.

Uso (desde la raiz del proyecto):
    python src/generar_avatar.py "storage/fotos/conejito.jpg"
    python src/generar_avatar.py --foto "storage/fotos/WhatsApp Image 2026-08-11 at 02.25.58.jpeg" --solo neutral
    python src/generar_avatar.py --todas
"""

import argparse
from pathlib import Path

from PIL import Image

from qwen_api import data_url, descargar, ejecutar_prediccion

CARPETA_AVATAR = Path("storage/avatar")
CARPETA_SRC = CARPETA_AVATAR / "_src"

PROMPT_BASE = (
    "Convierte esta foto de un conejo en un avatar de canal estilo mascota: "
    "un conejito-robot animado estilo Snoo (NO el logo de Reddit), cabeza redonda "
    "tipo peluche, ojos grandes expresivos, cuerpo simple, sobre un fondo BLANCO "
    "LISO Y UNIFORME, ilustracion limpia para YouTube. Expresion facial: {expresion}. "
    "Sin texto, sin logotipos, centrado, recorte de busto."
)

EXPRESIONES = {
    "neutral": "neutral, calma",
    "feliz": "feliz, sonrisa amplia",
    "triste": "triste, ojos bajos",
    "enojado": "enojado, cejas fruncidas",
    "sorprendido": "sorprendido, ojos abiertos y boca pequena",
    "asustado": "asustado, ojos muy abiertos",
    "decepcionado": "decepcionado, labio apretado",
    "emocionado": "emocionado, brillo en los ojos",
    "pensativo": "pensativo, mirada hacia arriba",
    "sospechoso": "sospechoso, ojos entrecerrados",
}


def _fondo_transparente(ruta_src: Path, ruta_out: Path) -> None:
    """Quita el fondo blanco liso (post-proceso) y recorta a la silueta."""
    img = Image.open(ruta_src).convert("RGBA")
    w, h = img.size
    px = img.load()
    umbral = 90
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            dist = abs(r - 255) + abs(g - 255) + abs(b - 255)
            if dist < umbral:
                alpha = max(0, int(255 * dist / umbral))
                px[x, y] = (r, g, b, alpha)
    alpha = img.getchannel("A")
    bbox = alpha.getbbox()
    if bbox:
        img = img.crop(bbox)
    ruta_out.parent.mkdir(parents=True, exist_ok=True)
    img.save(ruta_out)


def generar_avatar(ruta_foto: Path, expresiones: list[str]) -> None:
    print(f"Foto de referencia: {ruta_foto.name} ({ruta_foto.stat().st_size // 1024} KB)")
    foto_url = data_url(ruta_foto)
    CARPETA_SRC.mkdir(parents=True, exist_ok=True)

    for expr in expresiones:
        print(f"Generando avatar_{expr}.png ...")
        prompt = PROMPT_BASE.format(expresion=EXPRESIONES[expr])
        url = ejecutar_prediccion(prompt, [foto_url], aspect="1:1", formato="png")
        ruta_src = CARPETA_SRC / f"avatar_{expr}.png"
        descargar(url, ruta_src)
        ruta_out = CARPETA_AVATAR / f"avatar_{expr}.png"
        try:
            _fondo_transparente(ruta_src, ruta_out)
            print(f"  -> {ruta_out} (transparente)")
        except Exception as e:
            ruta_src.replace(ruta_out)
            print(f"  -> {ruta_out} (sin transparencia: {e})")

    print("\nAvatar listo en storage/avatar/.")


def main():
    parser = argparse.ArgumentParser(description="Genera el avatar del canal con Qwen-Image-Edit (Replicate).")
    parser.add_argument("foto", nargs="?", help="Ruta a la foto del conejito de referencia")
    parser.add_argument("--foto", dest="foto_alt", help="Alternativa a posicion: --foto")
    parser.add_argument("--solo", choices=list(EXPRESIONES.keys()), default=None,
                        help="Generar solo una expresion")
    parser.add_argument("--todas", action="store_true", help="Generar las 10 expresiones")
    args = parser.parse_args()

    foto_arg = args.foto or args.foto_alt
    if not foto_arg:
        candidatos = sorted(Path("storage/fotos").glob("*.jpeg")) + sorted(Path("storage/fotos").glob("*.jpg"))
        if not candidatos:
            raise SystemExit("No se encontro la foto del conejito en storage/fotos/.")
        foto = candidatos[0]
        print(f"Usando foto por defecto: {foto.name}")
    else:
        foto = Path(foto_arg)
        if not foto.exists():
            raise SystemExit(f"No existe la foto: {foto}")

    expresiones = list(EXPRESIONES.keys()) if args.todas else ([args.solo] if args.solo else ["neutral"])
    generar_avatar(foto, expresiones)


if __name__ == "__main__":
    main()
