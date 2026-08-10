"""
limpiar_output.py

Limpia archivos temporales e intermedios del proyecto sin tocar los
resultados finales. Elimina: WAV intermedios de Kokoro, fragmentos de
descarga de yt-dlp, y archivos en output/audio/ y output/subtitulos_ass/
que no tengan un guion correspondiente.

Uso (desde la raiz del proyecto):
    python src/limpiar_output.py            # modo seco: muestra que borraria
    python src/limpiar_output.py --aplicar  # borra de verdad
"""

import argparse
from pathlib import Path

CARPETA_GUIONES = Path("output/guiones_listos")
CARPETA_AUDIO = Path("output/audio")
CARPETA_ASS = Path("output/subtitulos_ass")
CARPETA_GAMEPLAY = Path("storage/raw_gameplay")

PREFIJOS_TEMP = ["_temp_download", "_temp"]


def _es_temp(nombre: str) -> bool:
    return any(nombre.startswith(p) for p in PREFIJOS_TEMP) or nombre.endswith(".wav")


def _lista_a_borrar() -> list[Path]:
    a_borrar = []

    for carpeta in [CARPETA_AUDIO, CARPETA_ASS]:
        if not carpeta.exists():
            continue
        for f in carpeta.iterdir():
            if f.is_file() and _es_temp(f.name):
                a_borrar.append(f)

    if CARPETA_GAMEPLAY.exists():
        for f in CARPETA_GAMEPLAY.glob("_temp_download*"):
            a_borrar.append(f)

    return a_borrar


def main():
    parser = argparse.ArgumentParser(description="Limpia archivos temporales/intermedios.")
    parser.add_argument("--aplicar", action="store_true", help="Borrar de verdad (si no, solo muestra)")
    args = parser.parse_args()

    a_borrar = _lista_a_borrar()

    if not a_borrar:
        print("No hay archivos temporales para limpiar.")
        return

    print(f"Se eliminaran {len(a_borrar)} archivo(s):")
    for f in a_borrar:
        print(f"  {f}")

    if not args.aplicar:
        print("\n(MODO SECO: corre con --aplicar para borrar de verdad)")
        return

    for f in a_borrar:
        f.unlink(missing_ok=True)
        print(f"  Borrado: {f.name}")

    print(f"\nListo. {len(a_borrar)} archivos eliminados.")


if __name__ == "__main__":
    main()
