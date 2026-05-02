import discord
from discord import app_commands
from discord.ext import commands

from utils.storage import load_rpg_data, save_rpg_data

class RpgDoomCog(commands.Cog, name="RPG Relógio do Juízo"):
    """Relógio do Fim do Mundo (Doom Clock)."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    doom_group = app_commands.Group(name="doom", description="O Relógio do Juízo Final.")

    def _render_clock(self, ticks: int) -> str:
        clocks = ["🕛", "🕐", "🕑", "🕒", "🕓", "🕔", "🕕", "🕖", "🕗", "🕘", "🕙", "🕚", "🕛"]
        return clocks[min(12, max(0, ticks))]

    @doom_group.command(name="avancar", description="Mestre: Avança (ou recua) o Relógio do Juízo.")
    async def doom_avancar(self, interaction: discord.Interaction, ticks: int, motivo: str) -> None:
        data = load_rpg_data()
        doom = data.setdefault("doom_clock", 0)
        data["doom_clock"] = max(0, min(12, doom + ticks))
        save_rpg_data(data)
        
        embed = discord.Embed(title="⏳ O Relógio Avança...", description=f"*{motivo}*", color=discord.Color.dark_red())
        embed.add_field(name="Status do Fim do Mundo", value=f"{self._render_clock(data['doom_clock'])} ({data['doom_clock']}/12)")
        
        if data["doom_clock"] == 12:
            embed.description += "\n\n🚨 **O TEMPO ACABOU! O EVENTO APOCALÍPTICO COMEÇA!** 🚨"
            
        await interaction.response.send_message(embed=embed)

    @doom_group.command(name="status", description="Visualiza o estado atual do Relógio.")
    async def doom_status(self, interaction: discord.Interaction) -> None:
        data = load_rpg_data()
        doom = data.get("doom_clock", 0)
        
        embed = discord.Embed(title="⏳ Relógio do Juízo Final", description=f"{self._render_clock(doom)} ({doom}/12)", color=discord.Color.dark_grey())
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RpgDoomCog(bot))
