import discord
from discord import app_commands
from discord.ext import commands
import json

from utils.storage import load_rpg_data, save_rpg_data

class RpgEconomyCog(commands.Cog, name="Economia e Pets"):
    """Lojas, Mercadores e Adoção de Pets"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        try:
            with open("rpg_tables.json", "r", encoding="utf-8") as f:
                self.tables = json.load(f)
        except Exception as e:
            print(f"Erro ao carregar rpg_tables.json em Economy: {e}")
            self.tables = {}

    loja_group = app_commands.Group(name="loja", description="Sistema de mercadores.")

    @loja_group.command(name="visitar", description="Visita um mercador para ver seus itens.")
    @app_commands.choices(tipo=[
        app_commands.Choice(name="Ferreiro", value="Ferreiro"),
        app_commands.Choice(name="Alquimista", value="Alquimista"),
        app_commands.Choice(name="Místico", value="Místico")
    ])
    async def loja_visitar(self, interaction: discord.Interaction, tipo: app_commands.Choice[str]) -> None:
        shop_items = self.tables.get("shop_items", {}).get(tipo.value, [])
        if not shop_items:
            return await interaction.response.send_message(f"O {tipo.value} fechou as portas hoje.", ephemeral=True)
            
        embed = discord.Embed(title=f"🏪 Loja do {tipo.value}", description="Bem-vindo aventureiro! O que deseja comprar?", color=discord.Color.gold())
        
        for i, item in enumerate(shop_items):
            embed.add_field(name=f"{i+1}. {item['nome']} (💰 {item['preco']}g)", value=f"{item['desc']}\n*Peso: {item['peso']}kg*", inline=False)
            
        await interaction.response.send_message(embed=embed)

    @loja_group.command(name="comprar", description="Compra um item da loja especificada.")
    @app_commands.choices(tipo=[
        app_commands.Choice(name="Ferreiro", value="Ferreiro"),
        app_commands.Choice(name="Alquimista", value="Alquimista"),
        app_commands.Choice(name="Místico", value="Místico")
    ])
    async def loja_comprar(self, interaction: discord.Interaction, tipo: app_commands.Choice[str], numero_item: int) -> None:
        shop_items = self.tables.get("shop_items", {}).get(tipo.value, [])
        if not (1 <= numero_item <= len(shop_items)):
            return await interaction.response.send_message("❌ Item não encontrado.", ephemeral=True)
            
        item_escolhido = shop_items[numero_item - 1]
        data = load_rpg_data()
        party_gold = data["party"].setdefault("gold", 0)
        
        if party_gold < item_escolhido["preco"]:
            return await interaction.response.send_message(f"💸 Dinheiro insuficiente! A party tem {party_gold}g, mas custa {item_escolhido['preco']}g.", ephemeral=True)
            
        # Deduz gold
        data["party"]["gold"] -= item_escolhido["preco"]
        
        # Adiciona à mochila
        inv = data["party"].setdefault("inventory", [])
        inv.append({
            "nome": item_escolhido["nome"],
            "desc": item_escolhido["desc"],
            "peso": item_escolhido["peso"]
        })
        save_rpg_data(data)
        
        await interaction.response.send_message(f"🛒 Vocês compraram **{item_escolhido['nome']}** por {item_escolhido['preco']}g!\nO item foi guardado na mochila. Restam {data['party']['gold']}g.")

    # ── Sistema de Pets ───────────────────────────────────────────────────
    
    pet_group = app_commands.Group(name="pet", description="Adoção e gestão de companheiros.")

    @pet_group.command(name="adotar", description="Adota um novo companheiro para a party.")
    async def pet_adotar(self, interaction: discord.Interaction, dono: str, nome_pet: str, especie: str) -> None:
        data = load_rpg_data()
        uid = dono.lower()
        
        pets = data.setdefault("pets", {})
        user_pets = pets.setdefault(uid, [])
        
        user_pets.append({
            "nome": nome_pet,
            "especie": especie,
            "hp": {"atual": 10, "max": 10}
        })
        save_rpg_data(data)
        
        embed = discord.Embed(title="🐾 Novo Companheiro!", description=f"O aventureiro **{uid.capitalize()}** adotou um(a) **{especie}** chamado **{nome_pet}**!", color=discord.Color.blurple())
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RpgEconomyCog(bot))
