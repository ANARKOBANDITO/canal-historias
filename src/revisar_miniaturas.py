"""
revisar_miniaturas.py

Revisa las miniaturas generadas (y opcionalmente la tarjeta Reddit y
videos cortos) usando MiniMax M3 (multimodal) para evaluar calidad y
"clickability". Devuelve un veredicto por elemento y sugiere regenerar
si algo falla.

Backends soportados:
    "api"   -> API de MiniMax M3 (se configura con la API key del usuario)
    "local" -> MiniMax M3 GGUF en GPU local (Vast.ai)

Uso (desde la raiz del proyecto):
    python src/revisar_miniaturas.py --procesar
    python src/revisar_miniaturas.py "output/miniaturas/x_miniatura.png"
"""

import argparse
from pathlib import Path

CARPETA_MINIATURAS = Path("output/miniaturas")
CARPETA_TARJETAS = Path("output/tarjetas")

BACKEND = "api"  # cambiara a "local" cuando se configure M3 GGUF en Vast.ai

PROMPT_REVISION = (
    "Eres un experto en thumbnails de YouTube. Evalua esta miniatura "
    "(y el contexto del titulo si se da). Responde SOLO con JSON: "
    '{"puntaje": 0-10, "clickability": "alta|media|baja", '
    '"problemas": [...], "sugerencia": "..."}'
)


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
    # TODO: conectar con MiniMax M3 GGUF (unsloth/MiniMax-M3-GGUF) en Vast.ai.
    print(f"  [INFO] Backend local M3 no configurado. Veredicto provisional para {ruta_imagen.name}.")
    return {
        "archivo": ruta_imagen.name,
        "puntaje": 0,
        "clickability": "pendiente",
        "problemas": ["Backend local M3 no configurado"],
        "sugerencia": "Configurar MiniMax M3 GGUF en Vast.ai",
    }


def revisar(ruta_imagen: Path, backend: str = BACKEND) -> dict:
    contexto = f"Miniatura para video: {ruta_imagen.stem}"
    if backend == "local":
        return _revisar_con_local(ruta_imagen, contexto)
    return _revisar_con_api(ruta_imagen, contexto)


def main():
    parser = argparse.ArgumentParser(description="Revisa miniaturas con MiniMax M3.")
    parser.add_argument("imagen", nargs="?", help="Ruta a una imagen especifica")
    parser.add_argument("--procesar", action="store_true", help="Revisar todas las miniaturas")
    parser.add_argument("--backend", choices=["api", "local"], default=BACKEND)
    args = parser.parse_args()

    imagenes: list[Path] = []
    if args.imagen:
        imagenes = [Path(args.imagen)]
    elif args.procesar:
        if not CARPETA_MINIATURAS.exists():
            print(f"No existe {CARPETA_MINIATURAS}/")
            return
        imagenes = sorted(CARPETA_MINIATURAS.glob("*.png"))
        if CARPETA_TARJETAS.exists():
            imagenes += sorted(CARPETA_TARJETAS.glob("*.png"))
    else:
        print("Especifica una imagen o usa --procesar.")
        return

    if not imagenes:
        print("No se encontraron imagenes para revisar.")
        return

    resultados = []
    for img in imagenes:
        print(f"Revisando {img.name}...")
        resultados.append(revisar(img, args.backend))

    for r in resultados:
        print(f"  {r['archivo']}: puntaje={r['puntaje']} clickability={r['clickability']}")

    print("\nListo. Revisar resultados y regenerar los que fallen.")


if __name__ == "__main__":
    main()
