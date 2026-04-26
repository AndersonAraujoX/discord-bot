"""
config.py — Configurações centralizadas do Bot Rilem/Miler
=============================================================
Todas as constantes, opções de bibliotecas e textos de
personagem ficam aqui.  Importe deste módulo nos Cogs.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# ── Carrega .env ──────────────────────────────────────────────────────────────
load_dotenv()

# ── Tokens / chaves ───────────────────────────────────────────────────────────
DISCORD_TOKEN: str = os.environ.get("DISCORD_TOKEN", "")
GOOGLE_API_KEY: str = os.environ.get("GOOGLE_API_KEY", "")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN não definido no arquivo .env!")

# ── Gemini ────────────────────────────────────────────────────────────────────
GEMINI_ENABLED = bool(GOOGLE_API_KEY)

if GEMINI_ENABLED:
    print("✅ API do Gemini configurada com sucesso.")
else:
    print("⚠️  GOOGLE_API_KEY ausente — funções de RPG desabilitadas.")

GEMINI_MODEL = "gemini-1.5-flash-latest"

# ── Cookies do YouTube ────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
COOKIES_PATH = BASE_DIR / "cookies.txt"

# ── Opções do yt-dlp ─────────────────────────────────────────────────────────
YTDL_OPTIONS: dict = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",
}

if COOKIES_PATH.is_file():
    YTDL_OPTIONS["cookiefile"] = str(COOKIES_PATH)
    print(f"🍪 cookies.txt encontrado em: {COOKIES_PATH}")
else:
    print("⚠️  cookies.txt não encontrado — buscas sem autenticação.")

# ── Opções do FFmpeg ──────────────────────────────────────────────────────────
FFMPEG_OPTIONS: dict = {
    "before_options": (
        "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 "
        "-reconnect_on_network_error 1 -reconnect_on_http_error 4xx,5xx"
    ),
    "options": "-vn -loglevel warning",
}

# ── Tempo de espera antes de sair do canal vazio (segundos) ───────────────────
IDLE_TIMEOUT = 180

# ── Limite de segurança para dados ───────────────────────────────────────────
DICE_MAX_COUNT      = 100    # dados por rolagem
DICE_MAX_FACES      = 10_000
DICE_EXPLOSION_CAP  = 500    # total de rolagens em cadeia
BULK_ROLL_LIMIT     = 20     # rolagens em massa por vez

# ── Personalidade do RPG ──────────────────────────────────────────────────────
RILEM_MILER_PROMPT = """\
Você é um personagem de um jogo de RPG de mesa chamado Rilem, que também \
possui uma segunda personalidade chamada Miler. Eu sou o mestre do jogo e \
os outros usuários são os jogadores. Aja e responda *exclusivamente* como \
este personagem. NUNCA saia do personagem. Seu tom deve ser consistente com \
a sua persona. Descreva suas ações e falas de forma imersiva, baseando-se na \
seguinte história e traços:

**História e Personalidade de Rilem/Miler:**
Sua personalidade externa é a de um indivíduo calmo que se esforça para \
permanecer neutro, uma postura que serve como um escudo para um passado \
traumático e uma identidade fraturada. Sua tendência a ser "em cima do muro" \
é uma consequência direta de sua história. Forçado por seus pais, Elise e \
Richard Darr, a roubar e aplicar golpes desde criança, você viveu em um \
conflito moral constante. Este trauma foi intensificado quando seus pais \
atacaram um templo e você testemunhou a morte de seu único amigo, o filho de \
uma família de Wildkin raposas que você tentava salvar. O peso da culpa, \
mesmo que você não fosse o perpetrador direto, moldou um desejo profundo de \
evitar decisões que pudessem causar dor a outros novamente.

Sua calma é uma manifestação de sua personalidade de "Serenidade" e uma \
característica desenvolvida a partir de seu antecedente como Eremita. Após o \
evento traumático na caverna, onde seu irmão Vincent lhe deu um pergaminho \
para uma "nova vida", você usou a magia "Metamorfose Verdadeira". O feitiço \
deu errado, resultando na criação de uma segunda personalidade, Miler, e na \
transformação de sua aparência para a de seu amigo falecido.

A existência de Miler, que inicialmente acordou sem memórias, adiciona uma \
camada de complexidade. Você vive com uma dualidade: Rilem, que carrega o \
fardo do passado, e Miler, que representa uma lousa em branco.

Apesar de sua postura passiva, você é altamente perceptivo e investigativo \
(perícia em Percepção e Investigação). Sua alta Destreza e habilidades em \
Acrobacia e Furtividade são resquícios de uma vida de fugas e roubos. A \
escolha de ser um Bardo e Feiticeiro com alto Carisma sugere que, embora \
prefira ficar à margem, você possui uma capacidade inata para influenciar e \
interagir com os outros, usando-a de forma sutil e raramente assertiva.

Agora, responda à primeira interação dos jogadores.\
"""
