import discord

# Constantes de Loop para Musica (copiado do musica.py)
LOOP_SONG = "song"
LOOP_QUEUE = "queue"
LOOP_OFF = None

class TurnoView(discord.ui.View):
    """View para controle de turnos de RPG."""
    def __init__(self, cog, channel_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.channel_id = channel_id

    @discord.ui.button(label="Próximo Turno", style=discord.ButtonStyle.green, emoji="⏭️")
    async def next_turn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._avancar_turno(interaction)


class MusicControlView(discord.ui.View):
    """View de controle para o Player de Música e Soundboard."""
    def __init__(self, cog, guild_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id

    @discord.ui.button(label="⏯️", style=discord.ButtonStyle.grey)
    async def play_pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.cog._state(self.guild_id)
        if state.voice_client:
            if state.voice_client.is_playing():
                state.voice_client.pause()
                await interaction.response.send_message("Pausado.", ephemeral=True)
            elif state.voice_client.is_paused():
                state.voice_client.resume()
                await interaction.response.send_message("Retomado.", ephemeral=True)

    @discord.ui.button(label="⏭️ Próxima", style=discord.ButtonStyle.grey)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.cog._state(self.guild_id)
        if state.voice_client and state.voice_client.is_playing():
            state.voice_client.stop()
            await interaction.response.send_message("Pulada.", ephemeral=True)

    @discord.ui.button(label="🔁 Loop", style=discord.ButtonStyle.grey)
    async def toggle_loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.cog._state(self.guild_id)
        if state.loop == LOOP_OFF: state.loop = LOOP_SONG
        elif state.loop == LOOP_SONG: state.loop = LOOP_QUEUE
        else: state.loop = LOOP_OFF
        await interaction.response.send_message(f"Loop: {state.loop or 'OFF'}", ephemeral=True)

    @discord.ui.button(label="⏹️ Parar", style=discord.ButtonStyle.red)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.cog._state(self.guild_id)
        state.clear()
        if state.voice_client:
            await state.voice_client.disconnect()
        await interaction.response.send_message("Música encerrada.", ephemeral=True)

    # Row 2: Soundboard
    @discord.ui.button(label="⚔️", style=discord.ButtonStyle.secondary)
    async def fx_sword(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._play_fx(interaction, "https://www.youtube.com/watch?v=Pr3sBks7m9w")

    @discord.ui.button(label="🐉", style=discord.ButtonStyle.secondary)
    async def fx_dragon(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._play_fx(interaction, "https://www.youtube.com/watch?v=4z9jd7z9f7M")

    @discord.ui.button(label="🍻", style=discord.ButtonStyle.secondary)
    async def fx_cheers(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._play_fx(interaction, "https://www.youtube.com/watch?v=O1f8S077Cto")
