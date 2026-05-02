import discord
from discord import app_commands
from discord.ext import commands

from utils.storage import load_rpg_data, save_rpg_data
from utils.ai_helper import generate_ai_response

class RpgCraftCog(commands.Cog, name="RPG Forja"):
    """Sistemas de forja e criação de itens."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    craft_group = app_commands.Group(name="craft", description="Sistemas de forja e criação de itens.")

    @craft_group.command(name="forjar", description="Forja um item a partir de materiais da mochila.")
    async def craft_forjar(self, interaction: discord.Interaction, material_1: str, material_2: str) -> None:
        await interaction.response.defer()
        data = load_rpg_data()
        inv = data["party"].setdefault("inventory", [])
        
        prompt = (
            f"Eu estou misturando '{material_1}' com '{material_2}' em uma forja mágica de RPG. "
            f"Crie UM nome épico para a arma ou item resultante e DÊ uma breve descrição de 1 linha de seu poder. "
            f"Exemplo: 'A Lâmina Escarlate: Uma espada que emite chamas vermelhas ao cortar'."
        )
        resultado = await generate_ai_response(prompt)
        
        inv.append({
            "nome": f"Item Forjado ({material_1} + {material_2})",
            "desc": resultado,
            "peso": 2.0
        })
        save_rpg_data(data)
        
        embed = discord.Embed(title="⚒️ Forja Concluída!", description=f"Você combinou **{material_1}** e **{material_2}**.\n\n{resultado}", color=discord.Color.orange())
        await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RpgCraftCog(bot))
