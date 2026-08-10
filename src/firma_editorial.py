"""
firma_editorial.py

Añade un sello de cierre reconocible del canal al final de cada guion,
DESPUES de generar la historia completa (no requiere llamada extra a la
API DeepSeek, es texto local -> costo cero).

Uso en generar_lote.py o generar_historia.py, justo antes de guardar el
archivo .txt final:

    from firma_editorial import agregar_firma

    guion_completo = f"{gancho}\n\n---\n\n{historia}"
    guion_completo = agregar_firma(guion_completo)
"""

import random

# --------------------------------------------------------------------------
# Elige UNA sola linea de estas para que sea el sello fijo del canal
# (recomendado: fija, no rotativa -- es lo que la hace reconocible).
# Deja las demas comentadas como opciones para probar tono.
# --------------------------------------------------------------------------

FIRMA_FIJA = (
    "\n\n—\n\nY así fue como aprendí que algunas heridas no se cierran, "
    "solo se aprende a cargar con ellas de otra forma."
)

# Alternativas de tono, por si quieres probar cual conecta mejor con tu
# audiencia antes de fijar una definitiva:
ALTERNATIVAS = [
    "\n\n—\n\nSi esta historia te recordó a algo tuyo, ya sabes cómo termina: "
    "no todos los finales necesitan cerrarse bien, solo necesitan cerrarse.",
    "\n\n—\n\nA veces la única justicia posible es contar la historia. "
    "Esta ya la conté yo. La tuya, ¿la has contado?",
    "\n\n—\n\nNo todo lo que se rompe se puede arreglar. Pero se puede "
    "aprender a vivir con la grieta.",
]


def agregar_firma(guion: str, usar_fija: bool = True) -> str:
    """
    Agrega el sello editorial al final del guion.

    usar_fija=True  -> siempre la misma linea (recomendado una vez que
                        elijas la que mejor conecta con tu audiencia).
    usar_fija=False -> rota entre ALTERNATIVAS mientras pruebas cual usar.
    """
    if usar_fija:
        return guion + FIRMA_FIJA
    return guion + random.choice(ALTERNATIVAS)


if __name__ == "__main__":
    ejemplo = "GANCHO DE PRUEBA\n\n---\n\nHISTORIA DE PRUEBA."
    print(agregar_firma(ejemplo, usar_fija=True))
