"""
qa_audio.py

QA de locucion: transcribe el audio con faster-whisper y lo compara contra
el guion para detectar omisiones, cortes o truncamientos. Reporta:

  - duracion del audio
  - palabras transcritas vs palabras del guion
  - cobertura (%) = % de palabras del guion presentes en la transcripcion
  - si el final del guion aparece en el audio (detecta truncamiento)
  - primera y ultima frase transcrita

Uso (desde la raiz):
    python src/qa_audio.py output/audio/mi_guion.mp3 output/guiones_listos/mi_guion.txt
    python src/qa_audio.py output/audio/x.mp3 output/guiones_listos/x.txt --idioma es
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from faster_whisper import WhisperModel


def _duracion(ruta: Path) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(ruta)],
        capture_output=True, text=True,
    )
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return 0.0


def _texto_guion(ruta: Path) -> str:
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    cuerpo = [l for l in lineas
              if not l.startswith("[GENERO:") and not l.startswith("[IDIOMA:")
              and not re.fullmatch(r"[\s\-–—*_]+", l.strip())]
    return "\n".join(cuerpo)


def _palabras(texto: str) -> list[str]:
    return re.findall(r"[\wáéíóúüñÁÉÍÓÚÜÑ]+", texto.lower())


def main():
    parser = argparse.ArgumentParser(description="QA de locucion: whisper vs guion.")
    parser.add_argument("audio", help="Ruta al audio (MP3/WAV)")
    parser.add_argument("guion", help="Ruta al guion .txt")
    parser.add_argument("--idioma", default=None, help="Idioma para whisper (default auto)")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    parser.add_argument("--modelo", default="base")
    args = parser.parse_args()

    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    dur = _duracion(Path(args.audio))
    print(f"Duracion audio: {dur/60:.1f} min ({dur:.0f}s)")

    compute = "int8" if args.device == "cpu" else "float16"
    model = WhisperModel(args.modelo, device=args.device, compute_type=compute)
    segmentos, info = model.transcribe(
        str(Path(args.audio)), word_timestamps=False,
        language=args.idioma or None)
    transcrito = " ".join(s.text for s in segmentos).strip()

    guion_txt = _texto_guion(Path(args.guion))
    pal_guion = _palabras(guion_txt)
    pal_audio = _palabras(transcrito)

    if not pal_guion:
        print("El guion no tiene palabras (revisar formato).")
        return

    set_audio = set(pal_audio)
    presentes = [p for p in pal_guion if p in set_audio]
    cobertura = len(presentes) / len(pal_guion) * 100

    fin_guion = " ".join(pal_guion[-15:])
    fin_en_audio = fin_guion in " ".join(pal_audio[-60:])

    print(f"Palabras guion: {len(pal_guion)} | transcritas: {len(pal_audio)}")
    print(f"Cobertura: {cobertura:.1f}%  ({len(presentes)}/{len(pal_guion)})")
    print(f"Final del guion presente en el audio: {'SI' if fin_en_audio else 'NO (posible truncamiento)'}")
    print(f"Idioma detectado: {info.language}")
    print(f"\nInicio:  {transcrito[:150]}...")
    print(f"Final:   ...{transcrito[-150:]}")

    if cobertura < 90:
        print("\n[ALERTA] Cobertura < 90%: revisar cortes/omisiones antes de producir.")
    elif not fin_en_audio:
        print("\n[AVISO] El audio podria estar truncado al final.")


if __name__ == "__main__":
    main()
