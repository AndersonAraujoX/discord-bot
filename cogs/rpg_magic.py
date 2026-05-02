import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from utils.storage import load_rpg_data, save_rpg_data

class RpgMagicCog(commands.Cog, name="Magia"):
    """Sistema de Grimório e Lançamento de Magias"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    magia_group = app_commands.Group(name="magia", description="Gerencia seu grimório e lança feitiços.")

    @magia_group.command(name="aprender", description="Adiciona uma magia ao seu grimório.")
    async def magia_aprender(self, interaction: discord.Interaction, nome: str, descricao: str, custo_mana: int = 1) -> None:
        data = load_rpg_data()
        uid = str(interaction.user.id)
        
        if uid not in data.setdefault("users", {}):
            data["users"][uid] = {}
        
        u_data = data["users"][uid]
        if "grimorio" not in u_data:
            u_data["grimorio"] = []
            
        # Impede duplicatas pelo nome
        u_data["grimorio"] = [m for m in u_data["grimorio"] if m["nome"].lower() != nome.lower()]
        
        u_data["grimorio"].append({"nome": nome, "desc": descricao, "mana": custo_mana})
        save_rpg_data(data)
        
        await interaction.response.send_message(f"📖 **{nome}** (Custo: {custo_mana} MP) foi adicionada ao seu grimório!")

    @magia_group.command(name="castar", description="Gasta mana e lança uma magia.")
    async def magia_castar(self, interaction: discord.Interaction, nome: str) -> None:
        data = load_rpg_data()
        uid = str(interaction.user.id)
        u_data = data.get("users", {}).get(uid, {})
        
        grimorio = u_data.get("grimorio", [])
        magia = next((m for m in grimorio if m["nome"].lower() == nome.lower()), None)
        
        if not magia:
            return await interaction.response.send_message(f"❌ Você não conhece a magia **{nome}**.", ephemeral=True)
            
        mana_info = u_data.get("mana", {"atual": 10, "max": 10}) # Padrão 10/10 se não definido
        
        if mana_info["atual"] < magia["mana"]:
            return await interaction.response.send_message(f"⚠️ Mana insuficiente! (Atual: {mana_info['atual']}, Necessário: {magia['mana']})", ephemeral=True)
            
        # Deduz a mana
        mana_info["atual"] -= magia["mana"]
        u_data["mana"] = mana_info
        
        if "users" not in data: data["users"] = {}
        data["users"][uid] = u_data
        save_rpg_data(data)
        
        embed = discord.Embed(title=f"✨ Conjurou: {magia['nome']}", description=magia['desc'], color=discord.Color.purple())
        embed.set_footer(text=f"Custo: {magia['mana']} MP | Mana restante: {mana_info['atual']}/{mana_info['max']}")
        
        await interaction.response.send_message(embed=embed)

    @magia_group.command(name="grimorio", description="Exibe todas as suas magias aprendidas.")
    async def magia_grimorio(self, interaction: discord.Interaction) -> None:
        data = load_rpg_data()
        uid = str(interaction.user.id)
        u_data = data.get("users", {}).get(uid, {})
        
        grimorio = u_data.get("grimorio", [])
        mana_info = u_data.get("mana", {"atual": 10, "max": 10})
        
        if not grimorio:
            return await interaction.response.send_message("Seu grimório está vazio. Use `/magia aprender` para adicionar feitiços.", ephemeral=True)
            
        embed = discord.Embed(title=f"📖 Grimório de {interaction.user.display_name}", color=discord.Color.blue())
        embed.description = f"**Mana:** {mana_info['atual']}/{mana_info['max']} MP\n\n"
        
        for m in sorted(grimorio, key=lambda x: x["mana"]):
            embed.description += f"**{m['nome']}** (*{m['mana']} MP*)\n{m['desc']}\n\n"
            
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RpgMagicCog(bot))
