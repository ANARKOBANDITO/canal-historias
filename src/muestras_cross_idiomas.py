"""
muestras_cross_idiomas.py

Valida la voz del canal (narrador HOMBRE = alonso, MUJER = dalia) clonada
con Chatterbox Multilingual en TODOS los idiomas del canal (es/en/pt).
Genera 1 muestra por idioma por narrador con una frase de prueba traducida.

La referencia de voz es la MISMA para los 3 idiomas (voice cloning
cross-language). Si el acento del espanol se nota mucho en en/pt, habra
que ajustar cfg_weight; este script sirve para decidirlo con evidencia.

Salida: output/muestras_voz/<idioma>_<narrador>.wav (+ .mp3 si hay ffmpeg)

Uso (en el pod, desde la raiz):
    python src/muestras_cross_idiomas.py --guion output/guiones_listos/mi_guion.txt
    python src/muestras_cross_idiomas.py --idiomas en,pt --voces hombre,mujer
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

CARPETA_VOCES = Path("storage/voces")
CARPETA_SALIDA = Path("output/muestras_voz")

REFERENCIA_POR_GENERO = {
    "hombre": "referencia_hombre.wav",
    "mujer": "referencia_mujer.wav",
}

# Frases de prueba traducidas (misma historia del piloto, por idioma).
# La frase "es" se toma del gancho del guion cuando se pasa --guion.
TRADUCCIONES = {
    "en": (
        "Never accept someone just because of their story. I learned that the "
        "hard way, when I found out the guy who stole my heart was faking being "
        "an orphan to pay his gambling debts. Listen closely."
    ),
    "pt": (
        "Nunca aceite alguem so pela sua historia. Aprendi isso da pior maneira, "
        "quando descobri que o cara que roubou meu coracao fingia ser orfao para "
        "pagar suas dividas de jogo. Escutem com atencao."
    ),
}

FRASE_ES_DEFAULT = (
    "Nunca aceptes a alguien solo por su historia. Yo aprendi esto de la manera "
    "mas cruel, cuando descubri que el chico que me robo el corazon fingia ser "
    "huerfano para pagar sus apuestas. Escucha bien."
)


def _reconfig() -> None:
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _leer_gancho(ruta: Path) -> str:
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
    return parrafos[0] if parrafos else FRASE_ES_DEFAULT


def _guardar_audio(tensor, sample_rate: int, ruta_wav: Path) -> None:
    import torchaudio as ta

    if tensor.dim() == 1:
        tensor = tensor.unsqueeze(0)
    ruta_wav.parent.mkdir(exist_ok=True, parents=True)
    ta.save(str(ruta_wav), tensor, sample_rate)
    print(f"    -> {ruta_wav.name}")


def _mp3_si_posible(ruta_wav: Path) -> None:
    ruta_mp3 = ruta_wav.with_suffix(".mp3")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(ruta_wav),
             "-codec:a", "libmp3lame", "-ar", "44100", "-qscale:a", "2",
             str(ruta_mp3)],
            check=True, capture_output=True,
        )
        ruta_wav.unlink(missing_ok=True)
    except Exception:
        pass


def main():
    _reconfig()
    parser = argparse.ArgumentParser(
        description="Valida la voz del canal (alonso/dalia) clonada en es/en/pt.")
    parser.add_argument("--guion", default=None, help="Guion para tomar el gancho en espanol")
    parser.add_argument("--idiomas", default="es,en,pt", help="Idiomas (comma, default es,en,pt)")
    parser.add_argument("--voces", default="hombre,mujer", help="Narradores (comma, default hombre,mujer)")
    parser.add_argument("--exaggeration", type=float, default=0.5)
    args = parser.parse_args()

    idiomas = [i.strip() for i in args.idiomas.split(",") if i.strip()]
    voces = [v.strip() for v in args.voces.split(",") if v.strip()]

    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    import torch
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"CUDA: {torch.cuda.is_available()}")
    model = ChatterboxMultilingualTTS.from_pretrained(device=torch.device(device))
    print("Modelo cargado.\n")

    frase_es = _leer_gancho(Path(args.guion)) if args.guion else FRASE_ES_DEFAULT
    frases = {"es": frase_es}
    frases.update(TRADUCCIONES)

    resumen: list[str] = ["Muestras cross-language (alonso/dalia) - voz del canal", ""]
    for genero in voces:
        ref = CARPETA_VOCES / REFERENCIA_POR_GENERO[genero]
        if not ref.exists():
            print(f"[X] falta referencia {ref}")
            continue
        print(f"=== Narrador {genero} (ref: {ref.name}) ===")
        for idioma in idiomas:
            texto = frases.get(idioma)
            if not texto:
                print(f"  [skip] sin frase para {idioma}")
                continue
            print(f"  [{idioma}] {len(texto.split())} palabras ...")
            try:
                model.prepare_conditionals(str(ref), exaggeration=args.exaggeration)
                wav = model.generate(texto, language_id=idioma)
                ruta = CARPETA_SALIDA / f"{idioma}_{genero}.wav"
                _guardar_audio(wav, model.sr, ruta)
                resumen.append(f"{idioma}_{genero}.wav  (clon de {ref.name})")
            except Exception as e:
                print(f"    [fallo] {type(e).__name__}: {str(e)[:150]}")
                resumen.append(f"{idioma}_{genero}.wav  FALLO: {str(e)[:80]}")

    for wav in sorted(CARPETA_SALIDA.glob("es_*.wav")) + sorted(CARPETA_SALIDA.glob("en_*.wav")) + sorted(CARPETA_SALIDA.glob("pt_*.wav")):
        _mp3_si_posible(wav)

    (CARPETA_SALIDA / "RESUMEN_CROSS.txt").write_text("\n".join(resumen) + "\n", encoding="utf-8")
    print("\n" + "=" * 50)
    print("\n".join(resumen))
    print("=" * 50)


if __name__ == "__main__":
    main()
