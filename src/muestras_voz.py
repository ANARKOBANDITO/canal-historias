"""
muestras_voz.py

Genera muestras de voz en espanol con Chatterbox Multilingual en GPU
(Vast.ai) para elegir el narrador del canal (Fase 2.5). Para cada clip de
referencia candidato en storage/voces/candidatas/ clona la voz y sintetiza
la MISMA frase de prueba (el gancho del guion del piloto). Ademas genera:

  - es_default: baseline sin clonar (voz default del modelo)
  - es_v3_*:    experimento con el finetune LatAm Spanish V3 (si carga)
  - es_largo:   prueba LARGA (primeros capitulos del guion) para detectar
                cortes/glitches en generacion larga

Salida: output/muestras_voz/*.wav (+ .mp3 si hay ffmpeg) y RESUMEN.txt

Uso (en el pod, desde la raiz del proyecto):
    python src/muestras_voz.py --guion output/guiones_listos/mi_guion.txt --idioma es --largo
    python src/muestras_voz.py --frase "Frase de prueba" --idioma es
    python src/muestras_voz.py --guion ... --solo jorge --exaggeration 0.3   # re-iterar 1 voz
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

CARPETA_CANDIDATAS = Path("storage/voces/candidatas")
CARPETA_SALIDA = Path("output/muestras_voz")
REF_DEFAULT = Path("storage/voces/referencia_hombre.wav")

MODELO_V3 = "ResembleAI/Chatterbox-Multilingual-es-mx-latam"


def _reconfig() -> None:
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _leer_guion(ruta: Path) -> tuple[str, str]:
    """Devuelve (gancho, cuerpo). Gancho = primer parrafo; cuerpo = resto."""
    parrafos: list[str] = []
    actual: list[str] = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if linea.startswith("[GENERO:") or linea.startswith("[IDIOMA:"):
            continue
        if linea.strip() == "":
            if actual:
                parrafos.append(" ".join(actual).strip())
                actual = []
            continue
        actual.append(linea.strip())
    if actual:
        parrafos.append(" ".join(actual).strip())

    parrafos = [p for p in parrafos if p and p.strip("-–—") != ""]
    gancho = parrafos[0] if parrafos else ""
    cuerpo = " ".join(parrafos[1:])
    return gancho, cuerpo


def _gancho_corto(gancho: str, max_palabras: int = 45) -> str:
    palabras = gancho.split()
    return " ".join(palabras[:max_palabras])


def _cuerpo_largo(cuerpo: str, max_palabras: int = 320) -> str:
    palabras = cuerpo.split()
    return " ".join(palabras[:max_palabras])


def _guardar_audio(tensor, sample_rate: int, ruta_wav: Path) -> None:
    import torchaudio as ta

    if tensor.dim() == 1:
        tensor = tensor.unsqueeze(0)
    ruta_wav.parent.mkdir(exist_ok=True, parents=True)
    ta.save(str(ruta_wav), tensor, sample_rate)
    print(f"    -> {ruta_wav.name} ({ruta_wav.stat().st_size / 1024:.0f} KB)")


def _mp3_si_posible(ruta_wav: Path) -> Path | None:
    """Convierte WAV a MP3 si hay ffmpeg. Devuelve la ruta MP3 o None."""
    ruta_mp3 = ruta_wav.with_suffix(".mp3")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(ruta_wav),
             "-codec:a", "libmp3lame", "-ar", "44100", "-qscale:a", "2",
             str(ruta_mp3)],
            check=True, capture_output=True,
        )
        ruta_wav.unlink(missing_ok=True)
        return ruta_mp3
    except Exception:
        return None


def _cargar_modelo(device: str, kwargs: dict | None = None):
    import torch
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    opciones = [kwargs or {}]
    opciones.append({"model_name": MODELO_V3})
    opciones.append({"t3_model": MODELO_V3})

    ultimo_error = None
    for kw in opciones:
        try:
            print(f"  cargando ChatterboxMultilingual {kw if kw else '(default)'} ...")
            return ChatterboxMultilingualTTS.from_pretrained(device=torch.device(device), **kw)
        except Exception as e:
            ultimo_error = e
            print(f"  [fallo] {type(e).__name__}: {str(e)[:120]}")
    raise RuntimeError(f"No se pudo cargar ChatterboxMultilingual: {ultimo_error}")


def main():
    _reconfig()
    parser = argparse.ArgumentParser(
        description="Genera muestras de voz en espanol con Chatterbox Multilingual (pod).")
    parser.add_argument("--guion", default=None, help="Guion del piloto (para extraer el gancho)")
    parser.add_argument("--frase", default=None, help="Frase de prueba directa")
    parser.add_argument("--idioma", default="es", help="Idioma (default: es)")
    parser.add_argument("--largo", action="store_true", help="Incluir prueba LARGA (detectar glitches)")
    parser.add_argument("--solo", default=None, help="Solo una candidata por label (ej: jorge)")
    parser.add_argument("--exaggeration", type=float, default=0.5, help="Exaggeration para clonar")
    parser.add_argument("--carpeta", default=str(CARPETA_CANDIDATAS), help="Carpeta de candidatas")
    args = parser.parse_args()

    if not args.frase and not args.guion:
        raise SystemExit("Pasa --frase o --guion.")

    if args.guion:
        gancho, cuerpo = _leer_guion(Path(args.guion))
        frase = _gancho_corto(gancho) if gancho else args.frase or ""
        if not frase:
            raise SystemExit("El guion no tiene gancho.")
    else:
        frase = args.frase
        cuerpo = ""

    print(f"Frase de prueba ({len(frase.split())} palabras):\n  {frase[:120]}...\n")

    import torch
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"CUDA: {torch.cuda.is_available()}  GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu'}")

    CARPETA_SALIDA.mkdir(exist_ok=True, parents=True)
    model = _cargar_modelo(device)
    print("Modelo cargado.\n")

    resumen: list[str] = [f"Muestras de voz - idioma {args.idioma}", ""]
    resumen.append(f"Frase: {frase}")
    resumen.append("")

    # 1) baseline sin clonar
    print("Baseline (sin clonar):")
    try:
        wav = model.generate(frase, language_id=args.idioma)
        ruta = CARPETA_SALIDA / "es_default.wav"
        _guardar_audio(wav, model.sr, ruta)
        resumen.append(f"es_default.wav  (baseline, sin clonar)")
    except Exception as e:
        print(f"  [fallo] {e}")
        resumen.append("es_default.wav  FALLO")

    # 2) candidatas clonadas
    carpeta = Path(args.carpeta)
    candidatas = sorted(carpeta.glob("es_*_*.wav")) if carpeta.exists() else []
    if not candidatas:
        candidatas = sorted(carpeta.glob("*.wav"))
    print(f"\nCandidatas encontradas: {len(candidatas)}")
    for clip in candidatas:
        label = clip.stem
        if args.solo and args.solo not in label:
            continue
        print(f"\nClonando {label} ...")
        try:
            model.prepare_conditionals(str(clip), exaggeration=args.exaggeration)
            wav = model.generate(frase, language_id=args.idioma)
            ruta = CARPETA_SALIDA / f"{label}.wav"
            _guardar_audio(wav, model.sr, ruta)
            resumen.append(f"{label}.wav  (clon de {clip.name})")
        except Exception as e:
            print(f"  [fallo] {type(e).__name__}: {str(e)[:200]}")
            resumen.append(f"{label}.wav  FALLO: {str(e)[:80]}")

    # 3) experimento es-mx-latam (V3)
    print("\nExperimento es-mx-latam (V3):")
    try:
        model_v3 = _cargar_modelo(device, kwargs={"model_name": MODELO_V3})
        wav = model_v3.generate(frase, language_id=args.idioma)
        ruta = CARPETA_SALIDA / "es_v3_default.wav"
        _guardar_audio(wav, model_v3.sr, ruta)
        resumen.append("es_v3_default.wav  (finetune es-mx-latam, sin clonar)")
        ref = REF_DEFAULT if REF_DEFAULT.exists() else (candidatas[0] if candidatas else None)
        if ref:
            model_v3.prepare_conditionals(str(ref), exaggeration=args.exaggeration)
            wav = model_v3.generate(frase, language_id=args.idioma)
            ruta = CARPETA_SALIDA / "es_v3_clonado.wav"
            _guardar_audio(wav, model_v3.sr, ruta)
            resumen.append("es_v3_clonado.wav  (finetune es-mx-latam, clon)")
    except Exception as e:
        print(f"  [descarte] el finetune V3 no carga con este paquete: {type(e).__name__}: {str(e)[:120]}")
        resumen.append("es_v3_*  NO DISPONIBLE (el paquete 0.1.7 no carga el finetune)")

    # 4) prueba larga (si --largo)
    if args.largo and cuerpo:
        print("\nPrueba larga (detectar glitches):")
        texto_largo = _cuerpo_largo(cuerpo)
        ref = REF_DEFAULT if REF_DEFAULT.exists() else (candidatas[0] if candidatas else None)
        if ref:
            print(f"  {len(texto_largo.split())} palabras, referencia {ref.name}")
            try:
                model.prepare_conditionals(str(ref), exaggeration=args.exaggeration)
                wav = model.generate(texto_largo, language_id=args.idioma)
                ruta = CARPETA_SALIDA / "es_largo.wav"
                _guardar_audio(wav, model.sr, ruta)
                resumen.append("es_largo.wav  (prueba larga ~2 min, chequear cortes)")
            except Exception as e:
                print(f"  [fallo] {type(e).__name__}: {str(e)[:200]}")
                resumen.append("es_largo.wav  FALLO (indica limite de longitud)")
        else:
            print("  [aviso] sin referencia, se omite la prueba larga")

    # convertir WAV -> MP3 si hay ffmpeg
    for wav in sorted(CARPETA_SALIDA.glob("*.wav")):
        _mp3_si_posible(wav)

    (CARPETA_SALIDA / "RESUMEN.txt").write_text("\n".join(resumen) + "\n", encoding="utf-8")
    print("\n" + "=" * 50)
    print("\n".join(resumen))
    print("=" * 50)
    print(f"\nListo. Muestras en {CARPETA_SALIDA}/")


if __name__ == "__main__":
    main()
