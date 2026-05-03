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

    async def _avancar_turno(self, interaction: discord.Interaction, skip_advance: bool = False):
        cid = interaction.channel.id
        if cid not in self.iniciativas or not self.iniciativas[cid]["players"]:
            return await interaction.response.send_message("Sem combate ativo.", ephemeral=True)
        
        ini = self.iniciativas[cid]
        # Ordena: maior rolagem primeiro. Em caso de empate, mantemos a ordem de entrada.
        ordenada = sorted(ini["players"].items(), key=lambda x: x[1]["roll"], reverse=True)
        
        if not skip_advance:
            # Incrementa o turno
            ini["idx"] += 1
            
            # Se demos a volta completa, incrementa o round
            if ini["idx"] >= len(ordenada):
                ini["idx"] = 0
                ini["round"] += 1
                await self._process_statuses(interaction.guild.id, interaction.channel)

        # Se o index for -1 (início do combate) e pedirmos atualizar, colocamos no 0
        if ini["idx"] == -1:
            ini["idx"] = 0

        key, atual = ordenada[ini["idx"]]
        
        embed = discord.Embed(
            title=f"🛡️ Ordem de Combate — Round {ini['round']}", 
            color=discord.Color.blue()
        )
        lista_str = []
        for i, (k, p) in enumerate(ordenada):
            seta = "➡️ " if i == ini["idx"] else "      "
            vivo = "💀 " if p.get("dead") else ""
            lista_str.append(f"{seta}**{p['roll']}** - {p['name']} {vivo}")
        
        embed.description = "\n".join(lista_str)
        embed.add_field(name="Vez de:", value=atual['mention'])

        # Busca condições ativas para quem vai jogar
        data = load_rpg_data()
        statuses = data.get("statuses", {})
        
        # Procura tanto por ID (para players) quanto por Nome em minúsculo (para NPCs)
        alvo_lookup = str(key) if isinstance(key, int) else key.lower()
        active_conds = statuses.get(alvo_lookup, [])
        if not active_conds and isinstance(key, str):
            # Fallback se a chave no dicionário foi o nome original
            active_conds = statuses.get(atual["name"].lower(), [])

        if active_conds:
            conds_str = "\n".join([f"• {c['name']} ({c['duration']} turnos)" for c in active_conds if isinstance(c, dict)])
            if conds_str:
                embed.add_field(name="⚠️ Efeitos Ativos", value=conds_str, inline=False)
        
        view = TurnoView(self, cid)
        
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)

    iniciativa_group = app_commands.Group(name="iniciativa", description="Gestão de combate.")

    @iniciativa_group.command(name="iniciar", description="Abre o combate no canal.")
    async def ini_start(self, interaction: discord.Interaction) -> None:
        self.iniciativas[interaction.channel.id] = {"idx": -1, "round": 1, "players": {}}
        await interaction.response.send_message("⚔️ **Combate iniciado!** Usem `/iniciativa rolar` para entrar na briga.")

    @iniciativa_group.command(name="rolar", description="Entra no combate (Player).")
    @app_commands.describe(dado="Número de faces do dado a ser rolado (Padrão: 20)")
    async def ini_roll(self, interaction: discord.Interaction, dado: int = 20) -> None:
        cid = interaction.channel.id
        if cid not in self.iniciativas: return await interaction.response.send_message("Sem combate ativo.", ephemeral=True)
        
        # Impede dados inválidos
        if dado < 1:
            dado = 20

        data = load_rpg_data()
        dex = data.get("users", {}).get(str(interaction.user.id), {}).get("fichas", {}).get("destreza", 0)
        
        resultado_dado = random.randint(1, dado)
        roll = resultado_dado + dex
        self.iniciativas[cid]["players"][interaction.user.id] = {"name": interaction.user.display_name, "roll": roll, "mention": interaction.user.mention}
        
        await interaction.response.send_message(
            f"🎲 {interaction.user.mention} entrou na iniciativa!\n"
            f"> Rolou um **d{dado}** e tirou `{resultado_dado}` + Destreza `{dex}` = **{roll}**!"
        )

    async def adicionar_npc_logica(self, interaction: discord.Interaction, nome: str, modificador: int = 0, dado: int = 20) -> None:
        cid = interaction.channel.id
        if cid not in self.iniciativas: 
            return await interaction.response.send_message("Sem combate ativo.", ephemeral=True)
        
        if dado < 1:
            dado = 20
            
        resultado_dado = random.randint(1, dado)
        rolagem = resultado_dado + modificador
        
        key_npc = f"npc_{nome}_{random.randint(100,999)}"
        self.iniciativas[cid]["players"][key_npc] = {
            "name": nome, 
            "roll": rolagem, 
            "mention": f"**{nome}** (NPC)"
        }
        await interaction.response.send_message(
            f"🦇 **{nome}** (NPC) entrou no combate!\n"
            f"> Rolou um **d{dado}** e tirou `{resultado_dado}` + Modificador `{modificador}` = **{rolagem}**!"
        )

    @iniciativa_group.command(name="npc", description="Mestre: Rola a iniciativa e adiciona um NPC.")
    @app_commands.describe(nome="Nome do NPC/Monstro", modificador="Bônus de Destreza (Padrão: 0)", dado="Faces do dado (Padrão: 20)")
    async def ini_npc(self, interaction: discord.Interaction, nome: str, modificador: int = 0, dado: int = 20) -> None:
        await self.adicionar_npc_logica(interaction, nome, modificador, dado)


    @iniciativa_group.command(name="remover", description="Mestre: Remove alguém da ordem (use o nome exato ou id).")
    async def ini_remove(self, interaction: discord.Interaction, nome: str) -> None:
        cid = interaction.channel.id
        if cid not in self.iniciativas: 
            return await interaction.response.send_message("Sem combate ativo.", ephemeral=True)
        
        ini = self.iniciativas[cid]
        # Procura pela chave ou pelo nome do combatente
        alvo_key = None
        for k, p in ini["players"].items():
            if p["name"].lower() == nome.lower() or str(k) == nome:
                alvo_key = k
                break
                
        if alvo_key:
            nome_removido = ini["players"][alvo_key]["name"]
            del ini["players"][alvo_key]
            
            # Ajusta o index se o removido estava antes do atual
            ordenada = sorted(ini["players"].items(), key=lambda x: x[1]["roll"], reverse=True)
            if ini["idx"] >= len(ordenada):
                ini["idx"] = max(-1, len(ordenada) - 1)
                
            await interaction.response.send_message(f"❌ **{nome_removido}** foi removido(a) do combate.")
        else:
            await interaction.response.send_message(f"⚠️ Combatente '{nome}' não encontrado na lista.", ephemeral=True)

    @iniciativa_group.command(name="encerrar", description="Mestre: Encerra o combate atual no canal.")
    async def ini_end(self, interaction: discord.Interaction) -> None:
        cid = interaction.channel.id
        if cid in self.iniciativas:
            del self.iniciativas[cid]
            await interaction.response.send_message("🛑 **Combate encerrado!** O sangue seca nas espadas e o silêncio retorna.")
        else:
            await interaction.response.send_message("Sem combate ativo neste canal.", ephemeral=True)

    @app_commands.command(name="turno", description="Exibe a ordem e avança para o próximo combatente.")
    async def turn_cmd(self, interaction: discord.Interaction) -> None:
        await self._avancar_turno(interaction)

    condicao_group = app_commands.Group(name="condicao", description="Gerencia buffs/debuffs.")

    @condicao_group.command(name="add", description="Adiciona uma condição com duração.")
    async def cond_add(self, interaction: discord.Interaction, alvo: str, nome: str, duracao: int = 3) -> None:
        data = load_rpg_data()
        alvo = alvo.lower()
        if "statuses" not in data: data["statuses"] = {}
        if alvo not in data["statuses"]: data["statuses"][alvo] = []
        
        data["statuses"][alvo] = [s for s in data["statuses"][alvo] if (s if isinstance(s, str) else s["name"]) != nome]
        
        data["statuses"][alvo].append({"name": nome, "duration": duracao})
        save_rpg_data(data)
        await interaction.response.send_message(f"⚡ **{alvo.capitalize()}** agora está sob efeito de **{nome}** ({duracao} turnos)!")

    async def _process_statuses(self, guild_id, channel):
        data = load_rpg_data()
        if "statuses" not in data: return []
        
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
        
        if expired and channel:
            await channel.send("\n".join(expired))
            
        return expired

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RpgCombatCog(bot))
