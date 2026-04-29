import json
import os
import random
import discord
from discord import app_commands
from discord.ext import commands
from typing import List

from cogs.dados import load_rpg_data, save_rpg_data

TABLES_FILE = "rpg_tables.json"

def load_rpg_tables():
    if os.path.exists(TABLES_FILE):
        with open(TABLES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"encounters": {}, "loot": {}, "facts": []}

class RpgUtilsCog(commands.Cog, name="Util RPG"):
    """Utilitários avançados para mestres e jogadores de RPG."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.tables = load_rpg_tables()

    # ── Autocompletes ─────────────────────────────────────────────────────────

    async def biome_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        biomes = list(self.tables.get("encounters", {}).keys())
        return [
            app_commands.Choice(name=biome.capitalize(), value=biome)
            for biome in biomes if current.lower() in biome.lower()
        ][:25]

    async def level_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        levels = list(self.tables.get("loot", {}).keys())
        return [
            app_commands.Choice(name=f"Nível {lvl}", value=lvl)
            for lvl in levels if current.lower() in lvl.lower()
        ][:25]

    # ── Comandos ──────────────────────────────────────────────────────────────

    @app_commands.command(name="encontro", description="Gera um encontro aleatório em um bioma.")
    @app_commands.autocomplete(bioma=biome_autocomplete)
    async def encontro(self, interaction: discord.Interaction, bioma: str) -> None:
        encounters = self.tables.get("encounters", {}).get(bioma.lower())
        if not encounters:
            return await interaction.response.send_message(
                f"❌ Bioma `{bioma}` não encontrado na tabela.", ephemeral=True
            )
        
        monster = random.choice(encounters)
        embed = discord.Embed(
            title="⚔️ Encontro Aleatório!",
            description=f"O grupo avistou: **{monster}**",
            color=discord.Color.dark_red()
        )
        embed.set_footer(text=f"Bioma: {bioma.capitalize()}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="loot", description="Gera um item de saque aleatório baseado no nível.")
    @app_commands.autocomplete(nivel=level_autocomplete)
    async def loot(self, interaction: discord.Interaction, nivel: str) -> None:
        loots = self.tables.get("loot", {}).get(nivel)
        if not loots:
            return await interaction.response.send_message(
                f"❌ Nível `{nivel}` não encontrado na tabela de loot.", ephemeral=True
            )
        
        item = random.choice(loots)
        embed = discord.Embed(
            title="💎 Saque Encontrado!",
            description=f"Item: **{item}**",
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Nível: {nivel}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dado_fato", description="Sorteia um fato ou curiosidade da mesa.")
    async def dado_fato(self, interaction: discord.Interaction) -> None:
        facts = self.tables.get("facts", [])
        if not facts:
            return await interaction.response.send_message(
                "❌ Nenhuma curiosidade cadastrada na tabela.", ephemeral=True
            )
        
        fato = random.choice(facts)
        await interaction.response.send_message(f"📖 **Dado de Fato:** {fato}")

    @app_commands.command(name="rpg_reload", description="Recarrega as tabelas de encontros e loot (rpg_tables.json).")
    async def rpg_reload(self, interaction: discord.Interaction) -> None:
        try:
            self.tables = load_rpg_tables()
            await interaction.response.send_message("✅ Tabelas de RPG recarregadas com sucesso!")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao recarregar tabelas: `{e}`", ephemeral=True)

    # ── Sistema de Status ─────────────────────────────────────────────────────

    status_group = app_commands.Group(name="status", description="Gerencia buffs e debuffs dos personagens.")

    @status_group.command(name="adicionar", description="Adiciona um status a um personagem.")
    async def status_add(self, interaction: discord.Interaction, alvo: str, status: str) -> None:
        data = load_rpg_data()
        
        # Estrutura: data["statuses"][alvo] = [status1, status2]
        if "statuses" not in data:
            data["statuses"] = {}
        
        alvo = alvo.lower()
        if alvo not in data["statuses"]:
            data["statuses"][alvo] = []
        
        if status not in data["statuses"][alvo]:
            data["statuses"][alvo].append(status)
            save_rpg_data(data)
            await interaction.response.send_message(f"✨ **{status}** adicionado a **{alvo.capitalize()}**!")
        else:
            await interaction.response.send_message(f"ℹ️ **{alvo.capitalize()}** já possui o status **{status}**.", ephemeral=True)

    @status_group.command(name="remover", description="Remove um status de um personagem.")
    async def status_remover(self, interaction: discord.Interaction, alvo: str, status: str) -> None:
        data = load_rpg_data()
        alvo = alvo.lower()
        
        if "statuses" in data and alvo in data["statuses"] and status in data["statuses"][alvo]:
            data["statuses"][alvo].remove(status)
            if not data["statuses"][alvo]:
                del data["statuses"][alvo]
            save_rpg_data(data)
            await interaction.response.send_message(f"✅ **{status}** removido de **{alvo.capitalize()}**.")
        else:
            await interaction.response.send_message(f"❌ **{alvo.capitalize()}** não possui o status **{status}**.", ephemeral=True)

    @status_group.command(name="listar", description="Lista os status ativos.")
    async def status_listar(self, interaction: discord.Interaction, alvo: str = None) -> None:
        data = load_rpg_data()
        statuses = data.get("statuses", {})
        
        if not statuses:
            return await interaction.response.send_message("ℹ️ Não há status ativos em nenhum personagem.")
        
        embed = discord.Embed(title="🎭 Status Ativos", color=discord.Color.blue())
        
        if alvo:
            alvo = alvo.lower()
            if alvo in statuses:
                embed.add_field(name=alvo.capitalize(), value="\n".join(f"• {s}" for s in statuses[alvo]), inline=False)
            else:
                return await interaction.response.send_message(f"ℹ️ **{alvo.capitalize()}** não possui nenhum status ativo.")
        else:
            for char, list_s in statuses.items():
                embed.add_field(name=char.capitalize(), value="\n".join(f"• {s}" for s in list_s), inline=False)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RpgUtilsCog(bot))
