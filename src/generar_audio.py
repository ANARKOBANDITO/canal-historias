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

from __future__ import annotations

import argparse
import asyncio
import os
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

# ── Chatterbox API (serverless RunPod) ───────────────────────
try:
    import requests
    HAY_REQUESTS = True
except ImportError:
    HAY_REQUESTS = False

# Endpoint serverless Chatterbox Turbo (RunPod)
CHATTERBOX_API_URL = "https://api.runpod.ai/v2/chatterbox-turbo/runsync"

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
DEVICE_CHATTERBOX = "cuda" if (HAY_CHATTERBOX and torch.cuda.is_available()) else "cpu"

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
        # Vast.ai: el acelerador Xet de HF falla en hosts del marketplace; usar HTTPS.
        os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
        print(f"  Cargando Chatterbox Multilingual V3 en {device}...")
        _instancia_chatterbox = ChatterboxMultilingualTTS.from_pretrained(
            device=device
        )
    return _instancia_chatterbox


def _dividir_texto(texto: str, max_palabras: int = 180) -> list[str]:
    """Divide el texto en fragmentos de ~max_palabras para TTS por fragmentos.

    Chatterbox hardcodea max_new_tokens=1000, por lo que un guion entero de
    20 min excede el limite y crashea en CUDA. Se genera por fragmentos y se
    concatenan los WAV despues.
    """
    oraciones = texto.replace("\n", " ").split(". ")
    fragmentos: list[str] = []
    actual: list[str] = []
    for oracion in oraciones:
        oracion = oracion.strip()
        if not oracion:
            continue
        actual.append(oracion)
        if sum(len(o.split()) for o in actual) >= max_palabras:
            fragmentos.append(". ".join(actual).strip() + ".")
            actual = []
    if actual:
        fragmentos.append(". ".join(actual).strip() + ".")
    return [f for f in fragmentos if f.strip()]


def _generar_chatterbox(texto: str, idioma: str, ruta_mp3: Path,
                        ruta_ref: Path | None = None, device: str = DEVICE_CHATTERBOX) -> None:
    model = _obtener_chatterbox(device)
    ruta_wav = ruta_mp3.with_suffix(".wav")

    fragmentos = _dividir_texto(texto)
    print(f"  [chatterbox] {len(fragmentos)} fragmentos ({sum(len(f.split()) for f in fragmentos)} palabras)")

    # Voice cloning: preparar condicionals UNA vez (modelo cachea self.conds)
    kwargs = {"language_id": idioma}
    if ruta_ref and ruta_ref.exists():
        print(f"  [voice cloning: {ruta_ref.name}]")
        model.prepare_conditionals(str(ruta_ref), exaggeration=0.5)

    wavs = []
    for i, frag in enumerate(fragmentos, 1):
        print(f"    fragmento {i}/{len(fragmentos)}...")
        wav = model.generate(frag, **kwargs)
        wavs.append(wav.squeeze(0))
    wav_final = torch.cat(wavs, dim=0).unsqueeze(0)
    ta.save(str(ruta_wav), wav_final, model.sr)

    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(ruta_wav), "-codec:a", "libmp3lame", "-ar", "44100", "-qscale:a", "2",
        str(ruta_mp3),
    ], check=True, capture_output=True)
    ruta_wav.unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════
#  Chatterbox API (serverless RunPod, voice cloning via URL)
# ═══════════════════════════════════════════════════════════════

def _generar_chatterbox_api(texto: str, idioma: str, ruta_mp3: Path,
                            ruta_ref: Path | None = None,
                            voice_url: str | None = None) -> None:
    """Genera audio con la API serverless Chatterbox Turbo de RunPod.
    $0.001/seg. El audio_url expira a los 7 dias, se descarga al momento."""
    import os
    import urllib.request

    api_key = os.environ.get("RUNPOD_API_KEY")
    if not api_key:
        raise RuntimeError("RUNPOD_API_KEY no configurada. Exportala antes de usar --motor chatterbox-api.")

    # voice_url explicita o subir la referencia a GitHub raw (por convencion)
    ref_url = voice_url
    if not ref_url and ruta_ref and ruta_ref.exists():
        # TODO: subir storage/voces/ a un repo publico y construir la URL raw.
        # Por defecto se usa voz preset si no hay URL.
        print(f"  [voice cloning] Usar voice_url con {ruta_ref.name}. Se usara voz default por ahora.")

    payload = {
        "input": {
            "prompt": texto,
            "voice": "lucy",  # voz preset (fallback)
            "format": "wav",
        }
    }
    if ref_url:
        payload["input"]["voice_url"] = ref_url

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    resp = requests.post(CHATTERBOX_API_URL, json=payload, headers=headers, timeout=300)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "COMPLETED":
        raise RuntimeError(f"Chatterbox API fallo: {data}")

    audio_url = data["output"]["audio_url"]
    urllib.request.urlretrieve(audio_url, ruta_mp3)
    print(f"  [chatterbox-api] cost: ${data['output'].get('cost', 0):.4f}")


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
    parser.add_argument("--motor", choices=["kokoro", "edge", "chatterbox", "chatterbox-api"], default="kokoro",
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

        elif args.motor == "chatterbox-api":
            if not HAY_REQUESTS:
                print("  requests no esta instalado. pip install requests")
                return
            ruta_ref = CARPETA_VOCES / VOZ_REFERENCIA_POR_IDIOMA.get(idioma_efectivo, "")
            if not ruta_ref.exists():
                ruta_ref = None
            print(f"  [IDIOMA: {idioma_efectivo}] (serverless RunPod)")
            _generar_chatterbox_api(texto, idioma_efectivo, ruta_mp3, ruta_ref)

        print(f"  Audio : {ruta_mp3} ({ruta_mp3.stat().st_size / 1024:.0f} KB)")

    print(f"\nListo. {len(guiones)} guiones procesados con {args.motor}.")


if __name__ == "__main__":
    main()
