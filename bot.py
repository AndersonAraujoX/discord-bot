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


class RilemBot(commands.Bot):
    async def setup_hook(self) -> None:
        for cog in COGS:
            await self.load_extension(cog)
            print(f"   ✔ Cog carregado: {cog}")
        
        # Sincroniza a árvore de comandos Slash
        await self.tree.sync()
        print("   ✔ Árvore de Slash Commands sincronizada!")

def create_bot() -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states    = True
    return RilemBot(command_prefix="!", intents=intents)

async def main() -> None:
    bot = create_bot()
    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
