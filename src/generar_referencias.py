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
import subprocess
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

# Voces candidatas para elegir el narrador del canal (edge-tts, espanol).
# Se usan como referencia de voice cloning en el pod (Fase 2.5).
CANDIDATAS_ES = {
    "hombre": [
        ("jorge", "es-MX-JorgeNeural"),
        ("alvaro", "es-ES-AlvaroNeural"),
        ("tomas", "es-AR-TomasNeural"),
        ("gonzalo", "es-CO-GonzaloNeural"),
        ("alonso", "es-US-AlonsoNeural"),
    ],
    "mujer": [
        ("dalia", "es-MX-DaliaNeural"),
        ("elvira", "es-ES-ElviraNeural"),
        ("elena", "es-AR-ElenaNeural"),
        ("salome", "es-CO-SalomeNeural"),
        ("paloma", "es-US-PalomaNeural"),
    ],
}

TEXTO_CANDIDATAS_ES = (
    "Bienvenidos al canal. Hoy les traigo una historia real de traicion, "
    "de esas que te dejan sin palabras y que nadie se anima a contar. "
    "Si llegan hasta el final, van a entender por que nunca mas confie "
    "de la misma manera."
)


def _ffmpeg() -> str:
    """Devuelve la ruta a ffmpeg (puede no estar en el PATH en Windows)."""
    import os
    import shutil

    which = shutil.which("ffmpeg")
    if which:
        return which
    candidata = Path(os.environ.get("LOCALAPPDATA", "")) / "ffmpeg"
    if candidata.exists():
        for p in candidata.rglob("ffmpeg.exe"):
            return str(p)
    return "ffmpeg"


async def _generar_clip(texto: str, voz: str, ruta_salida: Path) -> None:
    communicate = edge_tts.Communicate(texto, voz)
    ruta_salida.parent.mkdir(exist_ok=True, parents=True)
    with open(ruta_salida, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
    print(f"  {ruta_salida.name} -> {ruta_salida.stat().st_size / 1024:.0f} KB")


def _mp3_a_wav(ruta_mp3: Path, ruta_wav: Path) -> None:
    """Convierte el clip a WAV mono 44.1k (mejor para voice cloning)."""
    subprocess.run([
        _ffmpeg(), "-y", "-i", str(ruta_mp3),
        "-ac", "1", "-ar", "44100", str(ruta_wav),
    ], check=True, capture_output=True)


def generar_candidatas() -> None:
    """Genera los 10 clips de referencia candidatos (5H + 5M) como WAV."""
    import subprocess

    carpeta = CARPETA_VOCES / "candidatas"
    carpeta.mkdir(exist_ok=True, parents=True)
    print("Generando candidatas de voz (espanol) para voice cloning...\n")

    for genero, voces in CANDIDATAS_ES.items():
        for label, voz in voces:
            prefijo = "h" if genero == "hombre" else "m"
            ruta_mp3 = carpeta / f"es_{prefijo}_{label}.mp3"
            ruta_wav = carpeta / f"es_{prefijo}_{label}.wav"
            print(f"[{genero}] {voz}")
            asyncio.run(_generar_clip(TEXTO_CANDIDATAS_ES, voz, ruta_mp3))
            try:
                _mp3_a_wav(ruta_mp3, ruta_wav)
                print(f"  WAV: {ruta_wav.name} ({ruta_wav.stat().st_size / 1024:.0f} KB)")
            except Exception as e:
                print(f"  [AVISO] No se pudo convertir a WAV: {e}")

    print(f"\nListo. Candidatas en {carpeta}/")
    print("Verifica que los WAV no esten rotos antes de subirlos al pod.")


def main():
    parser = argparse.ArgumentParser(
        description="Genera clips de voz de referencia con edge-tts para voice cloning con Chatterbox."
    )
    parser.add_argument("--idioma", choices=["es", "en", "pt"], default=None,
                        help="Idioma a generar (si no se especifica, se generan los tres)")
    parser.add_argument("--voz", type=str, default=None,
                        help="Voz edge-tts especifica (ignora la default del idioma)")
    parser.add_argument("--candidatas", action="store_true",
                        help="Generar las 10 voces candidatas (5H + 5M) en storage/voces/candidatas/")
    args = parser.parse_args()

    if args.candidatas:
        generar_candidatas()
        return

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
