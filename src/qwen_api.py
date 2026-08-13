"""
qwen_api.py

Helpers para generar imagenes con Qwen-Image-Edit-2511 (Apache 2.0, uso
comercial) a traves de la API de Replicate. Compartido por
generar_avatar.py y generar_miniaturas.py (--backend api).

Los archivos de entrada se pasan como data URLs cuando pesan <= 256 KB
(regla de Replicate). Para archivos mayores habria que hostearlos con un
URL publico.

Uso:
    from qwen_api import ejecutar_prediccion, descargar, data_url
"""

import base64
import mimetypes
import os
import time
from pathlib import Path

import requests

API = "https://api.replicate.com/v1"
VERSION = "a0670a7f47d5975347c105b6ce71456c4377d511993975988127dee03ca6c729"


def _token() -> str:
    key = os.environ.get("REPLICATE_API_TOKEN")
    if not key:
        raise SystemExit(
            "REPLICATE_API_TOKEN no configurada. Crealo en replicate.com/account/api-tokens."
        )
    return key


def data_url(ruta: str | Path) -> str:
    """Convierte un archivo local en data URL (solo para <= 256 KB)."""
    ruta = Path(ruta)
    mime = mimetypes.guess_type(str(ruta))[0] or "image/png"
    b64 = base64.b64encode(ruta.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _salida_url(salida) -> str | None:
    if isinstance(salida, list) and salida:
        return salida[0]
    if isinstance(salida, str):
        return salida
    return None


def ejecutar_prediccion(prompt: str, imagenes: list[str], aspect: str = "match_input_image",
                        formato: str = "png", **extra) -> str:
    """Ejecuta Qwen-Image-Edit-2511 y devuelve la URL del resultado."""
    input_data = {
        "prompt": prompt,
        "image": imagenes,
        "aspect_ratio": aspect,
        "output_format": formato,
    }
    input_data.update(extra)

    headers = {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": "application/json",
        "Prefer": "wait=60",
    }
    resp = requests.post(f"{API}/predictions",
                         json={"version": VERSION, "input": input_data},
                         headers=headers, timeout=120)
    resp.raise_for_status()
    pred = resp.json()

    while pred.get("status") in ("starting", "processing"):
        time.sleep(4)
        r = requests.get(pred["urls"]["get"], headers={"Authorization": f"Bearer {_token()}"}, timeout=60)
        r.raise_for_status()
        pred = r.json()

    if pred.get("status") != "succeeded":
        raise RuntimeError(f"Prediccion {pred.get('status')}: {pred.get('error')}")

    url = _salida_url(pred.get("output"))
    if not url:
        raise RuntimeError(f"Sin salida util: {pred.get('output')}")
    return url


def descargar(url: str, ruta: str | Path) -> Path:
    """Descarga la imagen de salida a un archivo local."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, timeout=90)
    resp.raise_for_status()
    ruta.write_bytes(resp.content)
    return ruta
