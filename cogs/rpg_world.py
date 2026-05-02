import discord
from discord import app_commands
from discord.ext import commands
import random

from utils.storage import load_rpg_data, save_rpg_data
from utils.ai_helper import generate_ai_response

class RpgWorldCog(commands.Cog, name="Mundo RPG"):
    """Sistemas de Descanso e Geração Dinâmica do Mundo"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ── Sistema de Descanso ───────────────────────────────────────────────

    descanso_group = app_commands.Group(name="descanso", description="Sistemas de recuperação para a party.")

    @descanso_group.command(name="curto", description="Recupera uma parte do HP e mana da party.")
    async def descanso_curto(self, interaction: discord.Interaction) -> None:
        data = load_rpg_data()
        msg = []
        
        # Recupera 25% do HP máximo de cada jogador registrado
        hp_data = data.setdefault("hp", {})
        for name, info in hp_data.items():
            cura = max(1, info["max"] // 4)
            info["atual"] = min(info["max"], info["atual"] + cura)
            msg.append(f"**{name.capitalize()}**: recuperou +{cura} HP.")
            
        # Recupera 25% da Mana de cada jogador
        users_data = data.setdefault("users", {})
        for uid, u_data in users_data.items():
            if "mana" in u_data:
                mana = u_data["mana"]
                m_cura = max(1, mana["max"] // 4)
                mana["atual"] = min(mana["max"], mana["atual"] + m_cura)
        
        save_rpg_data(data)
        
        embed = discord.Embed(title="🏕️ Descanso Curto", description="\n".join(msg) or "Ninguém registrou HP ainda.", color=discord.Color.orange())
        await interaction.response.send_message(embed=embed)

    @descanso_group.command(name="longo", description="Recupera todo HP, Mana e reseta status.")
    async def descanso_longo(self, interaction: discord.Interaction) -> None:
        data = load_rpg_data()
        
        # Recupera 100% HP
        for name, info in data.get("hp", {}).items():
            info["atual"] = info["max"]
            
        # Recupera 100% Mana
        for uid, u_data in data.get("users", {}).items():
            if "mana" in u_data:
                u_data["mana"]["atual"] = u_data["mana"]["max"]
                
        # Limpa Status
        data["statuses"] = {}
        
        save_rpg_data(data)
        
        embed = discord.Embed(title="⛺ Descanso Longo", description="A party dormiu bem. Todo o **HP e Mana** foram restaurados. As condições foram removidas.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    # ── Gerador de Masmorras ───────────────────────────────────────────────

    masmorra_group = app_commands.Group(name="masmorra", description="Gera instâncias dinâmicas do mundo.")

    @masmorra_group.command(name="gerar", description="Gera uma masmorra aleatória com a I.A.")
    @app_commands.describe(tema="O tipo de masmorra (ex: Caverna de Gelo, Ruínas Antigas)")
    async def masmorra_gerar(self, interaction: discord.Interaction, dificuldade: str = "Normal", tema: str = "Catacumbas") -> None:
        await interaction.response.defer()
        
        prompt = (
            f"Gere uma descrição sucinta para uma masmorra de D&D de dificuldade {dificuldade} com o tema '{tema}'. "
            f"Retorne 3 salas. Para cada sala, dê um Título e uma breve descrição do que há nela (monstros, loot ou armadilha). "
            f"A última sala deve ter o Chefe."
        )
        
        resposta = await generate_ai_response(prompt)
        
        embed = discord.Embed(title=f"🏰 {tema} ({dificuldade})", description=resposta, color=discord.Color.dark_red())
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RpgWorldCog(bot))
