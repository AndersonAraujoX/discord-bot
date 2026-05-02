import discord
from discord import app_commands
from discord.ext import commands

from utils.storage import load_rpg_data, save_rpg_data

class RpgFactionsCog(commands.Cog, name="RPG Facções"):
    """Gerencia reputação com facções e reinos."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    faccao_group = app_commands.Group(name="faccao", description="Gerencia reputação com facções.")

    @faccao_group.command(name="status", description="Mostra a reputação da party com o mundo.")
    async def faccao_status(self, interaction: discord.Interaction) -> None:
        data = load_rpg_data()
        faccoes = data.setdefault("faccoes", {})
        
        if not faccoes:
            return await interaction.response.send_message("A party ainda não é conhecida por nenhuma facção.", ephemeral=True)
            
        embed = discord.Embed(title="🤝 Reputação com Facções", color=discord.Color.blue())
        for nome, rep in faccoes.items():
            status = "Aliado" if rep >= 5 else "Inimigo" if rep <= -5 else "Neutro"
            embed.add_field(name=nome, value=f"{rep}/10 ({status})", inline=False)
            
        await interaction.response.send_message(embed=embed)

    @faccao_group.command(name="alterar", description="Mestre: Altera a reputação com uma facção (-10 a 10).")
    async def faccao_alterar(self, interaction: discord.Interaction, faccao: str, valor: int) -> None:
        data = load_rpg_data()
        faccoes = data.setdefault("faccoes", {})
        faccoes[faccao] = max(-10, min(10, faccoes.get(faccao, 0) + valor))
        save_rpg_data(data)
        
        await interaction.response.send_message(f"A reputação da party com **{faccao}** mudou em {valor:+}! (Atual: {faccoes[faccao]})")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RpgFactionsCog(bot))
