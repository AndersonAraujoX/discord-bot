"""
cogs/musica.py — Comandos de música (yt-dlp + FFmpeg)
======================================================
Estado de cada servidor encapsulado na classe GuildMusicState.
"""

import asyncio
from typing import Optional, List

import discord
from discord import app_commands
from discord.ext import commands

from config import PLAYLISTS, RADIO_URL
from utils.music_helper import search_songs, get_yt_suggestions, extract_song_info
from utils.ui_components import LOOP_SONG, LOOP_QUEUE, LOOP_OFF, MusicSearchView
from utils.music_core import MusicManager

AMBIENT_SOUNDS = {
    "Chuva": "https://www.youtube.com/watch?v=mPZkdNFkNps",
    "Taverna": "https://www.youtube.com/watch?v=hBpcovn0kb4",
    "Floresta": "https://www.youtube.com/watch?v=xNN7iTA57jM",
    "Combate": "https://www.youtube.com/watch?v=17X2fB-M880",
    "Suspense": "https://www.youtube.com/watch?v=S_S7p6tFmXU"
}


class MusicaCog(commands.Cog, name="Música"):
    """Comandos para tocar músicas em canais de voz."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.music_manager = MusicManager(bot)

    async def music_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Callback para sugestões do YouTube em tempo real."""
        if not current or len(current) < 3: return [] # Só busca após 3 caracteres
        suggestions = await get_yt_suggestions(current)
        return [
            app_commands.Choice(name=s, value=s)
            for s in suggestions[:25]
        ]

    # ── Comandos ──────────────────────────────────────────────────────────────

    @app_commands.command(name="join", description="Entra no canal de voz atual.")
    async def join(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        vc = await self.music_manager.connect_voice(interaction)
        if vc:
            await interaction.followup.send(f"Entrei em: **{interaction.user.voice.channel.name}** 🎙️")

    @app_commands.command(name="leave", description="Sai do canal de voz e limpa a fila.")
    async def leave(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        voice_client = interaction.guild.voice_client
        if not voice_client:
            return await interaction.followup.send("Eu não estou em um canal de voz.")
        await voice_client.disconnect()
        self.music_manager.get_state(interaction.guild.id).clear()
        await interaction.followup.send("Até mais! 👋")

    @app_commands.command(name="play", description="Busca e adiciona uma música à fila.")
    @app_commands.autocomplete(query=music_autocomplete)
    async def play(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer()
        
        if not interaction.user.voice:
            return await interaction.followup.send("Você precisa estar em um canal de voz.")

        state = self.music_manager.get_state(interaction.guild.id)
        voice_client = interaction.guild.voice_client

        if not voice_client or not voice_client.is_connected():
            vc = await self.music_manager.connect_voice(interaction)
            if not vc: return
        else:
            state.voice_client = voice_client
            state.text_channel = interaction.channel

        # Busca unificada (Link ou Termo)
        results = await search_songs(query)
        if not results:
            return await interaction.followup.send(f"❌ Nenhuma música encontrada para `{query}`.")

        view = MusicSearchView(self.music_manager, results)
        await interaction.followup.send(f"🔎 Resultados encontrados:", view=view)

    @app_commands.command(name="pause", description="Pausa a música atual.")
    async def pause(self, interaction: discord.Interaction) -> None:
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            await interaction.response.send_message("Música pausada. ⏸️")
        else:
            await interaction.response.send_message("Não há nada tocando agora.", ephemeral=True)

    @app_commands.command(name="resume", description="Retoma a música pausada.")
    async def resume(self, interaction: discord.Interaction) -> None:
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            await interaction.response.send_message("Música retomada. ▶️")
        else:
            await interaction.response.send_message("A música não está pausada.", ephemeral=True)

    @app_commands.command(name="skip", description="Pula para a próxima música.")
    async def skip(self, interaction: discord.Interaction) -> None:
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await interaction.response.send_message("Música pulada. ⏭️")
        else:
            await interaction.response.send_message("Não há nada para pular.", ephemeral=True)

    @app_commands.command(name="queue", description="Exibe a fila de músicas.")
    async def show_queue(self, interaction: discord.Interaction) -> None:
        state = self.music_manager.get_state(interaction.guild.id)
        if not state.queue:
            return await interaction.response.send_message("A fila está vazia.")

        embed = discord.Embed(title="🎵 Fila de Músicas", color=discord.Color.blurple())
        embed.description = "\n".join(
            f"{i + 1}. **{song.get('title', 'Desconhecido')}**"
            for i, song in enumerate(state.queue)
        )
        embed.set_footer(text=f"Loop: {state.loop or 'desligado'}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="loop", description="Define o modo de loop: song | queue | off")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Música", value="song"),
        app_commands.Choice(name="Fila", value="queue"),
        app_commands.Choice(name="Desligado", value="off")
    ])
    async def loop_cmd(self, interaction: discord.Interaction, mode: app_commands.Choice[str] = None) -> None:
        state = self.music_manager.get_state(interaction.guild.id)

        if mode is None:
            current = state.loop or "desligado"
            return await interaction.response.send_message(f"🔁 Modo de loop atual: **{current}**")

        if mode.value == "song":
            state.loop = LOOP_SONG
            await interaction.response.send_message("🔁 Loop da **música atual** ativado.")
        elif mode.value == "queue":
            state.loop = LOOP_QUEUE
            await interaction.response.send_message("🔁 Loop da **fila** ativado.")
        else:
            state.loop = LOOP_OFF
            await interaction.response.send_message("🔁 Loop **desligado**.")

    @app_commands.command(name="radio", description="Alterna o modo rádio Lo-Fi 24/7.")
    async def radio(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        state = self.music_manager.get_state(interaction.guild.id)
        state.radio_mode = not state.radio_mode
        
        if state.radio_mode:
            state.loop = LOOP_SONG
            await interaction.followup.send("📻 **Modo Rádio 24/7 Ativado!** O bot não vai se desconectar por inatividade.")
            
            if not interaction.user.voice:
                return await interaction.channel.send("Você precisa estar em um canal de voz para ouvir a rádio.")

            voice_client = interaction.guild.voice_client
            if not voice_client or not voice_client.is_connected():
                vc = await self.music_manager.connect_voice(interaction)
                if not vc:
                    return
            else:
                state.voice_client = voice_client
                state.text_channel = interaction.channel

            try:
                song = await extract_song_info(RADIO_URL)
                state.queue.append(song)
                vc = state.voice_client
                if vc and not vc.is_playing() and not vc.is_paused():
                    await self.music_manager.play_next(interaction.guild.id)
            except Exception as exc:
                print(f"[ERRO radio] {exc}")
                await interaction.channel.send("Erro ao sintonizar a rádio.")
        else:
            state.loop = LOOP_OFF
            await interaction.followup.send("📻 **Modo Rádio Desativado.**")

    @app_commands.command(name="playlist", description="Carrega uma playlist salva pelo Mestre.")
    async def playlist(self, interaction: discord.Interaction, nome: str) -> None:
        await interaction.response.defer()
        nome = nome.lower()
        if nome not in PLAYLISTS:
            await interaction.followup.send(f"❌ Playlist `{nome}` não encontrada. Playlists disponíveis: " + ", ".join(PLAYLISTS.keys()))
            return

        links = PLAYLISTS[nome]
        await interaction.followup.send(f"📂 Carregando playlist **{nome.capitalize()}** com {len(links)} músicas...")
        
        if not interaction.user.voice:
            return await interaction.channel.send("Você precisa estar em um canal de voz.")

        state = self.music_manager.get_state(interaction.guild.id)
        voice_client = interaction.guild.voice_client

        if not voice_client or not voice_client.is_connected():
            vc = await self.music_manager.connect_voice(interaction)
            if not vc:
                return
        else:
            state.voice_client = voice_client
            state.text_channel = interaction.channel

        for link in links:
            try:
                song = await extract_song_info(link)
                state.queue.append(song)
                await interaction.channel.send(f"✅ Adicionado à fila: **{song.get('title', 'Desconhecido')}**")
            except Exception as exc:
                print(f"[ERRO playlist] {exc}")
                
            vc = state.voice_client
            if vc and not vc.is_playing() and not vc.is_paused():
                await self.music_manager.play_next(interaction.guild.id)

    @app_commands.command(name="ambiente", description="Toca sons de ambiente para imersão (Chuva, Taverna, etc).")
    @app_commands.choices(som=[
        app_commands.Choice(name=k, value=v) for k, v in AMBIENT_SOUNDS.items()
    ])
    async def ambiente(self, interaction: discord.Interaction, som: app_commands.Choice[str]) -> None:
        await self.play(interaction, som.value)
        state = self.music_manager.get_state(interaction.guild.id)
        state.loop = LOOP_SONG # Força loop na música de ambiente
        await interaction.channel.send(f"🌌 **Clima alterado para:** {som.name}")

    @app_commands.command(name="volume", description="Ajusta o volume da música (0-100).")
    async def volume(self, interaction: discord.Interaction, nivel: int) -> None:
        state = self.music_manager.get_state(interaction.guild.id)
        state.volume = nivel / 100
        
        if state.voice_client and state.voice_client.source:
            if not isinstance(state.voice_client.source, discord.PCMVolumeTransformer):
                state.voice_client.source = discord.PCMVolumeTransformer(state.voice_client.source)
            state.voice_client.source.volume = state.volume
        
        await interaction.response.send_message(f"🔊 Volume ajustado para **{nivel}%**")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MusicaCog(bot))

