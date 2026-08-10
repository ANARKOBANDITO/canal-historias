"""
variacion_narrativa.py

Modulo para romper la sensacion de "plantilla" en los guiones generados,
sin cambiar el nicho ni el flujo del pipeline.

Rota el TIPO de gancho y el TIPO de desenlace usado en cada historia,
evitando repetir el mismo tipo mas de N veces seguidas.

Uso:
    from variacion_narrativa import elegir_gancho, elegir_desenlace

    gancho = elegir_gancho()
    # gancho["nombre"]       -> "pregunta_retorica"
    # gancho["instruccion"]  -> texto para inyectar en el prompt de generar_gancho()

    desenlace = elegir_desenlace()
    # desenlace["nombre"]       -> "final_agridulce"
    # desenlace["instruccion"]  -> texto para inyectar en el prompt de generar_esquema()

Guarda el historial en data/historial_variacion.json (mismo patron que
data/banco_temas.pkl), asi que no rompe nada de lo que ya tienes.
"""

import json
import random
from pathlib import Path

DATA_DIR = Path("data")
HISTORIAL_PATH = DATA_DIR / "historial_variacion.json"

# Cuantos guiones recientes se consideran para evitar repetir un mismo tipo
VENTANA_ANTI_REPETICION = 3

# --------------------------------------------------------------------------
# CATALOGO DE TIPOS DE GANCHO
# --------------------------------------------------------------------------
# "instruccion" es lo que se inyecta en el prompt que le mandas a DeepSeek
# para generar_gancho(). Ajusta el texto a como escribes tus prompts.

GANCHOS = [
    {
        "nombre": "pregunta_retorica",
        "instruccion": (
            "Abre el gancho con una pregunta retorica dirigida al oyente, "
            "que lo haga cuestionarse que haria el en esa situacion. "
            "No reveles el desenlace."
        ),
    },
    {
        "nombre": "confesion_directa",
        "instruccion": (
            "Abre el gancho como una confesion cruda y directa en primera "
            "persona, como si el narrador llevara tiempo queriendo contar esto. "
            "Tono intimo, sin rodeos."
        ),
    },
    {
        "nombre": "dato_shockeante",
        "instruccion": (
            "Abre el gancho con una afirmacion o dato que suene "
            "impactante o contraintuitivo, dejando claro que hay una "
            "historia detras sin explicarla todavia."
        ),
    },
    {
        "nombre": "in_medias_res",
        "instruccion": (
            "Abre el gancho a mitad de la escena mas tensa de la historia "
            "(sin dar contexto todavia), y corta justo antes de revelar "
            "que esta pasando."
        ),
    },
    {
        "nombre": "advertencia_al_oyente",
        "instruccion": (
            "Abre el gancho como una advertencia o consejo directo al "
            "oyente basado en lo que el narrador aprendio, sin explicar "
            "todavia por que llego a esa conclusion."
        ),
    },
]

# --------------------------------------------------------------------------
# CATALOGO DE TIPOS DE DESENLACE
# --------------------------------------------------------------------------
# "instruccion" es lo que se inyecta en el prompt de generar_esquema(),
# en la parte donde defines el ultimo beat (resolucion/climax final).

DESENLACES = [
    {
        "nombre": "justicia_poetica",
        "instruccion": (
            "El desenlace debe ser de justicia poetica: quien actuo mal "
            "recibe una consecuencia clara y satisfactoria para el oyente."
        ),
    },
    {
        "nombre": "final_agridulce",
        "instruccion": (
            "El desenlace debe ser agridulce: el conflicto se resuelve, "
            "pero el narrador pierde algo importante en el proceso. "
            "No es un final completamente feliz ni completamente triste."
        ),
    },
    {
        "nombre": "final_abierto",
        "instruccion": (
            "El desenlace debe dejar una pregunta o tension sin resolver "
            "del todo, de forma deliberada, invitando al oyente a "
            "sacar sus propias conclusiones. Evita un cierre demasiado limpio."
        ),
    },
    {
        "nombre": "giro_ironico",
        "instruccion": (
            "El desenlace debe incluir un giro ironico: el resultado final "
            "contradice lo que el narrador (o el oyente) esperaba durante "
            "la mayor parte de la historia."
        ),
    },
    {
        "nombre": "resolucion_calmada",
        "instruccion": (
            "El desenlace debe ser una resolucion calmada y reflexiva, "
            "sin un giro dramatico final, enfocada en como el narrador "
            "cambio de perspectiva. Evita golpes de efecto."
        ),
    },
]


def _cargar_historial() -> dict:
    if not HISTORIAL_PATH.exists():
        return {"ganchos": [], "desenlaces": []}
    try:
        return json.loads(HISTORIAL_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"ganchos": [], "desenlaces": []}


def _guardar_historial(historial: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    HISTORIAL_PATH.write_text(
        json.dumps(historial, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _elegir(catalogo: list, historial_key: str) -> dict:
    historial = _cargar_historial()
    recientes = set(historial[historial_key][-VENTANA_ANTI_REPETICION:])

    candidatos = [item for item in catalogo if item["nombre"] not in recientes]
    if not candidatos:
        # Si ya se usaron todos los tipos en la ventana, se libera la restriccion
        candidatos = catalogo

    elegido = random.choice(candidatos)

    historial[historial_key].append(elegido["nombre"])
    historial[historial_key] = historial[historial_key][-50:]  # no crece infinito
    _guardar_historial(historial)

    return elegido


def elegir_gancho() -> dict:
    """Devuelve un tipo de gancho no usado en los ultimos N guiones."""
    return _elegir(GANCHOS, "ganchos")


def elegir_desenlace() -> dict:
    """Devuelve un tipo de desenlace no usado en los ultimos N guiones."""
    return _elegir(DESENLACES, "desenlaces")


if __name__ == "__main__":
    # Prueba rapida: simula 8 elecciones seguidas para ver la rotacion
    for i in range(8):
        g = elegir_gancho()
        d = elegir_desenlace()
        print(f"{i+1}. gancho={g['nombre']:20s} desenlace={d['nombre']}")
