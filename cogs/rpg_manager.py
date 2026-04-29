import re
import json
import os
import random
import discord
from collections import Counter
from typing import List, Optional
from discord import app_commands
from discord.ext import commands

from config import BULK_ROLL_LIMIT
from utils.dice_engine import format_result, parse_roll
from utils.storage import load_rpg_data, save_rpg_data

TABLES_FILE = "rpg_tables.json"

def load_rpg_tables():
    if os.path.exists(TABLES_FILE):
        try:
            with open(TABLES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"encounters": {}, "loot": {}, "facts": []}

class RpgManagerCog(commands.Cog, name="RPG"):
    """Sistema unificado de mecânicas de RPG (Dados, Fichas, Combate e Exploração)."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.tables = load_rpg_tables()
        # self.iniciativas: channel_id -> {"current_index": int, "participants": list[dict]}
        self.iniciativas: dict[int, dict] = {}

    # ── Utilitários de Interface ──────────────────────────────────────────────

    def _get_hp_bar(self, atual, maximo):
        size = 10
        filled = max(0, min(size, round((atual / maximo) * size)))
        bar = "🟩" * filled + "⬜" * (size - filled)
        percent = (atual / maximo) * 100
        return f"{bar} ({atual}/{maximo}) — {percent:.0f}%"

    # ── Autocompletes ─────────────────────────────────────────────────────────

    async def biome_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        biomes = list(self.tables.get("encounters", {}).keys())
        return [app_commands.Choice(name=b.capitalize(), value=b) for b in biomes if current.lower() in b.lower()][:25]

    async def level_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        levels = list(self.tables.get("loot", {}).keys())
        return [app_commands.Choice(name=f"Nível {l}", value=l) for l in levels if current.lower() in l.lower()][:25]

    # ── Comandos de Dados ─────────────────────────────────────────────────────

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

    # ── Gerenciamento de Ficha ────────────────────────────────────────────────

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

    # ── Sistema de HP & Vida ──────────────────────────────────────────────────

    hp_group = app_commands.Group(name="hp", description="Gerencia pontos de vida.")

    @hp_group.command(name="set", description="Define o HP (atual e máximo) de um alvo.")
    async def hp_set(self, interaction: discord.Interaction, alvo: str, valor: int) -> None:
        data = load_rpg_data()
        data["hp"][alvo.lower()] = {"atual": valor, "max": valor}
        save_rpg_data(data)
        await interaction.response.send_message(f"🏥 HP de **{alvo.capitalize()}** definido para **{valor}**.")

    @hp_group.command(name="mudar", description="Adiciona ou retira HP (use valores negativos para dano).")
    async def hp_mudar(self, interaction: discord.Interaction, alvo: str, valor: int) -> None:
        data = load_rpg_data()
        alvo_l = alvo.lower()
        if alvo_l not in data["hp"]: return await interaction.response.send_message("❌ Alvo sem HP definido.", ephemeral=True)
        
        hp = data["hp"][alvo_l]
        hp["atual"] = max(0, min(hp["max"], hp["atual"] + valor))
        save_rpg_data(data)
        
        msg = f"{'✨ Cura' if valor > 0 else '💥 Dano'} em **{alvo.capitalize()}**: {abs(valor)}\n{self._get_hp_bar(hp['atual'], hp['max'])}"
        if hp["atual"] == 0: msg += f"\n\n💀 **ALERTA:** {alvo.capitalize()} caiu!"
        await interaction.response.send_message(msg)

    @hp_group.command(name="listar", description="Lista o HP de todos os registrados.")
    async def hp_listar(self, interaction: discord.Interaction) -> None:
        data = load_rpg_data()
        if not data["hp"]: return await interaction.response.send_message("Nenhum HP registrado.")
        embed = discord.Embed(title="🏥 Vitalidade do Grupo", color=discord.Color.red())
        for char, info in data["hp"].items():
            embed.add_field(name=char.capitalize(), value=self._get_hp_bar(info["atual"], info["max"]), inline=False)
        await interaction.response.send_message(embed=embed)

    # ── Combate: Ataque & Iniciativa ──────────────────────────────────────────

    @app_commands.command(name="atacar", description="Rola ataque e compara com a CA.")
    async def atacar(self, interaction: discord.Interaction, bonus: int, ca: int, alvo: str = "Alvo") -> None:
        d20 = random.randint(1, 20)
        total = d20 + bonus
        acertou = total >= ca
        cor = discord.Color.green() if acertou else discord.Color.red()
        res = "✅ ACERTOU!" if acertou else "❌ ERROU!"
        if d20 == 20: res, cor = "🔥 CRÍTICO!", discord.Color.gold()
        if d20 == 1: res, cor = "💀 FALHA CRÍTICA!", discord.Color.dark_gray()
        
        embed = discord.Embed(title=f"⚔️ Ataque contra {alvo}", color=cor)
        embed.add_field(name="Rolagem", value=f"🎲 {d20} + {bonus} = **{total}**")
        embed.add_field(name="Defesa (CA)", value=f"🛡️ {ca}")
        embed.add_field(name="Resultado", value=res, inline=False)
        await interaction.response.send_message(embed=embed)

    iniciativa_group = app_commands.Group(name="iniciativa", description="Gestão de combate.")

    @iniciativa_group.command(name="iniciar", description="Abre o combate no canal.")
    async def ini_start(self, interaction: discord.Interaction) -> None:
        self.iniciativas[interaction.channel.id] = {"idx": -1, "players": {}}
        await interaction.response.send_message("⚔️ **Combate iniciado!** Usem `/iniciativa rolar`.")

    @iniciativa_group.command(name="rolar", description="Entra no combate.")
    async def ini_roll(self, interaction: discord.Interaction) -> None:
        cid = interaction.channel.id
        if cid not in self.iniciativas: return await interaction.response.send_message("Sem combate ativo.", ephemeral=True)
        
        data = load_rpg_data()
        dex = data.get("users", {}).get(str(interaction.user.id), {}).get("fichas", {}).get("destreza", 0)
        roll = random.randint(1, 20) + dex
        self.iniciativas[cid]["players"][interaction.user.id] = {"name": interaction.user.display_name, "roll": roll, "mention": interaction.user.mention}
        await interaction.response.send_message(f"🎲 {interaction.user.mention} rolou **{roll}**!")

    @app_commands.command(name="turno", description="Avança para o próximo combatente.")
    async def turn_next(self, interaction: discord.Interaction) -> None:
        cid = interaction.channel.id
        if cid not in self.iniciativas or not self.iniciativas[cid]["players"]: return await interaction.response.send_message("Sem combate ativo.")
        
        ini = self.iniciativas[cid]
        ordenada = sorted(ini["players"].values(), key=lambda x: x["roll"], reverse=True)
        ini["idx"] = (ini["idx"] + 1) % len(ordenada)
        atual = ordenada[ini["idx"]]
        await interaction.response.send_message(f"🛡️ **Vez de:** {atual['mention']}!")

    # ── Exploração & Mestrado ─────────────────────────────────────────────────

    @app_commands.command(name="encontro", description="Gera um monstro aleatório por bioma.")
    @app_commands.autocomplete(bioma=biome_autocomplete)
    async def encontro(self, interaction: discord.Interaction, bioma: str) -> None:
        lista = self.tables.get("encounters", {}).get(bioma.lower())
        if not lista: return await interaction.response.send_message("Bioma não encontrado.", ephemeral=True)
        await interaction.response.send_message(f"⚔️ **Encontro:** {random.choice(lista)} ({bioma.capitalize()})")

    @app_commands.command(name="loot", description="Gera item por nível.")
    @app_commands.autocomplete(nivel=level_autocomplete)
    async def loot(self, interaction: discord.Interaction, nivel: str) -> None:
        lista = self.tables.get("loot", {}).get(nivel)
        if not lista: return await interaction.response.send_message("Nível não encontrado.", ephemeral=True)
        await interaction.response.send_message(f"💎 **Loot:** {random.choice(lista)} (Nível {nivel})")

    @app_commands.command(name="dado_fato", description="Sorteia curiosidade da mesa.")
    async def fato(self, interaction: discord.Interaction) -> None:
        fatos = self.tables.get("facts", [])
        if not fatos: return await interaction.response.send_message("Sem fatos cadastrados.")
        await interaction.response.send_message(f"📖 **Fato:** {random.choice(fatos)}")

    # ── Grupo & Economia ──────────────────────────────────────────────────────

    @app_commands.command(name="gold", description="Soma/subtrai ouro da party.")
    async def gold(self, interaction: discord.Interaction, valor: int) -> None:
        data = load_rpg_data()
        data["party"]["gold"] += valor
        save_rpg_data(data)
        await interaction.response.send_message(f"🪙 Ouro da party: **{data['party']['gold']}** (Alt: {valor:+d})")

    @app_commands.command(name="loot_add", description="Adiciona item ao inventário coletivo.")
    async def loot_add(self, interaction: discord.Interaction, item: str) -> None:
        data = load_rpg_data()
        data["party"]["inventory"].append(item)
        save_rpg_data(data)
        await interaction.response.send_message(f"🎒 **{item}** guardado na carroça!")

    @app_commands.command(name="grupo", description="Mostra status geral do grupo.")
    async def grupo(self, interaction: discord.Interaction) -> None:
        data = load_rpg_data()
        inv = "\n".join(f"• {i}" for i in data["party"]["inventory"]) or "Vazio."
        embed = discord.Embed(title="⛺ Acampamento do Grupo", color=discord.Color.gold())
        embed.add_field(name="🪙 Ouro", value=f"**{data['party']['gold']}**")
        embed.add_field(name="🎒 Inventário", value=inv, inline=False)
        await interaction.response.send_message(embed=embed)

    # ── Mural de Missões ──────────────────────────────────────────────────────

    @app_commands.command(name="mural_setup", description="Cria o canal #mural-de-missoes e configura permissões.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def mural_setup(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(send_messages=False),
            guild.me: discord.PermissionOverwrite(send_messages=True),
        }
        
        # Procura se já existe
        channel = discord.utils.get(guild.text_channels, name="mural-de-missoes")
        if not channel:
            channel = await guild.create_text_channel("mural-de-missoes", overwrites=overwrites)
            await interaction.response.send_message(f"✅ Canal {channel.mention} criado e bloqueado para jogadores!")
        else:
            await channel.edit(overwrites=overwrites)
            await interaction.response.send_message(f"✅ Permissões do canal {channel.mention} atualizadas!")

    @app_commands.command(name="missao_postar", description="Posta um gancho de missão no mural com votação.")
    @app_commands.describe(titulo="Título da missão", descricao="O que está acontecendo?", recompensa="O que ganharão?")
    async def missao_postar(self, interaction: discord.Interaction, titulo: str, descricao: str, recompensa: str) -> None:
        channel = discord.utils.get(interaction.guild.text_channels, name="mural-de-missoes")
        if not channel:
            return await interaction.response.send_message("❌ Canal `#mural-de-missoes` não encontrado. Use `/mural_setup` primeiro.", ephemeral=True)

        embed = discord.Embed(title=f"📜 MISSÃO: {titulo}", description=descricao, color=discord.Color.dark_gold())
        embed.add_field(name="💰 Recompensa", value=recompensa)
        embed.set_footer(text="Jogadores, votem com 👍 ou 👎 para decidir o rumo!")
        
        msg = await channel.send(embed=embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")
        
        await interaction.response.send_message(f"✅ Missão postada em {channel.mention}!")

    # ── Listener para dados diretos (ex: d20) ──────────────────────────────────


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot: return
        content = message.content.lower().strip().replace(" ", "")
        
        # Massa: N#XdY
        if "#" in content:
            m = re.fullmatch(r"(\d+)#(.+)", content)
            if m:
                await self._mass_roll(message, int(m.group(1)), m.group(2))
                return

        # Simples: XdY
        if re.fullmatch(r"(\d*d\d+.*)", content):
            res = parse_roll(content)
            if res: await message.channel.send(format_result(res))

    async def _mass_roll(self, msg, n, notation):
        if n > BULK_ROLL_LIMIT: return await msg.channel.send(f"Limite: {BULK_ROLL_LIMIT}")
        results = [parse_roll(notation) for _ in range(n)]
        if any(r is None for r in results): return await msg.channel.send("Erro na notação.")
        
        lines = [f"#{i+1}: **{r.total}**" for i, r in enumerate(results)]
        counts = Counter(r.total for r in results)
        top = " · ".join(f"{v}x**{k}**" for k, v in sorted(counts.items(), key=lambda x: -x[1])[:5])
        await msg.channel.send(f"📊 **Massa {n}x {notation.upper()}**\n```\n" + "\n".join(lines) + "```\nFrequentes: " + top)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RpgManagerCog(bot))
