"""
generar_temas.py

Genera automaticamente ideas de historias nuevas (sin que vos tengas
que buscarlas en ningun lado), usando DeepSeek para inventar premisas
variadas y el banco de temas local para descartar las que sean
demasiado parecidas a una que ya usaste.

El resultado se guarda en temas_pendientes.txt, uno por linea, listo
para que generar_lote.py los procese.

Uso (desde la raiz del proyecto):
    python src/generar_temas.py --cantidad 10
    python src/generar_temas.py --cantidad 5 --tema "traicion familiar"
    python src/generar_temas.py --cantidad 3 --tema "venganza post infidelidad"

Requisitos:
    pip install openai sentence-transformers numpy
"""

import argparse
import os
from pathlib import Path

from openai import OpenAI

from banco_temas import cargar_banco, agregar_tema, es_tema_repetido

API_KEY = os.environ.get("DEEPSEEK_API_KEY")
BASE_URL = "https://api.deepseek.com/v1"
MODEL = "deepseek-v4-flash"

ARCHIVO_PENDIENTES = Path("data/temas_pendientes.txt")

CATEGORIAS = [
    "traiciones y engaños en pareja",
    "conflictos familiares y herencias",
    "problemas en el trabajo con jefes o compañeros",
    "amistades que terminan mal",
    "vecinos y convivencia",
    "situaciones de venganza justificada",
    "secretos familiares que salen a la luz",
    "dilemas de convivencia con suegros",
    "misterios y eventos inexplicables en la vida cotidiana",
    "errores del pasado que regresan a cobrar factura",
    "citas desastrosas o relaciones que empiezan con una mentira",
    "encuentros perturbadores con desconocidos",
    "dinero o herencias inesperadas que destruyen relaciones",
    "secretos expuestos por redes sociales o tecnología",
    "competencia y rivalidad entre hermanos",
]


def _cliente() -> OpenAI:
    if not API_KEY:
        raise RuntimeError("Falta la variable de entorno DEEPSEEK_API_KEY.")
    return OpenAI(api_key=API_KEY, base_url=BASE_URL)


def proponer_temas(categoria: str, cantidad: int, tema_especifico: bool = False) -> list[str]:
    cliente = _cliente()
    system = """
Generas premisas de historias personales estilo "historias de reddit"
para videos narrados. Cada premisa es UNA frase corta (15-25 palabras)
que resume el conflicto central, sin resolverlo.

Devolve una premisa por linea, sin numerar, sin viñetas, sin texto
adicional.
"""

    if tema_especifico:
        user = (
            f"Quiero {cantidad} premisas de historias estilo \"historias de reddit\" "
            f"sobre el siguiente tema: {categoria}.\n\n"
            f"Cada premisa debe ser una frase corta (15-25 palabras) que resuma un "
            f"conflicto concreto, sin resolverlo. Variá los ángulos: distintos tipos "
            f"de personajes, situaciones, puntos de vista y giros dentro del mismo tema. "
            f"Ninguna premisa debe parecerse a las demás.\n\n"
            f"Una premisa por linea, sin numerar ni viñetas."
        )
    else:
        user = f"Genera {cantidad} premisas distintas sobre: {categoria}"

    respuesta = cliente.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=1.1,
        max_tokens=max(400, 120 * cantidad),
        extra_body={"thinking": {"type": "disabled"}},
    )
    lineas = respuesta.choices[0].message.content.strip().split("\n")
    return [l.strip("-• ").strip() for l in lineas if l.strip()]


def generar_temas_unicos(cantidad_objetivo: int, tema_especifico: str | None = None) -> list[str]:
    banco = cargar_banco()
    temas_nuevos = []
    intentos = 0
    max_intentos = cantidad_objetivo * 3

    if tema_especifico:
        while len(temas_nuevos) < cantidad_objetivo and intentos < max_intentos:
            faltan = cantidad_objetivo - len(temas_nuevos)
            candidatos = proponer_temas(tema_especifico, cantidad=min(5, faltan + 2), tema_especifico=True)

            for tema in candidatos:
                if len(temas_nuevos) >= cantidad_objetivo:
                    break
                if es_tema_repetido(tema, banco):
                    print(f"  Descartado (muy parecido a uno anterior): {tema[:70]}")
                    continue
                banco = agregar_tema(tema, banco)
                temas_nuevos.append(tema)
                print(f"  Nuevo tema: {tema[:70]}")

            intentos += 1
    else:
        while len(temas_nuevos) < cantidad_objetivo and intentos < max_intentos:
            categoria = CATEGORIAS[intentos % len(CATEGORIAS)]
            candidatos = proponer_temas(categoria, cantidad=5)

            for tema in candidatos:
                if len(temas_nuevos) >= cantidad_objetivo:
                    break
                if es_tema_repetido(tema, banco):
                    print(f"  Descartado (muy parecido a uno anterior): {tema[:70]}")
                    continue
                banco = agregar_tema(tema, banco)
                temas_nuevos.append(tema)
                print(f"  Nuevo tema: {tema[:70]}")

            intentos += 1

    return temas_nuevos


def main():
    parser = argparse.ArgumentParser(description="Genera temas de historias nuevos automaticamente.")
    parser.add_argument("--cantidad", type=int, default=10, help="Cuantos temas nuevos generar")
    parser.add_argument("--tema", type=str, default=None, help="Tema o idea especifica para generar las premisas (ej: traicion familiar, venganza, infidelidad). Si no se pasa, se usan categorias variadas.")
    args = parser.parse_args()

    if args.tema:
        print(f"Generando {args.cantidad} temas sobre \"{args.tema}\"...\n")
    else:
        print(f"Generando {args.cantidad} temas nuevos y unicos (categorias variadas)...\n")

    temas = generar_temas_unicos(args.cantidad, tema_especifico=args.tema)

    with open(ARCHIVO_PENDIENTES, "a", encoding="utf-8") as f:
        for tema in temas:
            f.write(tema + "\n")

    print(f"\nListo. {len(temas)} temas agregados a {ARCHIVO_PENDIENTES}")


if __name__ == "__main__":
    main()
