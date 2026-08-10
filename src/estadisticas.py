"""
estadisticas.py

Dashboard del proyecto: guiones generados, palabras, minutos narrados,
y consumo estimado de la API de DeepSeek.

Uso (desde la raiz del proyecto):
    python src/estadisticas.py
"""

from pathlib import Path

CARPETA_GUIONES = Path("output/guiones_listos")
PALABRAS_POR_MINUTO = 145

TARIFA_INPUT = 0.27   # USD por millon de tokens de entrada (deepseek-v4-flash)
TARIFA_OUTPUT = 1.10  # USD por millon de tokens de salida
# Nota: verificar estas tarifas en la pagina de precios de DeepSeek.
# Se pueden sobrescribir con las variables de entorno:
#   ESTADISTICAS_TARIFA_INPUT / ESTADISTICAS_TARIFA_OUTPUT
import os
TARIFA_INPUT = float(os.environ.get("ESTADISTICAS_TARIFA_INPUT", TARIFA_INPUT))
TARIFA_OUTPUT = float(os.environ.get("ESTADISTICAS_TARIFA_OUTPUT", TARIFA_OUTPUT))
TOKENS_POR_PALABRA_ES = 1.6  # aprox: una palabra en espanol ~1.6 tokens


def _contar_guiones() -> list[Path]:
    if not CARPETA_GUIONES.exists():
        return []
    return sorted(CARPETA_GUIONES.glob("*.txt"))


def main():
    guiones = _contar_guiones()
    if not guiones:
        print("No hay guiones generados en output/guiones_listos/")
        return

    total_palabras = 0
    tamanos = {}

    for guion in guiones:
        texto = guion.read_text(encoding="utf-8")
        palabras = len(texto.split())
        total_palabras += palabras
        tamanos[guion.name] = palabras

    mas_largo = max(tamanos, key=tamanos.get)
    mas_corto = min(tamanos, key=tamanos.get)
    promedio = total_palabras // len(guiones) if guiones else 0
    minutos = total_palabras / PALABRAS_POR_MINUTO

    tokens_input = total_palabras * TOKENS_POR_PALABRA_ES * 0.6  # ~60% del gasto es input (system prompts + contexto)
    tokens_output = total_palabras * TOKENS_POR_PALABRA_ES * 0.4
    costo_input = (tokens_input / 1_000_000) * TARIFA_INPUT
    costo_output = (tokens_output / 1_000_000) * TARIFA_OUTPUT
    costo_total = costo_input + costo_output

    print("=" * 55)
    print("  ESTADISTICAS DEL PROYECTO")
    print("=" * 55)
    print(f"  Guiones generados:        {len(guiones)}")
    print(f"  Palabras totales:         {total_palabras:,}")
    print(f"  Minutos narrados (est.):  {minutos:.1f} min")
    print(f"  Promedio por guion:       {promedio:,} palabras ({promedio / PALABRAS_POR_MINUTO:.1f} min)")
    print(f"  Mas largo:                {tamanos[mas_largo]:,} palabras  ({mas_largo[:50]})")
    print(f"  Mas corto:                {tamanos[mas_corto]:,} palabras  ({mas_corto[:50]})")
    print("-" * 55)
    print(f"  Costo API estimado:")
    print(f"    Input:   ${costo_input:.4f} USD")
    print(f"    Output:  ${costo_output:.4f} USD")
    print(f"    Total:   ${costo_total:.4f} USD")
    print("=" * 55)
    print()
    print("Nota: el costo es una estimacion. El gasto real depende de tokens")
    print("de system prompt, referencias, y modo thinking si esta activado.")


if __name__ == "__main__":
    main()
