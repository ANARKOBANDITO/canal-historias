"""
generar_lote.py

Toma todos los temas de temas_pendientes.txt (generados por
generar_temas.py) y genera un guion completo (gancho + historia) por
cada uno, de forma totalmente automatica. Los temas ya procesados se
mueven a temas_usados.txt para no repetirlos.

Uso (desde la raiz del proyecto):
    python src/generar_lote.py --genero mujer --minutos 30

Requisitos:
    pip install openai sentence-transformers numpy
"""

import argparse
from pathlib import Path

from generar_historia import generar_historia_completa, CARPETA_SALIDA, PALABRAS_POR_MINUTO
from firma_editorial import agregar_firma

ARCHIVO_PENDIENTES = Path("data/temas_pendientes.txt")
ARCHIVO_USADOS = Path("data/temas_usados.txt")


def _nombre_archivo_valido(texto: str) -> str:
    import re
    texto = re.sub(r"[^\w\s-]", "", texto).strip().lower()
    texto = re.sub(r"[\s]+", "_", texto)
    return texto[:50]


def main():
    parser = argparse.ArgumentParser(description="Genera un guion por cada tema pendiente, en lote.")
    parser.add_argument("--genero", choices=["hombre", "mujer"], default="mujer")
    parser.add_argument("--minutos", type=int, default=30)
    args = parser.parse_args()

    if not ARCHIVO_PENDIENTES.exists():
        print(f"No existe {ARCHIVO_PENDIENTES}. Corre primero: python generar_temas.py --cantidad 10")
        return

    temas = [l.strip() for l in ARCHIVO_PENDIENTES.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not temas:
        print("No hay temas pendientes.")
        return

    CARPETA_SALIDA.mkdir(exist_ok=True)

    for i, tema in enumerate(temas, 1):
        print(f"\n=== Historia {i}/{len(temas)}: {tema[:70]} ===")
        gancho, historia = generar_historia_completa(tema, args.genero, args.minutos, referencia_manual=None)

        guion_final = f"{gancho}\n\n---\n\n{historia}"
        guion_final = agregar_firma(guion_final)
        guion_final = f"[GENERO: {args.genero}]\n\n{guion_final}"
        nombre_archivo = _nombre_archivo_valido(tema) + ".txt"
        (CARPETA_SALIDA / nombre_archivo).write_text(guion_final, encoding="utf-8")

        with open(ARCHIVO_USADOS, "a", encoding="utf-8") as f:
            f.write(tema + "\n")

        print(f"  Guardado en: {CARPETA_SALIDA / nombre_archivo}")

    # vaciamos la lista de pendientes, ya se proceso todo
    ARCHIVO_PENDIENTES.write_text("", encoding="utf-8")
    print(f"\nListo. {len(temas)} guiones generados en '{CARPETA_SALIDA}/'.")


if __name__ == "__main__":
    main()
