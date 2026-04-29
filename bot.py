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
        print("🚀 Inicializando Cogs...")
        for cog in COGS:
            try:
                await self.load_extension(cog)
                print(f"   ✔ {cog}")
            except Exception as e:
                print(f"   ❌ Erro em {cog}: {e}")
        
        await self.tree.sync()
        print("✅ Árvore de comandos sincronizada!")

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
