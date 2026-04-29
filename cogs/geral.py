"""
cogs/geral.py — Eventos globais e respostas simples sem prefixo
===============================================================
"""

import discord
from discord import app_commands
from discord.ext import commands


HELP_TEXT = (
    "**Meus Comandos (Agora todos em `/`):**\n"
    "🎵 **Música:** `/play`, `/skip`, `/pause`, `/resume`, `/queue`, `/radio`, `/playlist`, `/loop`\n"
    "🎲 **RPG & Dados:** `/dados`, `/teste`, `/atacar`, `/hp`, `/turno`, `/status`, `/encontro`, `/loot`\n"
    "🤖 **RPG com IA:** `/rpg_start` inicia Rilem/Miler · `/rpg_stop` encerra\n"
    "   *(Após iniciar, mencione o bot para interagir)*"
)

# Mapa de palavras-chave → resposta (sem prefixo)
_RESPOSTAS_EXATAS: dict[str, str] = {
    "oi":   None,   # resposta especial — usa mention
    "olá":  None,
    "ola":  None,
}


class GeralCog(commands.Cog, name="Geral"):
    """Eventos e interações gerais do bot."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ── Slash Commands ────────────────────────────────────────────────────────
    
    @app_commands.command(name="ping", description="Verifica se o bot está online e sua latência.")
    async def ping(self, interaction: discord.Interaction) -> None:
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! 🏓 Latência: {latency}ms")

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

        content = message.content.lower().strip()

        if content in ("oi", "olá", "ola"):
            await message.channel.send(f"Olá, {message.author.mention}! Tudo bem?")

        elif "ajuda" in content and not message.content.startswith("/"):
            await message.channel.send(HELP_TEXT)

        pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GeralCog(bot))
