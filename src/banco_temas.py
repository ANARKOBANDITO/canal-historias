"""
banco_temas.py

Lleva un registro local (vectores, gratis, sin API) de los temas de
historias que ya se generaron, para que generar_temas.py pueda evitar
proponer temas repetidos o demasiado parecidos a uno anterior.
"""

import pickle
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ARCHIVO_BANCO = Path("data/banco_temas.pkl")
NOMBRE_MODELO = "paraphrase-multilingual-MiniLM-L12-v2"
UMBRAL_SIMILITUD = 0.75  # arriba de esto se considera "muy parecido"

_modelo = None


def _obtener_modelo():
    global _modelo
    if _modelo is None:
        _modelo = SentenceTransformer(NOMBRE_MODELO)
    return _modelo


def cargar_banco() -> dict:
    if ARCHIVO_BANCO.exists():
        with open(ARCHIVO_BANCO, "rb") as f:
            return pickle.load(f)
    return {"temas": [], "vectores": None}


def guardar_banco(banco: dict):
    with open(ARCHIVO_BANCO, "wb") as f:
        pickle.dump(banco, f)


def es_tema_repetido(tema: str, banco: dict) -> bool:
    if not banco["temas"]:
        return False

    modelo = _obtener_modelo()
    vector = modelo.encode(tema)
    similitudes = banco["vectores"] @ vector / (
        np.linalg.norm(banco["vectores"], axis=1) * np.linalg.norm(vector)
    )
    return float(np.max(similitudes)) >= UMBRAL_SIMILITUD


def agregar_tema(tema: str, banco: dict) -> dict:
    modelo = _obtener_modelo()
    vector = modelo.encode(tema)

    banco["temas"].append(tema)
    if banco["vectores"] is None:
        banco["vectores"] = np.array([vector])
    else:
        banco["vectores"] = np.vstack([banco["vectores"], vector])

    guardar_banco(banco)
    return banco
