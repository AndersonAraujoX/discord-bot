"""
cogs/dados.py — Comandos de rolagem de dados e RPG (Fichas, Macros, Iniciativa)
=============================================================================
Toda a lógica de rolagem vive em utils/dice_engine.py.
"""

import re
import json
import os
import discord
from collections import Counter
from discord import app_commands
from discord.ext import commands

from config import BULK_ROLL_LIMIT
from utils.dice_engine import format_result, parse_roll

RPG_DATA_FILE = "rpg_data.json"

def load_rpg_data():
    if os.path.exists(RPG_DATA_FILE):
        try:
            with open(RPG_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {"users": {}}

def save_rpg_data(data):
    with open(RPG_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


class DadosCog(commands.Cog, name="Dados"):
    """Sistema avançado de rolagem de dados e RPG."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # self.iniciativas_ativas: channel_id -> {user_id: {"name": str, "roll": int}}
        self.iniciativas_ativas: dict[int, dict[int, dict]] = {}

    # ── Guia de Ajuda ─────────────────────────────────────────────────────────
    @app_commands.command(name="dados", description="Exibe o guia de como rolar dados e usar o RPG.")
    async def help_dados(self, interaction: discord.Interaction) -> None:
        help_text = (
            "🎲 **Guia de Rolagem de Dados e RPG**\n\n"
            "**Básico (Digite direto no chat sem /):**\n"
            "`d20` — Rola um dado de 20 faces.\n"
            "`3d6` — Rola 3 dados de 6 faces e soma tudo.\n"
            "`4d6d1` — Rola 4 dados e **descarta** o menor.\n"
            "`10#d20` — Faz 10 rolagens de d20 de uma vez.\n\n"
            "**Fichas e Macros (Slash Commands):**\n"
            "`/ficha_salvar <atributo> <valor>` — Salva um modificador (ex: destreza +3).\n"
            "`/teste <atributo>` — Rola 1d20 somando o seu modificador.\n"
            "`/macro_salvar <nome> <fórmula>` — Salva uma fórmula de dano ou ataque.\n"
            "`/macro <nome>` — Rola a macro salva.\n\n"
            "**Iniciativa:**\n"
            "`/iniciativa_iniciar` — Abre a contagem no canal.\n"
            "`/iniciativa_rolar` — Rola seu d20 + destreza (se houver) para a iniciativa.\n"
            "`/iniciativa_listar` — Lista a ordem dos turnos.\n"
            "`/iniciativa_limpar` — Encerra a iniciativa no canal.\n"
        )
        await interaction.response.send_message(help_text)

    # ── Macros e Fichas ───────────────────────────────────────────────────────

    @app_commands.command(name="ficha_salvar", description="Salva um atributo do seu personagem (Ex: destreza 3).")
    async def ficha_salvar(self, interaction: discord.Interaction, atributo: str, valor: int) -> None:
        data = load_rpg_data()
        uid = str(interaction.user.id)
        if uid not in data["users"]:
            data["users"][uid] = {"macros": {}, "fichas": {}}
        
        atributo = atributo.lower()
        data["users"][uid]["fichas"][atributo] = valor
        save_rpg_data(data)
        
        await interaction.response.send_message(f"✅ Atributo **{atributo}** ({valor:+d}) salvo para {interaction.user.display_name}!")

    @app_commands.command(name="teste", description="Rola 1d20 + o atributo salvo (Ex: destreza).")
    async def teste(self, interaction: discord.Interaction, atributo: str) -> None:
        data = load_rpg_data()
        uid = str(interaction.user.id)
        atributo = atributo.lower()

        val = data.get("users", {}).get(uid, {}).get("fichas", {}).get(atributo, 0)
        
        # Monta a formula
        formula = f"1d20+{val}" if val >= 0 else f"1d20{val}"
        
        result = parse_roll(formula)
        if result:
            msg = f"**Teste de {atributo.capitalize()}** por {interaction.user.mention}:\n{format_result(result)}"
            await interaction.response.send_message(msg)
        else:
            await interaction.response.send_message("❌ Erro ao calcular rolagem.", ephemeral=True)

    @app_commands.command(name="macro_salvar", description="Salva uma rolagem recorrente (Ex: espada 1d20+5).")
    async def macro_salvar(self, interaction: discord.Interaction, nome: str, formula: str) -> None:
        # Testa a formula primeiro
        if not parse_roll(formula):
            await interaction.response.send_message(f"❌ Fórmula inválida: `{formula}`. Exemplo certo: `1d20+5`", ephemeral=True)
            return

        data = load_rpg_data()
        uid = str(interaction.user.id)
        if uid not in data["users"]:
            data["users"][uid] = {"macros": {}, "fichas": {}}
        
        nome = nome.lower()
        data["users"][uid]["macros"][nome] = formula
        save_rpg_data(data)
        
        await interaction.response.send_message(f"✅ Macro **{nome}** (`{formula}`) salva para {interaction.user.display_name}!")

    @app_commands.command(name="macro", description="Usa uma macro salva (Ex: espada).")
    async def macro(self, interaction: discord.Interaction, nome: str) -> None:
        data = load_rpg_data()
        uid = str(interaction.user.id)
        nome = nome.lower()

        formula = data.get("users", {}).get(uid, {}).get("macros", {}).get(nome)
        if not formula:
            await interaction.response.send_message(f"❌ Nenhuma macro chamada `{nome}` foi encontrada na sua ficha.", ephemeral=True)
            return
        
        result = parse_roll(formula)
        if result:
            msg = f"**Macro: {nome.capitalize()}** por {interaction.user.mention}:\n{format_result(result)}"
            await interaction.response.send_message(msg)
        else:
            await interaction.response.send_message("❌ Erro ao calcular a macro salva.", ephemeral=True)

    # ── Iniciativa ────────────────────────────────────────────────────────────

    @app_commands.command(name="iniciativa_iniciar", description="Abre a mesa de iniciativa neste canal.")
    async def iniciativa_iniciar(self, interaction: discord.Interaction) -> None:
        cid = interaction.channel.id
        self.iniciativas_ativas[cid] = {}
        await interaction.response.send_message(
            f"⚔️ **Iniciativa Iniciada!** ⚔️\nTodos rolando: usem o comando `/iniciativa_rolar`!"
        )

    @app_commands.command(name="iniciativa_rolar", description="Rola 1d20 (+ destreza se tiver salva) e entra na iniciativa.")
    async def iniciativa_rolar(self, interaction: discord.Interaction) -> None:
        cid = interaction.channel.id
        if cid not in self.iniciativas_ativas:
            await interaction.response.send_message("❌ Nenhuma iniciativa aberta. O mestre precisa dar `/iniciativa_iniciar` primeiro.", ephemeral=True)
            return
            
        data = load_rpg_data()
        uid = str(interaction.user.id)
        
        # Puxar destreza (dex) se tiver
        val = data.get("users", {}).get(uid, {}).get("fichas", {}).get("destreza", 0)
        formula = f"1d20+{val}" if val >= 0 else f"1d20{val}"
        
        result = parse_roll(formula)
        if result:
            self.iniciativas_ativas[cid][interaction.user.id] = {
                "name": interaction.user.display_name,
                "roll": result.total
            }
            await interaction.response.send_message(f"🎲 {interaction.user.mention} rolou iniciativa: **{result.total}**")
        else:
            await interaction.response.send_message("❌ Erro ao rolar iniciativa.", ephemeral=True)

    @app_commands.command(name="iniciativa_listar", description="Mostra a ordem dos turnos do maior pro menor.")
    async def iniciativa_listar(self, interaction: discord.Interaction) -> None:
        cid = interaction.channel.id
        if cid not in self.iniciativas_ativas or not self.iniciativas_ativas[cid]:
            await interaction.response.send_message("Ninguém rolou iniciativa ainda neste canal.", ephemeral=True)
            return
            
        ordenada = sorted(self.iniciativas_ativas[cid].values(), key=lambda x: x["roll"], reverse=True)
        
        lines = []
        for i, info in enumerate(ordenada, 1):
            lines.append(f"{i}º — **{info['name']}** ({info['roll']})")
            
        await interaction.response.send_message("**⚔️ Ordem de Iniciativa ⚔️**\n" + "\n".join(lines))

    @app_commands.command(name="iniciativa_limpar", description="Encerra a iniciativa do canal.")
    async def iniciativa_limpar(self, interaction: discord.Interaction) -> None:
        cid = interaction.channel.id
        if cid in self.iniciativas_ativas:
            del self.iniciativas_ativas[cid]
            await interaction.response.send_message("🧹 Iniciativa encerrada. A mesa está limpa.")
        else:
            await interaction.response.send_message("Não há iniciativa aberta aqui.", ephemeral=True)

    # ── Auto-Roll: Detecta se a mensagem é apenas um dado ──────────────────────
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        content = message.content.lower().strip()

        # Rolagem em massa: N#notação
        m = re.fullmatch(r"(\d+)#(.+)", content)
        if m:
            if re.fullmatch(r"(\d*d\d+.*)", m.group(2)):
                await self._bulk_roll(message, int(m.group(1)), m.group(2))
            return

        # Rolagem simples
        if re.fullmatch(r"(\d*d\d+.*)", content):
            result = parse_roll(content)
            if result:
                await message.channel.send(format_result(result))

    # ── Auxiliar para rolagem em massa ────────────────────────────────────────

    async def _bulk_roll(
        self, message: discord.Message, num_rolls: int, notation: str
    ) -> None:
        if num_rolls > BULK_ROLL_LIMIT:
            return await message.channel.send(f"Limite: {BULK_ROLL_LIMIT} rolagens em massa por vez.")

        test = parse_roll(notation)
        if test is None:
            return await message.channel.send("Notação inválida para rolagem em massa.")

        totais = []
        lines  = []
        for i in range(num_rolls):
            r = parse_roll(notation)
            totais.append(r.total)
            lines.append(f"Rolagem {i + 1}: **{r.total}**")

        counter = Counter(totais)
        top_str = " · ".join(
            f"{v}×**{k}**"
            for k, v in sorted(counter.items(), key=lambda x: -x[1])[:5]
        )

        await message.channel.send(
            f"📊 **Massa {num_rolls}× {notation.upper()}**\n"
            f"```\n{chr(10).join(lines)}```"
            f"Mais frequentes: {top_str}"
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DadosCog(bot))
