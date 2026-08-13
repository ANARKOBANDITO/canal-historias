"""
generar_historia.py

Genera una historia ORIGINAL, inspirada en el tema, lista para narrar.
Incluye:

  1. Un gancho/sintesis corto (5-15 seg hablados) para enganchar en
     TikTok/Reels antes de arrancar la historia.
  2. La historia completa, en primera persona, pensada para 20-40
     minutos de locucion.

La historia se genera en varias llamadas encadenadas (esquema -> cada
capitulo) en vez de una sola, para que se mantenga coherente en textos
largos y para no depender de un limite de tokens gigante por llamada.

Uso (desde la raiz del proyecto):
    python src/generar_historia.py "traicion de un mejor amigo" --genero mujer --minutos 30

Requisitos:
    pip install openai
"""

import argparse
import os
import sys
from pathlib import Path

from openai import OpenAI

from variacion_narrativa import elegir_gancho, elegir_desenlace
from firma_editorial import agregar_firma
from prompts import cargar_idioma, genero_en_idioma

API_KEY = os.environ.get("DEEPSEEK_API_KEY")
BASE_URL = "https://api.deepseek.com/v1"
MODEL = "deepseek-v4-flash"

CARPETA_SALIDA = Path("output/guiones_listos")

# Palabras por minuto de locucion, para calcular la extension objetivo.
PALABRAS_POR_MINUTO = 145


def _cliente() -> OpenAI:
    if not API_KEY:
        raise RuntimeError(
            "No encontre la variable de entorno DEEPSEEK_API_KEY. Configurala antes de correr el script."
        )
    return OpenAI(api_key=API_KEY, base_url=BASE_URL)


def _leer_referencias(referencia_manual: str | None) -> str:
    """Devuelve el fragmento de un archivo de referencia manual (opcional)."""
    if not referencia_manual:
        return ""
    ruta = Path(referencia_manual)
    if ruta.exists():
        return ruta.read_text(encoding="utf-8")[:1500]
    return ""


def generar_gancho(tema: str, genero: str, referencias: str, prompts=None, idioma: str = "es") -> str:
    cliente = _cliente()
    if prompts is None:
        prompts = cargar_idioma(idioma)
    genero_nativo = genero_en_idioma(idioma, genero)
    system = prompts.system_gancho(genero_nativo)
    user = f"Tema de la historia: {tema}"
    gancho_info = elegir_gancho()
    user += f"\n\n{gancho_info['instruccion']}"
    if referencias:
        user += f"\n\nEjemplos de tono de historias parecidas (solo para inspirar el estilo, no copiar):\n{referencias}"

    respuesta = cliente.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=1.1,
        max_tokens=200,
        extra_body={"thinking": {"type": "disabled"}},
    )
    return respuesta.choices[0].message.content.strip()


def generar_esquema(tema: str, genero: str, minutos: int, referencias: str, prompts=None, idioma: str = "es") -> list[str]:
    """Devuelve una lista de 5 a 8 beats/actos que va a tener la historia."""
    cliente = _cliente()
    if prompts is None:
        prompts = cargar_idioma(idioma)
    genero_nativo = genero_en_idioma(idioma, genero)
    system = prompts.system_esquema(genero_nativo)
    user = f"Tema: {tema}\nDuracion objetivo de la historia completa: {minutos} minutos narrados."
    desenlace_info = elegir_desenlace()
    user += f"\n\n{desenlace_info['instruccion']}"
    if referencias:
        user += f"\n\nHistorias parecidas para inspirar el tono (no copiar hechos ni nombres):\n{referencias}"

    respuesta = cliente.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=1.0,
        max_tokens=4000,
        extra_body={"thinking": {"type": "disabled"}},
    )
    lineas = respuesta.choices[0].message.content.strip().split("\n")
    return [l.strip("-• ").strip() for l in lineas if l.strip()]


