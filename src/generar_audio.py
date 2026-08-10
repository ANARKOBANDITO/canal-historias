"""
generar_audio.py

Genera locucion narrada (audio MP3) a partir de los guiones en
output/guiones_listos/ usando Kokoro (CPU), edge-tts (nube), o
Chatterbox (GPU local, voice cloning). Auto-detecta genero e idioma
del metadato del guion.

Uso (desde la raiz del proyecto):
    # Kokoro (local, espanol)
    python src/generar_audio.py --cantidad 5 --genero hombre
    python src/generar_audio.py "output/guiones_listos/mi_guion.txt" --motor kokoro

    # edge-tts (rapido, nube)
    python src/generar_audio.py --cantidad 3 --motor edge --genero hombre

    # Chatterbox (GPU, voice cloning, multi-idioma)
    python src/generar_audio.py --cantidad 2 --motor chatterbox --idioma en
    python src/generar_audio.py "guion.txt" --motor chatterbox --idioma pt
"""

import argparse
import asyncio
import subprocess
from pathlib import Path

from utilidades import normalizar_nombre

# ── Kokoro (opcional, para CPU local) ────────────────────────
try:
    from kokoro_onnx import Kokoro
    HAY_KOKORO = True
except ImportError:
    HAY_KOKORO = False

# ── edge-tts (opcional, para nube gratis) ────────────────────
try:
    import edge_tts
    HAY_EDGE_TTS = True
except ImportError:
    HAY_EDGE_TTS = False

# ── Chatterbox (opcional, para GPU con voice cloning) ────────
try:
    import torchaudio as ta
    import torch
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    HAY_CHATTERBOX = True
except ImportError:
    HAY_CHATTERBOX = False

# ── Carpetas ─────────────────────────────────────────────────
CARPETA_GUIONES = Path("output/guiones_listos")
CARPETA_AUDIO = Path("output/audio")
CARPETA_VOCES = Path("storage/voces")

# ── Voces Kokoro ─────────────────────────────────────────────
VOCES_KOKORO = {
    "hombre": "em_alex",
    "mujer": "ef_dora",
}
MODELO_KOKORO = Path("storage/kokoro-v1.0.onnx")
VOCES_KOKORO_BIN = Path("storage/voices-v1.0.bin")

# ── Voces edge-tts ───────────────────────────────────────────
VOZ_EDGE_POR_GENERO = {
    "hombre": "es-MX-JorgeNeural",
    "mujer": "es-MX-DaliaNeural",
}

# ── Chatterbox ───────────────────────────────────────────────
VOZ_REFERENCIA_POR_IDIOMA = {
    "es": "referencia_es.mp3",
    "en": "referencia_en.mp3",
    "pt": "referencia_pt.mp3",
}
DEVICE_CHATTERBOX = "cuda" if torch.cuda.is_available() else "cpu"

# ── Singletons ───────────────────────────────────────────────
_instancia_kokoro = None
_instancia_chatterbox = None


# ═══════════════════════════════════════════════════════════════
#  Kokoro
# ═══════════════════════════════════════════════════════════════

def _obtener_kokoro() -> Kokoro:
    global _instancia_kokoro
    if _instancia_kokoro is None:
        if not MODELO_KOKORO.exists():
            raise FileNotFoundError(f"No se encontro {MODELO_KOKORO}")
        _instancia_kokoro = Kokoro(str(MODELO_KOKORO), str(VOCES_KOKORO_BIN))
    return _instancia_kokoro


def _generar_kokoro(texto: str, voz: str, ruta_mp3: Path, rate: float = 1.0) -> None:
    kokoro = _obtener_kokoro()
    ruta_wav = ruta_mp3.with_suffix(".wav")
    import soundfile as sf
    samples, sample_rate = kokoro.create(texto, voice=voz, speed=rate, lang="es")
    sf.write(str(ruta_wav), samples, sample_rate)
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(ruta_wav), "-codec:a", "libmp3lame", "-ar", "44100", "-qscale:a", "2",
        str(ruta_mp3),
    ], check=True, capture_output=True)
    ruta_wav.unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════
#  edge-tts
# ═══════════════════════════════════════════════════════════════

async def _generar_edge(texto: str, voz: str, ruta_mp3: Path, rate_str: str) -> None:
    communicate = edge_tts.Communicate(texto, voz, rate=rate_str)
    with open(ruta_mp3, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])


# ═══════════════════════════════════════════════════════════════
#  Chatterbox (GPU)
# ═══════════════════════════════════════════════════════════════

def _obtener_chatterbox(device: str = DEVICE_CHATTERBOX):
    global _instancia_chatterbox
    if _instancia_chatterbox is None:
        if not HAY_CHATTERBOX:
            raise RuntimeError("chatterbox-tts no esta instalado. pip install chatterbox-tts")
        print(f"  Cargando Chatterbox Multilingual V3 en {device}...")
        _instancia_chatterbox = ChatterboxMultilingualTTS.from_pretrained(
            device=device, t3_model="v3"
        )
    return _instancia_chatterbox


def _generar_chatterbox(texto: str, idioma: str, ruta_mp3: Path,
                        ruta_ref: Path | None = None, device: str = DEVICE_CHATTERBOX) -> None:
    model = _obtener_chatterbox(device)
    ruta_wav = ruta_mp3.with_suffix(".wav")

    kwargs = {"language_id": idioma}
    if ruta_ref and ruta_ref.exists():
        kwargs["audio_prompt_path"] = str(ruta_ref)
        print(f"  [voice cloning: {ruta_ref.name}]")

    wav = model.generate(texto, **kwargs)
    ta.save(str(ruta_wav), wav, model.sr)

    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(ruta_wav), "-codec:a", "libmp3lame", "-ar", "44100", "-qscale:a", "2",
        str(ruta_mp3),
    ], check=True, capture_output=True)
    ruta_wav.unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════
