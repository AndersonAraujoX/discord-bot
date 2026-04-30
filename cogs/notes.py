import discord
from discord import app_commands
from discord.ext import commands
from utils.storage import load_rpg_data, save_rpg_data
from datetime import datetime

class NotesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    group = app_commands.Group(name="notas", description="Gerenciador de notações de RPG personalizadas.")

    @group.command(name="adicionar", description="Adiciona uma nota vinculada a este canal e à sua conta.")
    async def add_note(self, interaction: discord.Interaction, texto: str):
        data = load_rpg_data()
        channel_id = str(interaction.channel_id)
        user_id = str(interaction.user.id)

        if channel_id not in data["channel_notes"]:
            data["channel_notes"][channel_id] = {}
        
        if user_id not in data["channel_notes"][channel_id]:
            data["channel_notes"][channel_id][user_id] = []

        new_note = {
            "text": texto,
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M")
        }

        data["channel_notes"][channel_id][user_id].append(new_note)
        save_rpg_data(data)

        embed = discord.Embed(
            title="📝 Nota Registrada",
            description=texto,
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Canal: {interaction.channel.name} | {new_note['timestamp']}")
        await interaction.response.send_message(embed=embed)

    @group.command(name="listar", description="Lista todas as suas notas registradas neste canal.")
    async def list_notes(self, interaction: discord.Interaction):
        data = load_rpg_data()
        channel_id = str(interaction.channel_id)
        user_id = str(interaction.user.id)

        notes = data["channel_notes"].get(channel_id, {}).get(user_id, [])

        if not notes:
            return await interaction.response.send_message("🔍 Você não tem notas registradas neste canal.", ephemeral=True)

        embed = discord.Embed(
            title=f"📜 Suas Notas em #{interaction.channel.name}",
            color=discord.Color.blue()
        )

        for i, note in enumerate(notes, 1):
            embed.add_field(
                name=f"Nota #{i} - {note['timestamp']}",
                value=note['text'],
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @group.command(name="limpar", description="Apaga todas as suas notas deste canal.")
    async def clear_notes(self, interaction: discord.Interaction):
        data = load_rpg_data()
        channel_id = str(interaction.channel_id)
        user_id = str(interaction.user.id)

        if channel_id in data["channel_notes"] and user_id in data["channel_notes"][channel_id]:
            del data["channel_notes"][channel_id][user_id]
            save_rpg_data(data)
            await interaction.response.send_message("🧹 Todas as suas notas neste canal foram apagadas.")
        else:
            await interaction.response.send_message("🔍 Nenhuma nota encontrada para apagar.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(NotesCog(bot))
