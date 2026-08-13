"""
validar_guiones.py

Revisa todos los guiones en output/guiones_listos/ y reporta problemas
antes de locutar. Ademas de los checks basicos (gancho, separador,
longitud, encoding) valida la CALIDAD NARRATIVA que importa para TTS:

- Coherencia de genero del narrador: `[GENERO:]` debe coincidir con la voz
  que usa la historia (p.ej. "mi novio" => narradora mujer). El 13/08 se
  locuto un guion con [GENERO: hombre] narrado por una mujer (voz equivocada).
- Palabras consecutivas repetidas ("que que", "el el") -> el TTS las lee
  como sonidos extraños.
- N-gramas repetidos muchas veces (bucle/loop del modelo).
- Frases muy largas (dificiles de locutar con naturalidad).

Uso (desde la raiz del proyecto):
    python src/validar_guiones.py
    python src/validar_guiones.py --archivo mi_guion.txt
"""

import argparse
import re
from collections import Counter
from pathlib import Path

CARPETA_GUIONES = Path("output/guiones_listos")
PALABRAS_POR_MINUTO = 145
MIN_PALABRAS = 500     # menos de ~3.5 min es sospechoso
MAX_PALABRAS = 5000    # mas de ~34 min es sospechoso

# Senales de que el narrador es MUJER (habla de su pareja hombre)
SENALES_NARRADORA_MUJER = [
    "mi novio", "mi esposo", "mi marido", "mi prometido", "mi pareja me",
    "mi ex novio", "mi exnovio", "mi ex esposo", "mi novio me", "mi esposo me",
    "el chico que", "ese chico", "mi amigo del pecho",
]
# Senales de que el narrador es HOMBRE (habla de su pareja mujer)
SENALES_NARRADOR_HOMBRE = [
    "mi novia", "mi esposa", "mi mujer", "mi prometida", "mi ex novia",
    "mi exnovia", "mi ex esposa", "mi novia me", "mi esposa me", "esa chica",
]

MIN_APARICIONES_NGRAMA = 4  # un n-grama que aparece >= 4 veces = loop
LARGO_NGRAMA = 5
MAX_PALABRAS_FRASE = 45


def _palabras(texto: str) -> list[str]:
    return re.findall(r"[\wáéíóúüñÁÉÍÓÚÜÑ]+", texto.lower())


def _detectar_genero_narrador(texto: str) -> str | None:
    t = texto.lower()
    senales_mujer = sum(1 for s in SENALES_NARRADORA_MUJER if s in t)
    senales_hombre = sum(1 for s in SENALES_NARRADOR_HOMBRE if s in t)
    if senales_mujer > senales_hombre:
        return "mujer"
    if senales_hombre > senales_mujer:
        return "hombre"
    return None


def validar_guion(ruta: Path) -> list[str]:
    problemas = []

    if not ruta.exists():
        return [f"[NO EXISTE] {ruta}"]

    texto = ruta.read_text(encoding="utf-8-sig")
    lineas = texto.split("\n")
    palabras = len(texto.split())

    # --- metadatos ---
    genero_meta = None
    for l in lineas:
        m = re.match(r"\[GENERO:\s*(\w+)\]", l)
        if m:
            genero_meta = m.group(1).lower()

    if "---" not in texto:
        problemas.append("Falta el separador '---' entre gancho y cuerpo")

    if palabras < MIN_PALABRAS:
        problemas.append(f"Demasiado corto: {palabras} palabras (~{palabras / PALABRAS_POR_MINUTO:.1f} min). Minimo: {MIN_PALABRAS}")
    elif palabras > MAX_PALABRAS:
        problemas.append(f"Demasiado largo: {palabras} palabras (~{palabras / PALABRAS_POR_MINUTO:.1f} min). Maximo: {MAX_PALABRAS}")

    # --- coherencia de genero del narrador ---
    genero_narrado = _detectar_genero_narrador(texto)
    if genero_meta and genero_narrado and genero_meta != genero_narrado:
        problemas.append(
            f"[GENERO: {genero_meta}] pero la historia la narra {genero_narrado} "
            f"(voz equivocada en locucion). Corregir el genero."
        )

    # --- palabras consecutivas repetidas ("que que") ---
    toks = texto.split()
    for i in range(len(toks) - 1):
        if re.sub(r"[^\wáéíóúüñ]", "", toks[i].lower()) == re.sub(r"[^\wáéíóúüñ]", "", toks[i + 1].lower()):
            problemas.append(f"Palabra repetida consecutiva: \"{toks[i]} {toks[i + 1]}\"")
            break

    # --- n-gramas repetidos (loop del modelo) ---
    cuerpo = _palabras(texto)
    ngramas = Counter(tuple(cuerpo[i:i + LARGO_NGRAMA]) for i in range(len(cuerpo) - LARGO_NGRAMA + 1))
    top = ngramas.most_common(1)
    if top and top[0][1] >= MIN_APARICIONES_NGRAMA:
        ngrama, veces = top[0]
        problemas.append(f"Frase repetida {veces}x (posible loop): \"{' '.join(ngrama)}\"")

    # --- frases muy largas ---
    oraciones = [s.strip() for s in re.split(r"[.!?]", texto) if s.strip()]
    for s in oraciones[:10]:
        n = len(s.split())
        if n > MAX_PALABRAS_FRASE:
            problemas.append(f"Frase muy larga ({n} palabras, dificil de locutar): \"{s[:70]}...\"")
            break

    return problemas


def main():
    parser = argparse.ArgumentParser(description="Valida guiones generados antes de locutar (calidad narrativa + TTS).")
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
