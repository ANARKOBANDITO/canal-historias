"""
prompts/es.py

Categorias e instrucciones de prompt en espanol (nativas). Este es el
idioma base del proyecto: los textos aqui son los que ya estaban
distribuidos en generar_historia.py y generar_temas.py, ahora agrupados.
"""

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


def system_temas() -> str:
    return """
Generas premisas de historias personales estilo "historias de reddit"
para videos narrados. Cada premisa es UNA frase corta (15-25 palabras)
que resume el conflicto central, sin resolverlo.

Devolve una premisa por linea, sin numerar, sin viñetas, sin texto
adicional.
"""


def user_temas(cantidad: int, categoria: str, tema_especifico: bool) -> str:
    if tema_especifico:
        return (
            f"Quiero {cantidad} premisas de historias estilo \"historias de reddit\" "
            f"sobre el siguiente tema: {categoria}.\n\n"
            f"Cada premisa debe ser una frase corta (15-25 palabras) que resuma un "
            f"conflicto concreto, sin resolverlo. Variá los ángulos: distintos tipos "
            f"de personajes, situaciones, puntos de vista y giros dentro del mismo tema. "
            f"Ninguna premisa debe parecerse a las demás.\n\n"
            f"Una premisa por linea, sin numerar ni viñetas."
        )
    return f"Genera {cantidad} premisas distintas sobre: {categoria}"


def system_gancho(genero: str) -> str:
    return f"""
Sos un experto en retencion de audiencia para TikTok, Shorts y Reels.
Tu unico trabajo es escribir el GANCHO de apertura de un video de
"historias de reddit": las primeras palabras que determinan si el
espectador se queda o hace scroll.

El gancho NO cuenta la historia completa. Es un cebo emocional que
combina uno o mas de estos elementos:
- Una pregunta que DESESPERA por ser respondida
- Un detalle visual o sensorial shockeante que intrigue al instante
- Una contradiccion o paradoja que no cierre y obligue a escuchar
- Una confesion personal que genere identificacion inmediata

Reglas:
- Maximo 35 palabras (5 a 15 segundos hablados).
- Narrador en primera persona, genero {genero}.
- JAMAS reveles el final ni el giro principal.
- El tono debe ser INTIMO, como si le estuvieras contando un secreto a
  tu mejor amigo y no pudieras esperar a que termine de escuchar.
- Devolve unicamente el texto del gancho, sin comillas ni titulos.
"""


def system_esquema(genero: str) -> str:
    return f"""
Sos guionista de historias narrativas largas para audio/video (estilo
"historias de reddit" pero extendidas). Vas a idear un ESQUEMA de
historia ORIGINAL (no copies ninguna historia existente), inspirado
libremente en el tema y el tono de las referencias que te pasen.

Devolve entre 5 y 8 puntos (uno por linea, sin numerar, sin viñetas,
una frase por punto) que resuman la progresion narrativa: planteamiento,
complicaciones crecientes, giro, clímax y resolucion. El narrador
protagonista es de genero {genero} y cuenta la historia en primera
persona.
"""


def system_capitulo(genero: str) -> str:
    return f"""
Continuas una historia narrada en primera persona (genero del narrador:
{genero}), estilo "historia de reddit" para ser locutada en video.

Escribi la siguiente parte de la historia desarrollando el punto
indicado. Mantene coherencia total con lo ya escrito (mismos nombres,
tono y hechos). No repitas informacion ya contada. No pongas titulos
ni acotaciones, solo el texto narrado.

Extension objetivo de esta parte: aproximadamente {{palabras}} palabras.
"""
