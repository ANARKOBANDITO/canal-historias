"""
revisar_miniaturas.py

Revisa las miniaturas generadas (y opcionalmente la tarjeta Reddit y
frames de video) usando un modelo multimodal local (Qwen2.5-VL-7B) en GPU
para evaluar calidad, resolucion y "clickability". Devuelve un veredicto
por elemento y sugiere regenerar si algo falla.

Backends soportados:
    "local" -> Qwen2.5-VL-7B-Instruct en GPU local (Vast.ai, publico, sin token)
    "api"   -> API de MiniMax M3 (se configura con la API key del usuario)

Uso (desde la raiz del proyecto):
    python src/revisar_miniaturas.py --procesar --backend local
    python src/revisar_miniaturas.py "output/miniaturas/x_miniatura.png"
    python src/revisar_miniaturas.py --frames --backend local   # frames de video
"""

import argparse
import json
import re
from pathlib import Path

CARPETA_MINIATURAS = Path("output/miniaturas")
CARPETA_TARJETAS = Path("output/tarjetas")
CARPETA_FRAMES = Path("output/videos/_frames")

BACKEND = "local"  # Qwen2.5-VL-7B en el pod (validado 11/08)

# Resolucion esperada por tipo de archivo (16:9 vs 9:16)
RESOLUCION_ESPERADA = {
    "_16x9": (1920, 1080),
    "_9x16": (1080, 1920),
}

PROMPT_REVISION = (
    "Eres un experto en thumbnails de YouTube. Evalua esta imagen "
    "(y el contexto del titulo si se da). Responde SOLO con JSON: "
    '{"puntaje": 0-10, "clickability": "alta|media|baja", '
    '"resolucion_ok": true|false, "problemas": [...], "sugerencia": "..."}'
)

_modelo_vl = None


def _obtener_modelo_vl():
    """Carga Qwen2.5-VL-7B una sola vez (singleton)."""
    global _modelo_vl
    if _modelo_vl is None:
        import os
        os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
        import torch
        from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

        print("  Cargando Qwen2.5-VL-7B-Instruct...")
        cargas = {"torch_dtype": torch.bfloat16}
        try:
            _modelo_vl = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                "Qwen/Qwen2.5-VL-7B-Instruct", **cargas
            )
        except TypeError:
            # transformers 5.2.0 (chatterbox) no acepta load_in_4bit en este modelo
            cargas.pop("load_in_4bit", None)
            _modelo_vl = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                "Qwen/Qwen2.5-VL-7B-Instruct", **cargas
            )
        _modelo_vl.to("cuda" if torch.cuda.is_available() else "cpu")
        _modelo_vl.eval()
        _modelo_vl.procesador = AutoProcessor.from_pretrained("Qwen/Qwen2.5-VL-7B-Instruct")
    return _modelo_vl


def _revisar_con_vl(ruta_imagen: Path, contexto: str) -> dict:
    """Revisa una imagen con Qwen2.5-VL local y devuelve el veredicto JSON."""
    import torch

    model = _obtener_modelo_vl()
    from PIL import Image

    img = Image.open(ruta_imagen).convert("RGB")

    # Deteccion de resolucion esperada por el nombre del archivo
    resolucion_ok = None
    for marca, (w, h) in RESOLUCION_ESPERADA.items():
        if marca in ruta_imagen.name:
            resolucion_ok = (img.width == w and img.height == h)
            break

    mensajes = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": img},
                {"type": "text", "text": f"{contexto}\n\n{PROMPT_REVISION}"},
            ],
        }
    ]
    text = model.procesador.apply_chat_template(mensajes, tokenize=False, add_generation_prompt=True)
    inputs = model.procesador(text=[text], images=[img], return_tensors="pt")
    if torch.cuda.is_available():
        inputs = {k: v.to("cuda") for k, v in inputs.items()}

    with torch.inference_mode():
        outputs = model.generate(**inputs, max_new_tokens=200)
    respuesta = model.procesador.batch_decode(outputs, skip_special_tokens=True)[0]

    # Extraer el JSON de la respuesta
    m = re.search(r"\{.*\}", respuesta, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            data = {"puntaje": 0, "clickability": "pendiente",
                    "problemas": [respuesta[:200]], "sugerencia": "Respuesta no-JSON"}
    else:
        data = {"puntaje": 0, "clickability": "pendiente",
                "problemas": [respuesta[:200]], "sugerencia": "Sin JSON"}

    if resolucion_ok is not None:
        data["resolucion_ok"] = resolucion_ok
        data.setdefault("problemas", [])
        if not resolucion_ok:
            data["problemas"].append(f"Resolucion incorrecta: {img.width}x{img.height}")

    data["archivo"] = ruta_imagen.name
    return data


def _revisar_con_api(ruta_imagen: Path, contexto: str) -> dict:
    # TODO: conectar con la API de MiniMax M3 cuando el usuario la provea.
    print(f"  [INFO] Backend API no configurado. Veredicto provisional para {ruta_imagen.name}.")
    return {
        "archivo": ruta_imagen.name,
        "puntaje": 0,
        "clickability": "pendiente",
        "problemas": ["Backend de revision no configurado"],
        "sugerencia": "Configurar API o backend local de MiniMax M3",
    }


def _revisar_con_local(ruta_imagen: Path, contexto: str) -> dict:
    return _revisar_con_vl(ruta_imagen, contexto)


def revisar(ruta_imagen: Path, backend: str = BACKEND) -> dict:
    contexto = f"Miniatura para video: {ruta_imagen.stem}"
    if backend == "local":
        return _revisar_con_local(ruta_imagen, contexto)
    return _revisar_con_api(ruta_imagen, contexto)


def main():
    parser = argparse.ArgumentParser(description="Revisa miniaturas/tarjetas/frames con un modelo multimodal.")
    parser.add_argument("imagen", nargs="?", help="Ruta a una imagen especifica")
    parser.add_argument("--procesar", action="store_true", help="Revisar todas las miniaturas y tarjetas")
    parser.add_argument("--frames", action="store_true", help="Revisar los frames de control de videos (_frames/)")
    parser.add_argument("--backend", choices=["api", "local"], default=BACKEND)
    args = parser.parse_args()

    imagenes: list[Path] = []
    if args.imagen:
        imagenes = [Path(args.imagen)]
    elif args.frames:
        if not CARPETA_FRAMES.exists():
            print(f"No existe {CARPETA_FRAMES}/. Genera frames con: ensamblar_video.py --verificar")
            return
        imagenes = sorted(CARPETA_FRAMES.glob("*.png"))
    elif args.procesar:
        if not CARPETA_MINIATURAS.exists():
            print(f"No existe {CARPETA_MINIATURAS}/")
            return
        imagenes = sorted(CARPETA_MINIATURAS.glob("*.png"))
        if CARPETA_TARJETAS.exists():
            imagenes += sorted(CARPETA_TARJETAS.glob("*.png"))
    else:
        print("Especifica una imagen, --procesar o --frames.")
        return

    if not imagenes:
        print("No se encontraron imagenes para revisar.")
        return

    resultados = []
    for img in imagenes:
        print(f"Revisando {img.name}...")
        resultados.append(revisar(img, args.backend))

    print("\n=== RESULTADOS ===")
    for r in resultados:
        print(f"  {r['archivo']}: puntaje={r.get('puntaje')} "
              f"clickability={r.get('clickability')} "
              f"resolucion_ok={r.get('resolucion_ok', 'n/a')}")
        for p in r.get("problemas", []):
            print(f"      - {p}")

    print("\nListo. Revisar resultados y regenerar los que fallen.")


if __name__ == "__main__":
    main()