def expandir_capitulo(tema: str, genero: str, beat: str, contexto_previo: str, palabras_objetivo: int, prompts=None, idioma: str = "es") -> str:
    cliente = _cliente()
    if prompts is None:
        prompts = cargar_idioma(idioma)
    genero_nativo = genero_en_idioma(idioma, genero)
    system = prompts.system_capitulo(genero_nativo).replace("{palabras}", str(palabras_objetivo))
    user = f"""
Tema general de la historia: {tema}

Lo que ya se escribio hasta ahora (para mantener continuidad):
{contexto_previo[-2000:] if contexto_previo else "(esto es el inicio de la historia)"}

Punto a desarrollar ahora: {beat}
"""
    respuesta = cliente.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.9,
        max_tokens=max(int(palabras_objetivo * 2), 2000),
        extra_body={"thinking": {"type": "disabled"}},
    )
    return respuesta.choices[0].message.content.strip()


def generar_historia_completa(tema: str, genero: str, minutos: int, referencia_manual: str | None,
                             idioma: str = "es") -> tuple[str, str]:
    prompts = cargar_idioma(idioma)
    referencias = _leer_referencias(referencia_manual)

    print("Generando gancho...")
    gancho = generar_gancho(tema, genero, referencias, prompts, idioma)

    print("Generando esquema de la historia...")
    beats = generar_esquema(tema, genero, minutos, referencias, prompts, idioma)
    if not beats:
        raise RuntimeError(
            "El esquema de la historia volvió vacío. Probablemente max_tokens es muy bajo "
            "para que el modelo incluya su razonamiento interno (thinking) más la respuesta. "
            "Aumentá max_tokens en generar_esquema() o simplificá el tema e intentalo de nuevo."
        )
    print(f"  {len(beats)} partes planificadas.")

    palabras_totales = minutos * PALABRAS_POR_MINUTO
    palabras_por_beat = palabras_totales // len(beats)

    partes = []
    contexto = ""
    for i, beat in enumerate(beats, 1):
        print(f"Escribiendo parte {i}/{len(beats)}: {beat[:60]}...")
        texto = expandir_capitulo(tema, genero, beat, contexto, palabras_por_beat, prompts, idioma)
        partes.append(texto)
        contexto += "\n\n" + texto

    historia_completa = "\n\n".join(partes)
    return gancho, historia_completa


def main():
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    parser = argparse.ArgumentParser(description="Genera una historia original inspirada en tu banco de historias.")
    parser.add_argument("tema", help='Tema o consulta, ej: "traicion de un mejor amigo"')
    parser.add_argument("--genero", choices=["hombre", "mujer"], default="mujer", help="Genero del narrador protagonista")
    parser.add_argument("--minutos", type=int, default=30, help="Duracion objetivo en minutos narrados (20-40 recomendado)")
    parser.add_argument("--idioma", choices=["es", "en", "pt"], default="es",
                        help="Idioma nativo del guion (default: es)")
    parser.add_argument("--referencia", default=None, help="Ruta a un .txt puntual para usar como inspiracion de estilo")
    parser.add_argument("--salida", default=None, help="Nombre del archivo de salida (por defecto se autogenera)")
    args = parser.parse_args()

    gancho, historia = generar_historia_completa(args.tema, args.genero, args.minutos, args.referencia, args.idioma)

    guion_final = f"{gancho}\n\n---\n\n{historia}"
    guion_final = agregar_firma(guion_final)
    guion_final = f"[GENERO: {args.genero}]\n[IDIOMA: {args.idioma}]\n\n{guion_final}"

    CARPETA_SALIDA.mkdir(exist_ok=True)
    nombre_archivo = args.salida or (args.tema.lower().replace(" ", "_")[:40] + ".txt")
    ruta_salida = CARPETA_SALIDA / nombre_archivo
    ruta_salida.write_text(guion_final, encoding="utf-8")

    print(f"\nListo. Guion guardado en: {ruta_salida}")
    print(f"Palabras totales: {len(guion_final.split())} (~{len(guion_final.split()) / PALABRAS_POR_MINUTO:.1f} min narrados)")


if __name__ == "__main__":
    main()
