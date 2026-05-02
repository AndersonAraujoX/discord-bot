import discord
from discord import app_commands
from discord.ext import commands
import random

from utils.storage import load_rpg_data, save_rpg_data
from utils.ui_components import TurnoView

class RpgCombatCog(commands.Cog, name="RPG Combate"):
    """Sistemas de Batalha, Iniciativa e Condições."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.iniciativas: dict[int, dict] = {}

    @app_commands.command(name="atacar", description="Rola ataque e compara com a CA.")
    @app_commands.describe(bonus_ou_atributo="Bônus numérico (+5) ou nome de um atributo da ficha.")
    async def atacar(self, interaction: discord.Interaction, bonus_ou_atributo: str, ca: int, alvo: str = "Alvo") -> None:
        data = load_rpg_data()
        bonus = 0
        attr_name = bonus_ou_atributo.lower()
        char_data = data.get("users", {}).get(str(interaction.user.id), {}).get("fichas", {})
        
        if attr_name in char_data:
            bonus = char_data[attr_name]
            label = f" (usando {attr_name.capitalize()})"
        else:
            try:
                bonus = int(bonus_ou_atributo)
                label = ""
            except ValueError:
                return await interaction.response.send_message(f"❌ `{bonus_ou_atributo}` não é um número nem um atributo válido.", ephemeral=True)

        d20 = random.randint(1, 20)
        total = d20 + bonus
        acertou = total >= ca
        cor = discord.Color.green() if acertou else discord.Color.red()
        res = "✅ ACERTOU!" if acertou else "❌ ERROU!"
        if d20 == 20: 
            res, cor = "🔥 CRÍTICO!", discord.Color.gold()
        if d20 == 1: res, cor = "💀 FALHA CRÍTICA!", discord.Color.dark_gray()
        
        embed = discord.Embed(title=f"⚔️ Ataque contra {alvo}", color=cor)
        embed.add_field(name="Rolagem", value=f"🎲 {d20} + {bonus}{label} = **{total}**")
        embed.add_field(name="Defesa (CA)", value=f"🛡️ {ca}")
        embed.add_field(name="Resultado", value=res, inline=False)
        await interaction.response.send_message(embed=embed)

    async def _avancar_turno(self, interaction: discord.Interaction):
        cid = interaction.channel.id
        if cid not in self.iniciativas or not self.iniciativas[cid]["players"]:
            return await interaction.response.send_message("Sem combate ativo.", ephemeral=True)
        
        ini = self.iniciativas[cid]
        ordenada = sorted(ini["players"].values(), key=lambda x: x["roll"], reverse=True)
        ini["idx"] = (ini["idx"] + 1) % len(ordenada)
        atual = ordenada[ini["idx"]]
        
        embed = discord.Embed(title="🛡️ Ordem de Combate", color=discord.Color.blue())
        lista_str = []
        for i, p in enumerate(ordenada):
            seta = "➡️ " if i == ini["idx"] else "      "
            lista_str.append(f"{seta}**{p['roll']}** - {p['name']}")
        
        embed.description = "\n".join(lista_str)
        embed.add_field(name="Vez de:", value=atual['mention'])
        
        view = TurnoView(self, cid)
        
        if ini["idx"] == 0:
            await self._process_statuses(interaction.guild.id)

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)

    iniciativa_group = app_commands.Group(name="iniciativa", description="Gestão de combate.")

    @iniciativa_group.command(name="iniciar", description="Abre o combate no canal.")
    async def ini_start(self, interaction: discord.Interaction) -> None:
        self.iniciativas[interaction.channel.id] = {"idx": -1, "players": {}}
        await interaction.response.send_message("⚔️ **Combate iniciado!** Usem `/iniciativa rolar` para entrar na briga.")

    @iniciativa_group.command(name="rolar", description="Entra no combate.")
    async def ini_roll(self, interaction: discord.Interaction) -> None:
        cid = interaction.channel.id
        if cid not in self.iniciativas: return await interaction.response.send_message("Sem combate ativo.", ephemeral=True)
        
        data = load_rpg_data()
        dex = data.get("users", {}).get(str(interaction.user.id), {}).get("fichas", {}).get("destreza", 0)
        roll = random.randint(1, 20) + dex
        self.iniciativas[cid]["players"][interaction.user.id] = {"name": interaction.user.display_name, "roll": roll, "mention": interaction.user.mention}
        await interaction.response.send_message(f"🎲 {interaction.user.mention} rolou **{roll}**!")

    @app_commands.command(name="turno", description="Exibe a ordem e avança para o próximo combatente.")
    async def turn_cmd(self, interaction: discord.Interaction) -> None:
        await self._avancar_turno(interaction)

    condicao_group = app_commands.Group(name="condicao", description="Gerencia buffs/debuffs.")

    @condicao_group.command(name="add", description="Adiciona uma condição com duração.")
    async def cond_add(self, interaction: discord.Interaction, alvo: str, nome: str, duracao: int = 3) -> None:
        data = load_rpg_data()
        alvo = alvo.lower()
        if alvo not in data["statuses"]: data["statuses"][alvo] = []
        
        data["statuses"][alvo] = [s for s in data["statuses"][alvo] if (s if isinstance(s, str) else s["name"]) != nome]
        
        data["statuses"][alvo].append({"name": nome, "duration": duracao})
        save_rpg_data(data)
        await interaction.response.send_message(f"⚡ **{alvo.capitalize()}** agora está sob efeito de **{nome}** ({duracao} turnos)!")

    async def _process_statuses(self, guild_id):
        data = load_rpg_data()
        expired = []
        
        for alvo, statuses in data["statuses"].items():
            new_list = []
            for s in statuses:
                if isinstance(s, dict):
                    s["duration"] -= 1
                    if s["duration"] > 0:
                        new_list.append(s)
                    else:
                        expired.append(f"⏰ O efeito **{s['name']}** em **{alvo.capitalize()}** expirou!")
                else:
                    new_list.append(s)
            data["statuses"][alvo] = new_list
        
        save_rpg_data(data)
        return expired

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RpgCombatCog(bot))
