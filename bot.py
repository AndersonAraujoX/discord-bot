"""
bot.py — Ponto de entrada do Bot Rilem/Miler
=============================================
Apenas inicializa o bot e carrega os Cogs.
Toda lógica vive em cogs/ e utils/.
"""

import asyncio
import discord
from discord.ext import commands

from config import DISCORD_TOKEN
from cogs import COGS


def create_bot() -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states    = True
    return commands.Bot(command_prefix="!", intents=intents)


async def main() -> None:
    bot = create_bot()

    async with bot:
        for cog in COGS:
            await bot.load_extension(cog)
            print(f"   ✔ Cog carregado: {cog}")
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
