import discord
from discord import app_commands
from discord.ext import commands
import random
from config import IMAGES

from utils.storage import load_rpg_data, save_rpg_data

class RpgExploreCog(commands.Cog, name="RPG Exploração"):
    """Gerador de Encontros, Loot e Fatos Mágicos."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="encontro", description="Gera um encontro aleatório baseado no ambiente.")
    @app_commands.choices(ambiente=[
        app_commands.Choice(name="Floresta", value="floresta"),
        app_commands.Choice(name="Masmorra", value="masmorra"),
        app_commands.Choice(name="Estrada", value="estrada")
    ])
    async def encontro(self, interaction: discord.Interaction, ambiente: app_commands.Choice[str]) -> None:
        tabelas = {
            "floresta": [
                "🐺 Matilha de lobos famintos.",
                "🧚 Uma fada pede ajuda.",
                "🌲 Árvore desperta irritada.",
                "🍄 Esporos alucinógenos no ar."
            ],
            "masmorra": [
                "💀 Esqueletos erguem-se.",
                "🪤 Armadilha de dardos acionada!",
                "💎 Um baú aparentemente seguro.",
                "🕯️ Cultistas em um ritual negro."
            ],
            "estrada": [
                "💰 Bandidos exigem pedágio.",
                "🐴 Mercador com a carroça quebrada.",
                "🌧️ Tempestade súbita obriga a acampar.",
                "⚔️ Dois cavaleiros duelando."
            ]
        }
        res = random.choice(tabelas[ambiente.value])
        embed = discord.Embed(title=f"🗺️ Encontro na {ambiente.name}", description=res, color=discord.Color.dark_theme())
        if "lobo" in res.lower(): embed.set_image(url=IMAGES.get("encontro_floresta", ""))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="loot", description="Gera tesouros e atualiza o inventário/ouro.")
    async def loot(self, interaction: discord.Interaction, ouro: int, itens: str = None) -> None:
        data = load_rpg_data()
        data["party"]["gold"] += ouro
        
        embed = discord.Embed(title="💰 Loot Encontrado!", color=discord.Color.gold())
        embed.add_field(name="Ouro Adicionado", value=f"+{ouro} (Total: {data['party']['gold']})", inline=False)
        
        if itens:
            lista_itens = [i.strip() for i in itens.split(",")]
            data["party"]["inventory"].extend(lista_itens)
            embed.add_field(name="Itens Guardados", value="\n".join(f"• {i}" for i in lista_itens), inline=False)
            
        save_rpg_data(data)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dado_fato", description="Pergunta algo ao Mestre (Sim/Não com viés).")
    @app_commands.choices(probabilidade=[
        app_commands.Choice(name="Provável", value="provavel"),
        app_commands.Choice(name="Improvável", value="improvavel"),
        app_commands.Choice(name="Neutro", value="neutro")
    ])
    async def dado_fato(self, interaction: discord.Interaction, pergunta: str, probabilidade: app_commands.Choice[str]) -> None:
        probs = {
            "provavel": ["Sim", "Sim", "Sim, e...", "Sim, mas...", "Não, mas..."],
            "improvavel": ["Não", "Não", "Não, e...", "Não, mas...", "Sim, mas..."],
            "neutro": ["Sim", "Não", "Sim, mas...", "Não, mas...", "Sim, e...", "Não, e..."]
        }
        res = random.choice(probs[probabilidade.value])
        
        cor = discord.Color.green() if "Sim" in res else discord.Color.red()
        embed = discord.Embed(title="🔮 Oráculo do Mestre", color=cor)
        embed.add_field(name="Pergunta", value=pergunta, inline=False)
        embed.add_field(name="Probabilidade", value=probabilidade.name, inline=True)
        embed.add_field(name="Resposta", value=f"**{res}**", inline=True)
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RpgExploreCog(bot))