#  Lectura de guiones
# ═══════════════════════════════════════════════════════════════

def _leer_guion(ruta: Path) -> tuple[str, str | None, str | None]:
    lineas = ruta.read_text(encoding="utf-8").split("\n")
    genero = None
    idioma_meta = None
    inicio_contenido = 0

    for i, linea in enumerate(lineas):
        if linea.startswith("[GENERO:"):
            genero = linea.split(":", 1)[1].strip().rstrip("]").strip()
        elif linea.startswith("[IDIOMA:"):
            idioma_meta = linea.split(":", 1)[1].strip().rstrip("]").strip()
        elif linea.strip() == "":
            continue
        else:
            inicio_contenido = i
            break

    texto_limpio = "\n".join(lineas[inicio_contenido:])
    return texto_limpio, genero, idioma_meta


def _formato_rate_edge(raw: str) -> str:
    raw = raw.strip()
    if not raw.endswith("%"):
        raw += "%"
    if not (raw.startswith("+") or raw.startswith("-")):
        raw = "+" + raw
    return raw


# ═══════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Genera audio narrado desde guiones (Kokoro, edge-tts o Chatterbox).")
    parser.add_argument("guion", nargs="?", help="Ruta a un guion especifico")
    parser.add_argument("--cantidad", type=int, default=None, help="Cantidad de guiones a procesar")
    parser.add_argument("--genero", choices=["hombre", "mujer"], default="mujer",
                        help="Genero del narrador (kokoro / edge-tts)")
    parser.add_argument("--voz", type=str, default=None, help="Voz especifica (ignora --genero)")
    parser.add_argument("--motor", choices=["kokoro", "edge", "chatterbox"], default="kokoro",
                        help="Motor TTS (default: kokoro)")
    parser.add_argument("--idioma", choices=["es", "en", "pt"], default=None,
                        help="Idioma del contenido (chatterbox). Si no se pasa, se lee de [IDIOMA:] en el guion")
    parser.add_argument("--rate", type=float, default=1.0, help="Velocidad Kokoro (0.5-2.0)")
    parser.add_argument("--rate-edge", type=str, default="+0%", help="Velocidad edge-tts (ej: -10%%)")
    args = parser.parse_args()

    guiones: list[Path] = []
    if args.guion:
        guiones = [Path(args.guion)]
    elif args.cantidad:
        if not CARPETA_GUIONES.exists():
            print(f"No existe {CARPETA_GUIONES}/")
            return
        guiones = sorted(CARPETA_GUIONES.glob("*.txt"))[: args.cantidad]
    else:
        print("Debes especificar un guion o usar --cantidad.")
        return

    if not guiones:
        print("No se encontraron guiones para procesar.")
        return

    CARPETA_AUDIO.mkdir(exist_ok=True)

    for i, guion in enumerate(guiones, 1):
        print(f"[{i}/{len(guiones)}] {guion.name}...")

        texto, genero_meta, idioma_meta = _leer_guion(guion)
        idioma_efectivo = args.idioma or idioma_meta or "es"
        nombre_base = normalizar_nombre(guion.stem, max_largo=60)
        ruta_mp3 = CARPETA_AUDIO / f"{nombre_base}.mp3"

        if args.motor == "kokoro":
            if not HAY_KOKORO:
                print("  kokoro-onnx no esta instalado. Usa --motor edge.")
                return
            voz_forzada = args.voz is not None
            voz_default = VOCES_KOKORO[args.genero]
            if not voz_forzada and genero_meta and genero_meta in VOCES_KOKORO:
                voz_efectiva = VOCES_KOKORO[genero_meta]
                print(f"  [GENERO detectado: {genero_meta} -> {voz_efectiva}]")
            else:
                voz_efectiva = args.voz or voz_default
            _generar_kokoro(texto, voz_efectiva, ruta_mp3, args.rate)

        elif args.motor == "edge":
            if not HAY_EDGE_TTS:
                print("  edge-tts no esta instalado. Usa --motor kokoro.")
                return
            voz_default = VOZ_EDGE_POR_GENERO[args.genero]
            voz_efectiva = args.voz or voz_default
            asyncio.run(_generar_edge(texto, voz_efectiva, ruta_mp3,
                                      _formato_rate_edge(args.rate_edge)))

        elif args.motor == "chatterbox":
            if not HAY_CHATTERBOX:
                print("  chatterbox-tts no esta instalado. Instalalo con: pip install chatterbox-tts")
                return
            ruta_ref = CARPETA_VOCES / VOZ_REFERENCIA_POR_IDIOMA.get(idioma_efectivo, "")
            if not ruta_ref.exists():
                print(f"  [AVISO] No se encontro referencia {ruta_ref}. Generando con voz default.")
                ruta_ref = None
            print(f"  [IDIOMA: {idioma_efectivo}]")
            _generar_chatterbox(texto, idioma_efectivo, ruta_mp3, ruta_ref)

        print(f"  Audio : {ruta_mp3} ({ruta_mp3.stat().st_size / 1024:.0f} KB)")

    print(f"\nListo. {len(guiones)} guiones procesados con {args.motor}.")


if __name__ == "__main__":
    main()
