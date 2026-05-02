import discord
from discord import app_commands
from discord.ext import commands

from utils.storage import load_rpg_data, save_rpg_data

class RpgLoreCog(commands.Cog, name="RPG Lore e Bestiário"):
    """Enciclopédia de monstros e fatos da campanha."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    bestiario_group = app_commands.Group(name="bestiario", description="Enciclopédia de monstros.")
    lore_group = app_commands.Group(name="lore", description="Registros da história do mundo.")

    @bestiario_group.command(name="catalogar", description="Registra um novo monstro no bestiário.")
    async def bestiario_catalogar(self, interaction: discord.Interaction, nome: str, fraqueza: str, descricao: str) -> None:
        data = load_rpg_data()
        bestiario = data.setdefault("bestiario", {})
        
        bestiario[nome.lower()] = {
            "nome": nome,
            "fraqueza": fraqueza,
            "descricao": descricao
        }
        save_rpg_data(data)
        
        await interaction.response.send_message(f"🐉 **{nome}** foi adicionado ao Bestiário da Party!")

    @bestiario_group.command(name="ler", description="Consulta um monstro.")
    async def bestiario_ler(self, interaction: discord.Interaction, nome: str) -> None:
        data = load_rpg_data()
        monstro = data.get("bestiario", {}).get(nome.lower())
        
        if not monstro:
            return await interaction.response.send_message(f"Nenhum registro encontrado para '{nome}'.", ephemeral=True)
            
        embed = discord.Embed(title=f"📖 Bestiário: {monstro['nome']}", color=discord.Color.dark_teal())
        embed.add_field(name="🗡️ Fraqueza", value=monstro['fraqueza'], inline=False)
        embed.add_field(name="📜 Descrição", value=monstro['descricao'], inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    @lore_group.command(name="registrar", description="Grava uma nova lenda ou fato histórico.")
    async def lore_registrar(self, interaction: discord.Interaction, titulo: str, conteudo: str) -> None:
        data = load_rpg_data()
        lore = data.setdefault("lore", {})
        lore[titulo.lower()] = {"titulo": titulo, "conteudo": conteudo}
        save_rpg_data(data)
        
        await interaction.response.send_message(f"📜 O tomo sobre **{titulo}** foi guardado nos arquivos da campanha.")

    @lore_group.command(name="ler", description="Lê um arquivo de lore.")
    async def lore_ler(self, interaction: discord.Interaction, titulo: str) -> None:
        data = load_rpg_data()
        registro = data.get("lore", {}).get(titulo.lower())
        
        if not registro:
            return await interaction.response.send_message(f"Nenhum pergaminho encontrado com o título '{titulo}'.", ephemeral=True)
            
        embed = discord.Embed(title=f"🏛️ Lore: {registro['titulo']}", description=registro['conteudo'], color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RpgLoreCog(bot))
