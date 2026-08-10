"""
verificar_entorno.py

Chequea que todo el entorno del proyecto este listo antes de ejecutar:
dependencias Python, ffmpeg, yt-dlp, modelos Kokoro, fuente Montserrat,
API keys y estructura de carpetas. Reporta que falta y que esta OK.

Uso (desde la raiz del proyecto):
    python src/verificar_entorno.py
"""

import os
import shutil
import sys
from pathlib import Path

FALLOS = 0


def _chequear(nombre: str, condicion: bool, detalle: str = "") -> None:
    global FALLOS
    estado = "OK" if condicion else "FALTA"
    if not condicion:
        FALLOS += 1
    print(f"  [{estado}] {nombre}" + (f"  ({detalle})" if detalle else ""))


def _modulos_python() -> list[str]:
    return ["openai", "sentence_transformers", "numpy", "edge_tts", "kokoro_onnx", "soundfile", "faster_whisper"]


def _ffmpeg_disponible() -> str | None:
    ruta = shutil.which("ffmpeg")
    if ruta:
        return ruta
    candidata = Path(os.environ.get("LOCALAPPDATA", "")) / "ffmpeg"
    if candidata.exists():
        for p in candidata.rglob("ffmpeg.exe"):
            return str(p)
    return None


def main():
    print("Verificando entorno del proyecto canal-historias...\n")

    print("1) Modulos Python")
    for mod in _modulos_python():
        try:
            __import__(mod)
            _chequear(mod, True)
        except ImportError:
            _chequear(mod, False, "pip install -r requirements.txt")

    print("\n2) Herramientas externas")
    ffmpeg = _ffmpeg_disponible()
    _chequear("ffmpeg", ffmpeg is not None, ffmpeg or "instalar o agregar al PATH")
    ytdlp = shutil.which("yt-dlp")
    _chequear("yt-dlp", ytdlp is not None, ytdlp or "pip install yt-dlp")

    print("\n3) Modelos y recursos")
    _chequear("Kokoro ONNX", Path("storage/kokoro-v1.0.onnx").exists(), "storage/kokoro-v1.0.onnx")
    _chequear("Voces Kokoro", Path("storage/voices-v1.0.bin").exists(), "storage/voices-v1.0.bin")
    _chequear("Fuente Montserrat", Path("storage/Montserrat-Bold.ttf").exists(), "storage/Montserrat-Bold.ttf")

    print("\n4) API keys")
    _chequear("DEEPSEEK_API_KEY", bool(os.environ.get("DEEPSEEK_API_KEY")))
    _chequear("ELEVENLABS_API_KEY", bool(os.environ.get("ELEVENLABS_API_KEY")), "opcional")
    _chequear("FISH_AUDIO_API_KEY", bool(os.environ.get("FISH_AUDIO_API_KEY")), "opcional")

    print("\n5) Carpetas")
    for carpeta in ["data", "output/guiones_listos", "output/audio", "output/subtitulos_ass",
                    "output/videos", "output/shorts", "storage/raw_gameplay"]:
        _chequear(carpeta + "/", Path(carpeta).exists())

    print()
    if FALLOS == 0:
        print("Todo OK. El entorno esta listo.")
        sys.exit(0)
    else:
        print(f"{FALLOS} problema(s) detectados. Revisar lo marcado como [FALTA].")
        sys.exit(1)


if __name__ == "__main__":
    main()
