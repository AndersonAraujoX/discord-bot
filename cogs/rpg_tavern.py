import discord
from discord import app_commands
from discord.ext import commands
import random

from utils.storage import load_rpg_data, save_rpg_data

class RpgTavernCog(commands.Cog, name="RPG Taverna"):
    """Minigames e apostas em tavernas."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    taverna_group = app_commands.Group(name="taverna", description="Apostas e minigames.")

    @taverna_group.command(name="aposta", description="Jogue os dados na taverna valendo Gold da party!")
    async def taverna_aposta(self, interaction: discord.Interaction, aposta: int) -> None:
        data = load_rpg_data()
        gold = data["party"].setdefault("gold", 0)
        
        if gold < aposta:
            return await interaction.response.send_message(f"💸 A party não tem {aposta}g para apostar! (Gold atual: {gold}g)", ephemeral=True)
            
        # Jogo simples de Maior ganha (Player vs Casa) rolando d100
        player_roll = random.randint(1, 100)
        house_roll = random.randint(1, 100)
        
        msg = f"🎲 Você apostou **{aposta}g**.\nSeu dado: **{player_roll}** | Dado do Taverneiro: **{house_roll}**\n"
        
        if player_roll > house_roll:
            msg += f"\n🎉 **Você VENCEU!** Ganhou +{aposta}g."
            data["party"]["gold"] += aposta
        else:
            msg += f"\n💀 **Você PERDEU!** Perdeu -{aposta}g."
            data["party"]["gold"] -= aposta
            
        save_rpg_data(data)
        msg += f"\nOuro restante na Party: **{data['party']['gold']}g**."
        
        await interaction.response.send_message(msg)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RpgTavernCog(bot))
