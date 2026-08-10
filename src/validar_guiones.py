"""
validar_guiones.py

Revisa todos los guiones en output/guiones_listos/ y reporta problemas:
- Ganchos vacios o faltantes
- Separador --- ausente
- Guiones anomalamente cortos o largos
- Caracteres de encoding corruptos

Uso (desde la raiz del proyecto):
    python src/validar_guiones.py
    python src/validar_guiones.py --archivo mi_guion.txt
"""

import argparse
from pathlib import Path

CARPETA_GUIONES = Path("output/guiones_listos")
PALABRAS_POR_MINUTO = 145
MIN_PALABRAS = 500     # menos de ~3.5 min es sospechoso
MAX_PALABRAS = 5000    # mas de ~34 min es sospechoso


def validar_guion(ruta: Path) -> list[str]:
    problemas = []

    if not ruta.exists():
        return [f"[NO EXISTE] {ruta}"]

    texto = ruta.read_text(encoding="utf-8")
    lineas = texto.split("\n")
    palabras = len(texto.split())

    if "---" not in texto:
        problemas.append("Falta el separador '---' entre gancho y cuerpo")

    primera_linea = lineas[0].strip() if lineas else ""
    if not primera_linea and "---" in texto:
        idx = next(i for i, l in enumerate(lineas) if l.strip() == "---")
        if idx <= 2:
            problemas.append("Gancho vacio (primeras lineas en blanco antes del separador)")

    if palabras < MIN_PALABRAS:
        problemas.append(f"Demasiado corto: {palabras} palabras (~{palabras / PALABRAS_POR_MINUTO:.1f} min). Minimo esperado: {MIN_PALABRAS}")
    elif palabras > MAX_PALABRAS:
        problemas.append(f"Demasiado largo: {palabras} palabras (~{palabras / PALABRAS_POR_MINUTO:.1f} min). Maximo esperado: {MAX_PALABRAS}")

    caracteres_basura = sum(1 for c in ruta.name if ord(c) > 127 and c not in "áéíóúüñÁÉÍÓÚÜÑ")
    if caracteres_basura > 0:
        problemas.append(f"Encoding corrupto en nombre de archivo ({caracteres_basura} caracteres no validos)")

    textos_basura = sum(1 for c in texto[:500] if ord(c) == 0xFFFD)
    if textos_basura > 0:
        problemas.append(f"Caracteres de reemplazo (U+FFFD) en el contenido")

    return problemas


def main():
    parser = argparse.ArgumentParser(description="Valida guiones generados antes de locutar.")
    parser.add_argument("--archivo", type=str, default=None, help="Validar un solo guion especifico")
    args = parser.parse_args()

    if args.archivo:
        guiones = [CARPETA_GUIONES / args.archivo]
    else:
        guiones = sorted(CARPETA_GUIONES.glob("*.txt")) if CARPETA_GUIONES.exists() else []

    if not guiones:
        print("No se encontraron guiones para validar.")
        return

    total_problemas = 0
    limpios = 0

    for guion in guiones:
        problemas = validar_guion(guion)
        if problemas:
            total_problemas += len(problemas)
            print(f"[!] {guion.name}")
            for p in problemas:
                print(f"      {p}")
            print()
        else:
            limpios += 1

    print(f"Resultado: {limpios} guiones limpios, {total_problemas} problemas en {len(guiones) - limpios} archivos.")


if __name__ == "__main__":
    main()
