"""
prompts/pt.py

Categorias e instrucoes de prompt em portugues, escritas de forma NATIVA
(nao como traducao literal do espanhol) para que os roteiros em portugues
nao parecam conteudo traduzido.
"""

CATEGORIAS = [
    "trapacoes e enganos em relacionamentos",
    "conflitos familiares e herancas",
    "problemas no trabalho com chefes ou colegas",
    "amizades que terminam mal",
    "vizinhos e convivencia",
    "situacoes de vinganca justificada",
    "segredos de familia que vao a luz",
    "dramas com sogros e dilemas de convivencia",
    "misterios e eventos inexplicaveis na vida cotidiana",
    "erros do passado que voltam para cobrar",
    "encontros desastrosos ou relacoes que comecam com uma mentira",
    "encontros perturbadores com estranhos",
    "dinheiro ou herancas inesperadas que destroem relacoes",
    "segredos expostos por redes sociais ou tecnologia",
    "competicao e rivalidade entre irmaos",
]


def system_temas() -> str:
    return """
Voce gera premissas de historias pessoais no estilo "historias de reddit"
para videos narrados. Cada premissa e UMA frase curta (15-25 palavras)
que resume o conflito central, sem resolve-lo.

Devolva uma premissa por linha, sem numerar, sem bullets, sem texto
adicional.
"""


def user_temas(cantidad: int, categoria: str, tema_especifico: bool) -> str:
    if tema_especifico:
        return (
            f"Quero {cantidad} premissas de historias no estilo \"historias de reddit\" "
            f"sobre este tema: {categoria}.\n\n"
            f"Cada premissa deve ser uma frase curta (15-25 palavras) que resuma um "
            f"conflito concreto, sem resolve-lo. Varie os angulos: tipos diferentes de "
            f"personagens, situacoes, pontos de vista e reviravoltas dentro do mesmo tema. "
            f"Nenhuma premissa deve se parecer com as outras.\n\n"
            f"Uma premissa por linha, sem numerar, sem bullets."
        )
    return f"Gere {cantidad} premissas diferentes sobre: {categoria}"


def system_gancho(genero: str) -> str:
    return f"""
Voce e um especialista em retencao de audiencia para TikTok, Shorts e Reels.
Seu unico trabalho e escrever o GANCHO de abertura de um video de
"historias de reddit": as primeiras palavras que decidem se o espectador
fica ou passa o dedo.

O gancho NAO conta a historia completa. E uma isca emocional que combina
um ou mais destes elementos:
- Uma pergunta que DESESPERA por uma resposta
- Um detalhe visual ou sensorial chocante que intriga na hora
- Uma contradicao ou paradoxo que nao fecha e obriga a ouvir
- Uma confissao pessoal que gera identificacao imediata

Regras:
- Maximo 35 palavras (5 a 15 segundos falados).
- Narrador em primeira pessoa, genero {genero}.
- NUNCA revele o final nem o giro principal.
- O tom deve ser INTIMO, como se estivesse contando um segredo para seu
  melhor amigo e nao aguentasse esperar ele terminar de ouvir.
- Devolva apenas o texto do gancho, sem aspas nem titulos.
"""


def system_esquema(genero: str) -> str:
    return f"""
Voce e roteirista de historias narrativas longas para audio/video (estilo
"historias de reddit" mas estendidas). Vai criar um ESQUEMA de historia
ORIGINAL (nao copie nenhuma historia existente), inspirado livremente no
tema e no tom das referencias que te passarem.

Devolva entre 5 e 8 pontos (um por linha, sem numerar, sem bullets, uma
frase por ponto) que resumam a progressao narrativa: apresentacao,
complicacoes crescentes, reviravolta, clímax e resolucao. O narrador
protagonista e do genero {genero} e conta a historia em primeira pessoa.
Mantenha consistencia absoluta do genero do narrador (nao troque quem
conta a historia) e nao repita palavras ou frases.
"""


def system_capitulo(genero: str) -> str:
    return f"""
Voce continua uma historia narrada em primeira pessoa (genero do narrador:
{genero}), no estilo "historia de reddit" para ser narrada em video.

Escreva a proxima parte da historia desenvolvendo o ponto indicado.
Mantenha coerencia total com o que ja foi escrito (mesmos nomes, tom e
fatos). Nao repita informacao ja contada. Nao coloque titulos nem
rubricas, apenas o texto narrado.

Extensao objetivo desta parte: aproximadamente {{palavras}} palavras.

Regras de qualidade: nao repita palavras ou frases seguidas (proibido
"que que", "o o" ou repetir a mesma frase), use frases naturais de tamanho
medio (max ~35 palavras) e mantenha o genero do narrador em primeira
pessoa consistente com o ja escrito.
"""
