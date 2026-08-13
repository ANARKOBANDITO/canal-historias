"""
prompts/__init__.py

Carga los prompts y categorias nativos del idioma pedido. Cada idioma
tiene su propio modulo en src/prompts/<idioma>.py con textos redactados
de forma NATIVA (no traducidos literalmente), para que los guiones no
suenen a traduccion y no se detecten como duplicados entre canales.

Uso:
    from prompts import cargar_idioma
    p = cargar_idioma("en")   # -> modulo con CATEGORIAS y funciones de prompt
"""

import importlib

IDIOMAS_SOPORTADOS = ("es", "en", "pt")

# Mapeo genero -> como se escribe en cada idioma
GENERO_POR_IDIOMA = {
    "es": {"hombre": "hombre", "mujer": "mujer"},
    "en": {"hombre": "male", "mujer": "female"},
    "pt": {"hombre": "homem", "mujer": "mulher"},
}


def cargar_idioma(idioma: str):
    """Devuelve el modulo de prompts para el idioma (es|en|pt)."""
    if idioma not in IDIOMAS_SOPORTADOS:
        raise ValueError(f"Idioma no soportado: {idioma}. Usa {IDIOMAS_SOPORTADOS}")
    return importlib.import_module(f"prompts.{idioma}")


def genero_en_idioma(idioma: str, genero: str) -> str:
    """Traduce 'hombre'/'mujer' al termino que usa el prompt del idioma."""
    return GENERO_POR_IDIOMA.get(idioma, {}).get(genero, genero)
