"""
utilidades.py

Funciones compartidas del proyecto: normalizacion de nombres de archivo
para que las salidas no tengan tildes, enes ni caracteres que rompan la
compatibilidad en Windows.

Uso:
    from utilidades import normalizar_nombre

    nombre_limpio = normalizar_nombre("descubrí que mi compañero sabotea...")
    # -> "descubri_que_mi_companero_sabotea"
"""

import re
import unicodedata


def normalizar_nombre(texto: str, max_largo: int = 40) -> str:
    """Normaliza un texto para usarlo como nombre de archivo:
    quita tildes/enes, deja solo alfanumericos/espacios/guiones,
    convierte a minusculas y reemplaza espacios por guiones bajos."""
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^\w\s-]", "", texto).strip().lower()
    texto = re.sub(r"[\s]+", "_", texto)
    return texto[:max_largo]
