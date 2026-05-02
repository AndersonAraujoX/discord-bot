import discord
from discord import app_commands
from discord.ext import commands
import re
from collections import Counter
from typing import Optional

from config import BULK_ROLL_LIMIT
from utils.dice_engine import format_result, parse_roll
from utils.storage import load_rpg_data, save_rpg_data
from utils.rpg_core import XP_TABLE, get_hp_bar

class RpgFichaCog(commands.Cog, name="RPG Fichas"):
    """Gestão de Personagens, HP e Dados."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="dados", description="Exibe o guia de rolagem e comandos.")
    async def help_rpg(self, interaction: discord.Interaction) -> None:
        help_text = (
            "🎲 **Guia de RPG & Dados**\n\n"
            "**Rolagem Direta (sem /):**\n"
            "`d20` | `3d6+2` | `4d6d1` | `10#d20` (massa)\n\n"
            "**Fichas & Combate:**\n"
            "`/ficha_set` | `/teste` | `/hp` | `/atacar` | `/status`\n\n"
            "**Mestrado:**\n"
            "`/encontro` | `/loot` | `/iniciativa` | `/dado_fato` | `/grupo`"
        )
        await interaction.response.send_message(help_text)

    @app_commands.command(name="ficha_set", description="Define um atributo ou macro do seu personagem.")
    @app_commands.choices(tipo=[
        app_commands.Choice(name="Atributo (ex: Força)", value="atributo"),
        app_commands.Choice(name="Macro (ex: Ataque Espada)", value="macro")
    ])
    async def ficha_set(self, interaction: discord.Interaction, tipo: app_commands.Choice[str], nome: str, valor: str) -> None:
        data = load_rpg_data()
        uid = str(interaction.user.id)
        if uid not in data["users"]: data["users"][uid] = {"macros": {}, "fichas": {}}
        
        nome = nome.lower()
        if tipo.value == "atributo":
            try:
                data["users"][uid]["fichas"][nome] = int(valor)
                await interaction.response.send_message(f"✅ Atributo **{nome}** ({int(valor):+d}) salvo!")
            except ValueError:
                return await interaction.response.send_message("❌ Valor de atributo deve ser um número.", ephemeral=True)
        else:
            if not parse_roll(valor):
                return await interaction.response.send_message(f"❌ Fórmula `{valor}` inválida.", ephemeral=True)
            data["users"][uid]["macros"][nome] = valor
            await interaction.response.send_message(f"✅ Macro **{nome}** (`{valor}`) salva!")
        
        save_rpg_data(data)

    @app_commands.command(name="ficha", description="Exibe a ficha completa do seu herói.")
    async def ficha(self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None) -> None:
        target = usuario or interaction.user
        data = load_rpg_data()
        uid = str(target.id)
        u_data = data.get("users", {}).get(uid, {})
        
        if not u_data:
            return await interaction.response.send_message(f"❌ **{target.display_name}** ainda não possui dados registrados.", ephemeral=True)

        embed = discord.Embed(title=f"🛡️ Ficha de Herói: {target.display_name}", color=discord.Color.gold())
        embed.set_thumbnail(url=target.display_avatar.url)

        attrs = "\n".join([f"**{k.capitalize()}**: {v:+d}" for k, v in u_data.get("fichas", {}).items()]) or "Nenhum atributo definido."
        embed.add_field(name="📊 Atributos", value=attrs, inline=True)

        hp_info = data.get("hp", {}).get(target.display_name.lower())
        if hp_info:
            embed.add_field(name="❤️ Vitalidade", value=get_hp_bar(hp_info["atual"], hp_info["max"]), inline=True)
        else:
            embed.add_field(name="❤️ Vitalidade", value="Não registrado.", inline=True)

        party = data["party"]
        prox_xp = XP_TABLE.get(party["level"] + 1, "MAX")
        embed.add_field(name="🌟 Nível da Party", value=f"Nível {party['level']} ({party['xp']}/{prox_xp} XP)", inline=False)

        titles = u_data.get("titles", [])
        if titles:
            embed.add_field(name="🏅 Títulos", value="\n".join(f"• {t}" for t in titles), inline=False)

        stats = data.get("statuses", {}).get(target.display_name.lower(), [])
        if stats:
            status_str = []
            for s in stats:
                if isinstance(s, dict):
                    status_str.append(f"• {s['name']} ({s['duration']} turnos)")
                else:
                    status_str.append(f"• {s}")
            embed.add_field(name="⚡ Condições", value="\n".join(status_str), inline=False)

        view = discord.ui.View()
        btn = discord.ui.Button(label="Atualizar", style=discord.ButtonStyle.grey, emoji="🔄")
        async def update_callback(inter):
            await self.ficha(inter, target)
        btn.callback = update_callback
        view.add_item(btn)

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="teste", description="Rola 1d20 somado a um atributo da ficha.")
    async def teste(self, interaction: discord.Interaction, atributo: str) -> None:
        data = load_rpg_data()
        val = data.get("users", {}).get(str(interaction.user.id), {}).get("fichas", {}).get(atributo.lower(), 0)
        formula = f"1d20{val:+d}" if val != 0 else "1d20"
        result = parse_roll(formula)
        await interaction.response.send_message(f"**Teste de {atributo.capitalize()}**:\n{format_result(result)}")

    @app_commands.command(name="macro", description="Rola uma macro salva.")
    async def macro(self, interaction: discord.Interaction, nome: str) -> None:
        data = load_rpg_data()
        formula = data.get("users", {}).get(str(interaction.user.id), {}).get("macros", {}).get(nome.lower())
        if not formula: return await interaction.response.send_message(f"❌ Macro `{nome}` não encontrada.", ephemeral=True)
        result = parse_roll(formula)
        await interaction.response.send_message(f"**Macro: {nome.capitalize()}**:\n{format_result(result)}")

    hp_group = app_commands.Group(name="hp", description="Gerencia pontos de vida.")

    @hp_group.command(name="set", description="Define o HP (atual e máximo) de um alvo.")
    async def hp_set(self, interaction: discord.Interaction, alvo: str, valor: int) -> None:
        data = load_rpg_data()
        data["hp"][alvo.lower()] = {"atual": valor, "max": valor}
        save_rpg_data(data)
        await interaction.response.send_message(f"🏥 HP de **{alvo.capitalize()}** definido para **{valor}**.")

    @hp_group.command(name="dano", description="Aplica dano a um alvo.")
    async def hp_dano(self, interaction: discord.Interaction, alvo: str, valor: int) -> None:
        await self._hp_apply(interaction, alvo, -abs(valor))

    @hp_group.command(name="cura", description="Aplica cura a um alvo.")
    async def hp_cura(self, interaction: discord.Interaction, alvo: str, valor: int) -> None:
        await self._hp_apply(interaction, alvo, abs(valor))

    async def _hp_apply(self, interaction, alvo, valor):
        data = load_rpg_data()
        alvo_l = alvo.lower()
        if alvo_l not in data["hp"]:
            return await interaction.response.send_message(f"❌ Alvo `{alvo}` não encontrado.", ephemeral=True)
        
        hp = data["hp"][alvo_l]
        hp["atual"] = max(0, min(hp["max"], hp["atual"] + valor))
        save_rpg_data(data)
        
        emoji = "💥" if valor < 0 else "✨"
        acao = "Dano" if valor < 0 else "Cura"
        msg = f"{emoji} **{acao}** em **{alvo.capitalize()}**: {abs(valor)}\n{get_hp_bar(hp['atual'], hp['max'])}"
        if hp["atual"] == 0: msg += f"\n\n💀 **ALERTA:** {alvo.capitalize()} caiu!"
        await interaction.response.send_message(msg)

    @hp_group.command(name="listar", description="Lista o HP de todos os registrados.")
    async def hp_listar(self, interaction: discord.Interaction) -> None:
        data = load_rpg_data()
        if not data["hp"]: return await interaction.response.send_message("Nenhum HP registrado.")
        embed = discord.Embed(title="🏥 Vitalidade do Grupo", color=discord.Color.red())
        for char, info in data["hp"].items():
            embed.add_field(name=char.capitalize(), value=get_hp_bar(info["atual"], info["max"]), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="xp", description="Gerencia a experiência da party.")
    @app_commands.describe(valor="Quantidade de XP para adicionar (ou negativo para remover)")
    async def xp(self, interaction: discord.Interaction, valor: Optional[int] = None) -> None:
        data = load_rpg_data()
        party = data["party"]
        
        if valor is None:
            lvl = party["level"]
            xp_atual = party["xp"]
            proximo = XP_TABLE.get(lvl + 1, "MAX")
            embed = discord.Embed(title="🛡️ Progresso da Party", color=discord.Color.blue())
            embed.add_field(name="Nível Atual", value=f"**{lvl}**")
            embed.add_field(name="XP", value=f"{xp_atual} / {proximo}")
            return await interaction.response.send_message(embed=embed)

        party["xp"] += valor
        msg = f"✨ Party ganhou **{valor}** de XP!"
        
        new_lvl = party["level"]
        while True:
            prox_xp = XP_TABLE.get(new_lvl + 1)
            if prox_xp and party["xp"] >= prox_xp:
                new_lvl += 1
            else:
                break
        
        if new_lvl > party["level"]:
            party["level"] = new_lvl
            msg += f"\n\n🎊 **LEVEL UP!** A party agora é nível **{new_lvl}**! 🎊"
        
        save_rpg_data(data)
        await interaction.response.send_message(msg)

    titulo_group = app_commands.Group(name="titulo", description="Gerencia títulos dos personagens.")

    @titulo_group.command(name="add", description="Atribui um título a um jogador.")
    async def titulo_add(self, interaction: discord.Interaction, usuario: discord.Member, titulo: str) -> None:
        data = load_rpg_data()
        uid = str(usuario.id)
        if uid not in data["users"]: data["users"][uid] = {"macros": {}, "fichas": {}, "titles": []}
        if "titles" not in data["users"][uid]: data["users"][uid]["titles"] = []
        
        data["users"][uid]["titles"].append(titulo)
        save_rpg_data(data)
        await interaction.response.send_message(f"🏅 **{usuario.display_name}** agora é conhecido como: *{titulo}*")

    @titulo_group.command(name="listar", description="Lista os títulos de um jogador.")
    async def titulo_listar(self, interaction: discord.Interaction, usuario: discord.Member) -> None:
        data = load_rpg_data()
        titles = data.get("users", {}).get(str(usuario.id), {}).get("titles", [])
        if not titles: return await interaction.response.send_message(f"{usuario.display_name} não possui títulos ainda.")
        
        list_str = "\n".join(f"• {t}" for t in titles)
        await interaction.response.send_message(f"🏅 **Títulos de {usuario.display_name}:**\n{list_str}")

    @app_commands.command(name="ranking_crits", description="Mostra quem são os jogadores mais sortudos (Natural 20).")
    async def ranking_crits(self, interaction: discord.Interaction) -> None:
        data = load_rpg_data()
        crits = data.get("stats", {}).get("crits", {})
        if not crits: return await interaction.response.send_message("Nenhum crítico registrado ainda.")
        
        sorted_crits = sorted(crits.items(), key=lambda x: x[1], reverse=True)
        ranking = "\n".join(f"**{i+1}.** <@{uid}>: {count} 🔥" for i, (uid, count) in enumerate(sorted_crits[:10]))
        
        embed = discord.Embed(title="🏆 Ranking de Críticos (Natural 20)", description=ranking, color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)

    def _record_crit(self, user):
        data = load_rpg_data()
        uid = str(user.id)
        if uid not in data["stats"]["crits"]:
            data["stats"]["crits"][uid] = 0
        data["stats"]["crits"][uid] += 1
        save_rpg_data(data)

    @app_commands.command(name="grupo", description="Mostra status geral do grupo.")
    async def grupo(self, interaction: discord.Interaction) -> None:
        data = load_rpg_data()
        inv = "\n".join(f"• {i}" for i in data["party"]["inventory"]) or "Vazio."
        embed = discord.Embed(title="⛺ Acampamento do Grupo", color=discord.Color.gold())
        embed.add_field(name="🪙 Ouro", value=f"**{data['party']['gold']}**")
        embed.add_field(name="🎒 Inventário", value=inv, inline=False)
        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot: return
        content = message.content.lower().strip().replace(" ", "")
        
        if "#" in content:
            m = re.fullmatch(r"(\d+)#(.+)", content)
            if m:
                await self._mass_roll(message, int(m.group(1)), m.group(2))
                return

        if re.fullmatch(r"(\d*d\d+.*)", content):
            res = parse_roll(content)
            if res:
                await message.channel.send(format_result(res))
                if len(res.rolls) == 1 and res.rolls[0] == 20:
                    self._record_crit(message.author)
                    await message.add_reaction("🔥")

    async def _mass_roll(self, msg, n, notation):
        if n > BULK_ROLL_LIMIT: return await msg.channel.send(f"Limite: {BULK_ROLL_LIMIT}")
        results = [parse_roll(notation) for _ in range(n)]
        if any(r is None for r in results): return await msg.channel.send("Erro na notação.")
        
        lines = [f"#{i+1}: **{r.total}**" for i, r in enumerate(results)]
        counts = Counter(r.total for r in results)
        top = " · ".join(f"{v}x**{k}**" for k, v in sorted(counts.items(), key=lambda x: -x[1])[:5])
        await msg.channel.send(f"📊 **Massa {n}x {notation.upper()}**\n```\n" + "\n".join(lines) + "```\nFrequentes: " + top)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RpgFichaCog(bot))
