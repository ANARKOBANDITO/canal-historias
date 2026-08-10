"""
generar_referencias.py

Genera clips de voz de referencia (de ~10 segundos cada uno) usando
edge-tts para los idiomas necesarios en la migracion a Chatterbox:
espanol LATAM, ingles US y portugues brasileno.

Los clips se guardan en storage/voces/ como archivos WAV y son usados
por generar_audio.py en modo --motor chatterbox como referencia de
voice cloning.

Uso (desde la raiz del proyecto):
    python src/generar_referencias.py              # genera las 3
    python src/generar_referencias.py --idioma en  # solo ingles

Se puede re-ejecutar para probar voces distintas hasta encontrar
la que funcione para el canal.
"""

import argparse
import asyncio
from pathlib import Path

try:
    import edge_tts
except ImportError:
    print("edge-tts no esta instalado. pip install edge-tts")
    raise SystemExit(1)

CARPETA_VOCES = Path("storage/voces")
DURACION_ESTIMADA = None  # edge-tts genera la duracion que corresponde al texto


VOCES_POR_IDIOMA = {
    "es": "es-MX-JorgeNeural",
    "en": "en-US-GuyNeural",
    "pt": "pt-BR-AntonioNeural",
}

TEXTOS_NEUTROS = {
    "es": (
        "Hola, bienvenidos a este canal de historias. "
        "Hoy les voy a contar algo que me paso hace unos dias y que todavia no puedo creer."
    ),
    "en": (
        "Welcome to the channel. "
        "Today I'm going to share a story that happened to me recently, "
        "and honestly I still can't believe it happened."
    ),
    "pt": (
        "Bem vindos ao canal. "
        "Hoje vou contar uma historia que aconteceu comigo ha pouco tempo, "
        "e sinceramente ainda nao consigo acreditar."
    ),
}


async def _generar_clip(texto: str, voz: str, ruta_salida: Path) -> None:
    communicate = edge_tts.Communicate(texto, voz)
    ruta_salida.parent.mkdir(exist_ok=True, parents=True)
    with open(ruta_salida, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
    print(f"  {ruta_salida.name} -> {ruta_salida.stat().st_size / 1024:.0f} KB")


def main():
    parser = argparse.ArgumentParser(
        description="Genera clips de voz de referencia con edge-tts para voice cloning con Chatterbox."
    )
    parser.add_argument("--idioma", choices=["es", "en", "pt"], default=None,
                        help="Idioma a generar (si no se especifica, se generan los tres)")
    parser.add_argument("--voz", type=str, default=None,
                        help="Voz edge-tts especifica (ignora la default del idioma)")
    args = parser.parse_args()

    idiomas_procesar = [args.idioma] if args.idioma else ["es", "en", "pt"]

    print("Generando clips de referencia para Chatterbox...\n")

    for idioma in idiomas_procesar:
        voz = args.voz or VOCES_POR_IDIOMA[idioma]
        texto = TEXTOS_NEUTROS[idioma]
        ruta = CARPETA_VOCES / f"referencia_{idioma}.mp3"
        print(f"[{idioma}] voz: {voz}")
        asyncio.run(_generar_clip(texto, voz, ruta))

    print(f"\nListo. Clips guardados en {CARPETA_VOCES}/")
    print("Escucha cada clip y re-ejecuta con --voz <nombre> si quieres cambiar alguna.")


if __name__ == "__main__":
    main()
