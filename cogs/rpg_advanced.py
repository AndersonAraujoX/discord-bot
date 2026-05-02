import discord
from discord import app_commands
from discord.ext import commands
import random

from utils.storage import load_rpg_data, save_rpg_data
from utils.ai_helper import generate_ai_response

class RpgAdvancedCog(commands.Cog, name="RPG Avançado"):
    """Sistemas de Mundo Persistente, Lore, Facções e Taverna"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ── Módulo 6: Crafting e Forja ──────────────────────────────────────────

    craft_group = app_commands.Group(name="craft", description="Sistemas de forja e criação de itens.")

    @craft_group.command(name="forjar", description="Forja um item a partir de materiais da mochila.")
    async def craft_forjar(self, interaction: discord.Interaction, material_1: str, material_2: str) -> None:
        await interaction.response.defer()
        data = load_rpg_data()
        inv = data["party"].setdefault("inventory", [])
        
        # Simplificação: assume que os materiais existem para acelerar o RP
        # Em um sistema hardcore, verificaríamos se material_1 e material_2 estão no inv.
        
        prompt = (
            f"Eu estou misturando '{material_1}' com '{material_2}' em uma forja mágica de RPG. "
            f"Crie UM nome épico para a arma ou item resultante e DÊ uma breve descrição de 1 linha de seu poder. "
            f"Exemplo: 'A Lâmina Escarlate: Uma espada que emite chamas vermelhas ao cortar'."
        )
        resultado = await generate_ai_response(prompt)
        
        # Adiciona à mochila
        inv.append({
            "nome": f"Item Forjado ({material_1} + {material_2})",
            "desc": resultado,
            "peso": 2.0
        })
        save_rpg_data(data)
        
        embed = discord.Embed(title="⚒️ Forja Concluída!", description=f"Você combinou **{material_1}** e **{material_2}**.\n\n{resultado}", color=discord.Color.orange())
        await interaction.followup.send(embed=embed)

    # ── Módulo 7: Facções e Reputação ────────────────────────────────────────

    faccao_group = app_commands.Group(name="faccao", description="Gerencia reputação com facções.")

    @faccao_group.command(name="status", description="Mostra a reputação da party com o mundo.")
    async def faccao_status(self, interaction: discord.Interaction) -> None:
        data = load_rpg_data()
        faccoes = data.setdefault("faccoes", {})
        
        if not faccoes:
            return await interaction.response.send_message("A party ainda não é conhecida por nenhuma facção.", ephemeral=True)
            
        embed = discord.Embed(title="🤝 Reputação com Facções", color=discord.Color.blue())
        for nome, rep in faccoes.items():
            status = "Aliado" if rep >= 5 else "Inimigo" if rep <= -5 else "Neutro"
            embed.add_field(name=nome, value=f"{rep}/10 ({status})", inline=False)
            
        await interaction.response.send_message(embed=embed)

    @faccao_group.command(name="alterar", description="Mestre: Altera a reputação com uma facção (-10 a 10).")
    async def faccao_alterar(self, interaction: discord.Interaction, faccao: str, valor: int) -> None:
        data = load_rpg_data()
        faccoes = data.setdefault("faccoes", {})
        faccoes[faccao] = max(-10, min(10, faccoes.get(faccao, 0) + valor))
        save_rpg_data(data)
        
        await interaction.response.send_message(f"A reputação da party com **{faccao}** mudou em {valor:+}! (Atual: {faccoes[faccao]})")

    # ── Módulo 8: Relógio do Fim do Mundo (Doom Clock) ────────────────────────

    doom_group = app_commands.Group(name="doom", description="O Relógio do Juízo Final.")

    def _render_clock(self, ticks: int) -> str:
        clocks = ["🕛", "🕐", "🕑", "🕒", "🕓", "🕔", "🕕", "🕖", "🕗", "🕘", "🕙", "🕚", "🕛"]
        return clocks[min(12, max(0, ticks))]

    @doom_group.command(name="avancar", description="Mestre: Avança (ou recua) o Relógio do Juízo.")
    async def doom_avancar(self, interaction: discord.Interaction, ticks: int, motivo: str) -> None:
        data = load_rpg_data()
        doom = data.setdefault("doom_clock", 0)
        data["doom_clock"] = max(0, min(12, doom + ticks))
        save_rpg_data(data)
        
        embed = discord.Embed(title="⏳ O Relógio Avança...", description=f"*{motivo}*", color=discord.Color.dark_red())
        embed.add_field(name="Status do Fim do Mundo", value=f"{self._render_clock(data['doom_clock'])} ({data['doom_clock']}/12)")
        
        if data["doom_clock"] == 12:
            embed.description += "\n\n🚨 **O TEMPO ACABOU! O EVENTO APOCALÍPTICO COMEÇA!** 🚨"
            
        await interaction.response.send_message(embed=embed)

    @doom_group.command(name="status", description="Visualiza o estado atual do Relógio.")
    async def doom_status(self, interaction: discord.Interaction) -> None:
        data = load_rpg_data()
        doom = data.get("doom_clock", 0)
        
        embed = discord.Embed(title="⏳ Relógio do Juízo Final", description=f"{self._render_clock(doom)} ({doom}/12)", color=discord.Color.dark_grey())
        await interaction.response.send_message(embed=embed)

    # ── Módulo 9: Minigames de Taverna ────────────────────────────────────────

    taverna_group = app_commands.Group(name="taverna", description="Apostas e minigames.")

    @taverna_group.command(name="aposta", description="Jogue os dados na taverna valendo Gold da party!")
    async def taverna_aposta(self, interaction: discord.Interaction, aposta: int) -> None:
        data = load_rpg_data()
        gold = data["party"].setdefault("gold", 0)
        
        if gold < aposta:
            return await interaction.response.send_message(f"💸 A party não tem {aposta}g para apostar! (Gold atual: {gold}g)", ephemeral=True)
            
        # Jogo simples de Maior ganha (Player vs Casa) rolando d100
        player_roll = random.randint(1, 100)
        house_roll = random.randint(1, 100)
        
        msg = f"🎲 Você apostou **{aposta}g**.\nSeu dado: **{player_roll}** | Dado do Taverneiro: **{house_roll}**\n"
        
        if player_roll > house_roll:
            msg += f"\n🎉 **Você VENCEU!** Ganhou +{aposta}g."
            data["party"]["gold"] += aposta
        else:
            msg += f"\n💀 **Você PERDEU!** Perdeu -{aposta}g."
            data["party"]["gold"] -= aposta
            
        save_rpg_data(data)
        msg += f"\nOuro restante na Party: **{data['party']['gold']}g**."
        
        await interaction.response.send_message(msg)

    # ── Módulo 10: Bestiário e Lore ──────────────────────────────────────────

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
    await bot.add_cog(RpgAdvancedCog(bot))
