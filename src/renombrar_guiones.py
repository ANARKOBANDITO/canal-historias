"""
renombrar_guiones.py

Renombra los archivos de output/guiones_listos/ con un formato mas
limpio: numeracion secuencial + primeras 40 letras del tema, sin
caracteres extranos ni truncamientos bruscos.

Uso (desde la raiz del proyecto):
    python src/renombrar_guiones.py
    python src/renombrar_guiones.py --dry-run
"""

import argparse
from pathlib import Path

from utilidades import normalizar_nombre

CARPETA_GUIONES = Path("output/guiones_listos")


def main():
    parser = argparse.ArgumentParser(description="Renombra guiones con formato limpio y numerado.")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar cambios sin aplicarlos")
    args = parser.parse_args()

    if not CARPETA_GUIONES.exists():
        print(f"No existe {CARPETA_GUIONES}/")
        return

    archivos = sorted(CARPETA_GUIONES.glob("*.txt"))
    if not archivos:
        print("No hay guiones para renombrar.")
        return

    print(f"Guiones encontrados: {len(archivos)}")
    if args.dry_run:
        print("(MODO SIMULACION -- no se modifica nada)\n")

    for i, archivo in enumerate(archivos, 1):
        tema_aproximado = archivo.stem
        nombre_limpio = f"{i:03d}_{normalizar_nombre(tema_aproximado)}.txt"
        destino = CARPETA_GUIONES / nombre_limpio

        if archivo.name == nombre_limpio:
            continue

        if args.dry_run:
            print(f"  {archivo.name}")
            print(f"  -> {nombre_limpio}\n")
        else:
            archivo.rename(destino)
            print(f"  {archivo.name}  ->  {nombre_limpio}")

    if not args.dry_run:
        print(f"\nListo. {len(archivos)} archivos renombrados.")


if __name__ == "__main__":
    main()
