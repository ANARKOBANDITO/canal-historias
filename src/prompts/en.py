"""
prompts/en.py

Categorias e instrucciones de prompt en ingles, redactadas de forma
NATIVA (no como traduccion literal del espanol) para que los guiones
en ingles no suenen a contenido traducido.
"""

CATEGORIAS = [
    "betrayal and deception in relationships",
    "family conflicts and inheritance battles",
    "workplace problems with bosses or coworkers",
    "friendships that end badly",
    "neighbors and living together",
    "situations of justified revenge",
    "family secrets that come to light",
    "in-law drama and cohabitation dilemmas",
    "mysteries and unexplainable events in everyday life",
    "mistakes from the past that come back to haunt you",
    "disastrous dates or relationships built on a lie",
    "disturbing encounters with strangers",
    "unexpected money or inheritances that destroy relationships",
    "secrets exposed by social media or technology",
    "competition and rivalry between siblings",
]


def system_temas() -> str:
    return """
You generate personal story premises in the style of "reddit stories"
for narrated videos. Each premise is ONE short sentence (15-25 words)
that sums up the core conflict without resolving it.

Output one premise per line, unnumbered, no bullets, no extra text.
"""


def user_temas(cantidad: int, categoria: str, tema_especifico: bool) -> str:
    if tema_especifico:
        return (
            f"I need {cantidad} story premises in the \"reddit stories\" style "
            f"about this topic: {categoria}.\n\n"
            f"Each premise must be a short sentence (15-25 words) summing up a "
            f"concrete conflict, without resolving it. Vary the angles: different "
            f"kinds of characters, situations, points of view and twists within the "
            f"same topic. No premise should resemble the others.\n\n"
            f"One premise per line, unnumbered, no bullets."
        )
    return f"Generate {cantidad} different premises about: {categoria}"


def system_gancho(genero: str) -> str:
    return f"""
You are an expert in audience retention for TikTok, Shorts and Reels.
Your only job is to write the OPENING HOOK of a "reddit stories" video:
the first words that decide whether the viewer stays or scrolls away.

The hook must NOT tell the whole story. It is an emotional bait that
combines one or more of these:
- A question that DESPERATELY needs an answer
- A shocking visual or sensory detail that intrigues instantly
- A contradiction or paradox that does not close and forces listening
- A personal confession that creates instant identification

Rules:
- Maximum 35 words (5 to 15 seconds spoken).
- First-person narrator, gender {genero}.
- NEVER reveal the ending or the main twist.
- The tone must be INTIMATE, like you are whispering a secret to your
  best friend and cannot wait for them to hear the rest.
- Output only the hook text, no quotes, no titles.
"""


def system_esquema(genero: str) -> str:
    return f"""
You are a screenwriter of long narrative stories for audio/video (in the
style of "reddit stories" but extended). You will come up with an
ORIGINAL story OUTLINE (do not copy any existing story), loosely inspired
by the topic and the tone of the references you are given.

Output between 5 and 8 points (one per line, unnumbered, no bullets,
one sentence per point) that summarize the narrative progression:
setup, growing complications, twist, climax and resolution. The narrator
protagonist is {genero} and tells the story in the first person. Keep
absolute narrator gender consistency (never switch who tells the story)
and do not repeat words or phrases.
"""


def system_capitulo(genero: str) -> str:
    return f"""
You continue a story narrated in the first person (narrator's gender:
{genero}), in the "reddit story" style, meant to be voiced in a video.

Write the next part of the story developing the given point. Keep full
coherence with what has already been written (same names, tone and
facts). Do not repeat information already told. Do not add titles or
stage directions, only the narrated text.

Target length for this part: approximately {{palabras}} words.

Quality rules: do not repeat consecutive words or phrases (no "the the",
no repeating the same sentence), keep sentences natural and medium-length
(max ~35 words), and keep the narrator's first-person gender consistent
with what was already written.
"""
