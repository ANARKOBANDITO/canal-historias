"""
generar_cta_parte.py

Genera la llamada a la accion al final de cada parte del video 9:16:
"like para la parte N" (donde N es la parte siguiente). Incluye:
  - Overlay visual (Pillow -> PNG) con el texto
  - Audio narrado (edge-tts o el motor TTS que se use) de la frase

Uso (desde la raiz del proyecto):
    python src/generar_cta_parte.py --parte 2 --siguiente 3 --idioma es
    python src/generar_cta_parte.py --procesar
"""

import argparse
import asyncio
import subprocess
from pathlib import Path

CARPETA_CTA = Path("output/cta")
FFMPEG = "ffmpeg"

# Motor TTS para narrar el CTA. "edge" = edge-tts (gratis). "chatterbox" = voice cloning GPU.
MOTOR_CTA = "edge"

VOZ_EDGE_POR_IDIOMA = {
    "es": "es-MX-JorgeNeural",
    "en": "en-US-GuyNeural",
    "pt": "pt-BR-AntonioNeural",
}

TEXTO_CTA_POR_IDIOMA = {
    "es": "¡Dale like para la parte {n}!",
    "en": "Like for part {n}!",
    "pt": "Deixe o like para a parte {n}!",
}


def generar_overlay(ruta_png: Path, texto: str) -> None:
    """Crea un PNG 1080x300 con el texto del CTA."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGBA", (1080, 300), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            fuente = ImageFont.truetype("storage/Montserrat-Bold.ttf", 72)
        except Exception:
            fuente = ImageFont.load_default()
        # fondo semi-transparente
        draw.rounded_rectangle([40, 40, 1040, 260], radius=40, fill=(0, 0, 0, 160))
        # texto centrado
        try:
            bbox = draw.textbbox((0, 0), texto, font=fuente)
            w = bbox[2] - bbox[0]
            x = (1080 - w) // 2
            draw.text((x, 90), texto, fill=(255, 255, 255), font=fuente)
        except Exception:
            draw.text((400, 100), texto, fill=(255, 255, 255), font=fuente)
        ruta_png.parent.mkdir(exist_ok=True, parents=True)
        img.save(str(ruta_png))
        print(f"  Overlay CTA: {ruta_png}")
    except ImportError:
        print("  Pillow no instalado. No se genero overlay.")


async def generar_audio_edge(ruta_mp3: Path, texto: str, idioma: str) -> None:
    import edge_tts
    voz = VOZ_EDGE_POR_IDIOMA.get(idioma, "es-MX-JorgeNeural")
    communicate = edge_tts.Communicate(texto, voz)
    with open(ruta_mp3, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
    print(f"  Audio CTA: {ruta_mp3}")


def generar_cta(parte: int, siguiente: int, idioma: str, motor: str = MOTOR_CTA) -> tuple[Path, Path]:
    texto = TEXTO_CTA_POR_IDIOMA.get(idioma, TEXTO_CTA_POR_IDIOMA["es"]).format(n=siguiente)
    nombre = f"cta_parte_{parte:02d}_{idioma}"
    ruta_png = CARPETA_CTA / f"{nombre}.png"
    ruta_mp3 = CARPETA_CTA / f"{nombre}.mp3"
    CARPETA_CTA.mkdir(exist_ok=True, parents=True)

    generar_overlay(ruta_png, texto)

    if motor == "edge":
        asyncio.run(generar_audio_edge(ruta_mp3, texto, idioma))
    else:
        # TODO: motor chatterbox local (Vast.ai) cuando este configurado.
        print(f"  [INFO] Motor '{motor}' no configurado. Audio CTA omitido.")
        ruta_mp3 = None

    return ruta_png, ruta_mp3


def main():
    parser = argparse.ArgumentParser(description="Genera CTA 'like para la parte N' (overlay + audio).")
    parser.add_argument("--parte", type=int, default=1, help="Numero de la parte actual")
    parser.add_argument("--siguiente", type=int, default=None, help="Numero de la parte siguiente (default: parte+1)")
    parser.add_argument("--idioma", choices=["es", "en", "pt"], default="es")
    parser.add_argument("--motor", choices=["edge", "chatterbox"], default=MOTOR_CTA)
    args = parser.parse_args()

    siguiente = args.siguiente if args.siguiente else args.parte + 1
    generar_cta(args.parte, siguiente, args.idioma, args.motor)
    print("\nListo. CTA en output/cta/.")


if __name__ == "__main__":
    main()
