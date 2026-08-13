"""
generar_avatar.py

Genera el avatar del canal (conejito-robot estilo Snoo adaptado) a partir
de una foto de referencia del conejito del usuario, usando Qwen-Image-Edit-2511
en GPU (Vast.ai). Genera las 10 expresiones del canal en PNG transparente.

Expresiones: neutral, feliz, triste, enojado, sorprendido, asustado,
decepcionado, emocionado, pensativo, sospechoso.

Uso (en el pod, desde la raiz del proyecto):
    python src/generar_avatar.py "storage/fotos/conejito.jpg"
    python src/generar_avatar.py --foto "storage/fotos/WhatsApp Image 2026-08-11 at 02.25.58.jpeg" --solo neutral
"""

import argparse
from pathlib import Path

from PIL import Image

CARPETA_AVATAR = Path("storage/avatar")

PROMPT_BASE = (
    "Convierte esta foto de un conejo en un avatar de canal estilo mascota: "
    "un conejito-robot animado estilo Snoo (NO el logo de Reddit), cabeza redonda "
    "tipo peluche, ojos grandes expresivos, cuerpo simple, fondo TRANSPARENTE, "
    "ilustracion limpia para YouTube. Expresion facial: {expresion}. "
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


def _recortar_transparente(ruta_png: Path) -> None:
    """Recorta el PNG a la bounding box no transparente (limpieza del avatar)."""
    img = Image.open(ruta_png)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    alpha = img.getchannel("A")
    bbox = alpha.getbbox()
    if bbox:
        img = img.crop(bbox)
    img.save(ruta_png)


def generar_avatar(ruta_foto: Path, expresiones: list[str], solo: str | None = None) -> None:
    import torch
    from diffusers import QwenImageEditPipeline

    cargas = {"torch_dtype": torch.bfloat16}
    if torch.cuda.is_available() and torch.cuda.get_device_properties(0).total_memory < 40 * 2**30:
        print("  [INFO] GPU < 40GB: cargando con cuantizacion 4-bit...")
        cargas["load_in_4bit"] = True

    print("Cargando Qwen-Image-Edit-2511...")
    pipe = QwenImageEditPipeline.from_pretrained("Qwen/Qwen-Image-Edit-2511", **cargas)
    pipe.to("cuda" if torch.cuda.is_available() else "cpu")

    foto = Image.open(ruta_foto).convert("RGB")
    CARPETA_AVATAR.mkdir(exist_ok=True, parents=True)

    for expr in expresiones:
        if solo and expr != solo:
            continue
        print(f"Generando avatar_{expr}.png ...")
        prompt = PROMPT_BASE.format(expresion=EXPRESIONES[expr])
        img = pipe(prompt=prompt, image=foto, guidance_scale=4.0).images[0]
        ruta_out = CARPETA_AVATAR / f"avatar_{expr}.png"
        img.save(ruta_out)
        try:
            _recortar_transparente(ruta_out)
        except Exception:
            pass
        print(f"  -> {ruta_out}")

    print("\nAvatar listo en storage/avatar/.")


def main():
    parser = argparse.ArgumentParser(description="Genera el avatar del canal con Qwen-Image-Edit.")
    parser.add_argument("foto", nargs="?", help="Ruta a la foto del conejito de referencia")
    parser.add_argument("--foto", dest="foto_alt", help="Alternativa a posicion: --foto")
    parser.add_argument("--solo", choices=list(EXPRESIONES.keys()), default=None,
                        help="Generar solo una expresion")
    parser.add_argument("--todas", action="store_true", help="Generar las 10 expresiones")
    args = parser.parse_args()

    foto = Path(args.foto or args.foto_alt or "")
    if not foto.exists():
        candidatos = sorted(Path("storage/fotos").glob("*.jpeg")) + sorted(Path("storage/fotos").glob("*.jpg"))
        if not candidatos:
            raise SystemExit("No se encontro la foto del conejito en storage/fotos/.")
        foto = candidatos[0]
        print(f"Usando foto por defecto: {foto.name}")

    expresiones = list(EXPRESIONES.keys()) if args.todas else ([args.solo] if args.solo else ["neutral"])
    generar_avatar(foto, expresiones)


if __name__ == "__main__":
    main()
