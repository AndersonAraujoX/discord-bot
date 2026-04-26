"""
cogs/geral.py — Eventos globais e respostas simples sem prefixo
===============================================================
"""

import discord
from discord.ext import commands


HELP_TEXT = (
    "**Meus Comandos:**\n"
    "🎵 **Música (`!`):** `!play <nome ou link>`, `!skip`, `!pause`, `!resume`, "
    "`!queue`, `!join`, `!leave`, `!loop <song/queue/off>`\n"
    "   *(YouTube, SoundCloud, etc.)*\n"
    "🎲 **Dados (`!roll`):** `!roll 4d6`, `!roll d20!`, `!roll 4d6d1`, `!roll 6#4d6d1`\n"
    "🤖 **RPG com IA:** `!rpg_start` inicia Rilem/Miler · `!rpg_stop` encerra\n"
    "   *(Após iniciar, mencione o bot para interagir)*"
)

# Mapa de palavras-chave → resposta (sem prefixo)
_RESPOSTAS_EXATAS: dict[str, str] = {
    "ping": "Pong! 🏓",
    "oi":   None,   # resposta especial — usa mention
    "olá":  None,
    "ola":  None,
}


class GeralCog(commands.Cog, name="Geral"):
    """Eventos e interações gerais do bot."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ── Eventos ───────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print(f"🤖 Bot conectado como {self.bot.user}")
        print("   Pronto para tudo!")
        print("─" * 40)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.bot.user:
            return

        # RPG é tratado pelo RpgCog — apenas propaga o evento aqui
        content = message.content.lower().strip()

        if content == "ping":
            await message.channel.send("Pong! 🏓")

        elif content in ("oi", "olá", "ola"):
            await message.channel.send(f"Olá, {message.author.mention}! Tudo bem?")

        elif "ajuda" in content and not message.content.startswith("!"):
            await message.channel.send(HELP_TEXT)

        # O discord.py já processa os comandos automaticamente, 
        # não precisamos chamar process_commands aqui.
        pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GeralCog(bot))
