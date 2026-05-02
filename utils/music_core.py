"""
utils/music_core.py — Lógica de Estado e Reprodução Musical
===========================================================
Encapsula o gerenciamento de filas (GuildMusicState) e o 
comportamento do player de áudio (FFmpeg) de forma pura,
desacoplada dos Comandos do Discord.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional

import discord
from discord.ext import commands

from config import FFMPEG_OPTIONS, IDLE_TIMEOUT
from utils.music_helper import extract_song_info
from utils.ui_components import LOOP_SONG, LOOP_QUEUE, LOOP_OFF, MusicControlView


@dataclass
class GuildMusicState:
    """Estado de música isolado por servidor (guild)."""
    queue:        list[dict]             = field(default_factory=list)
    voice_client: Optional[discord.VoiceClient] = None
    text_channel: Optional[discord.TextChannel] = None
    current:      Optional[dict]         = None
    loop:         Optional[str]          = None   # LOOP_SONG | LOOP_QUEUE | None
    radio_mode:   bool                   = False
    volume:       float                  = 1.0

    def clear(self) -> None:
        self.queue.clear()
        self.current = None
        self.loop    = None
        self.radio_mode = False


class MusicManager:
    """
    Controlador centralizado do sistema de áudio para todos os servidores.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._states: dict[int, GuildMusicState] = {}

    def get_state(self, guild_id: int) -> GuildMusicState:
        """Obtém ou cria o estado de música para um servidor."""
        if guild_id not in self._states:
            self._states[guild_id] = GuildMusicState()
        return self._states[guild_id]

    async def connect_voice(self, interaction: discord.Interaction) -> Optional[discord.VoiceClient]:
        """Conecta o bot ao canal de voz do usuário que invocou o comando."""
        if not interaction.user.voice:
            await interaction.followup.send("Você não está em um canal de voz!", ephemeral=True)
            return None

        channel = interaction.user.voice.channel
        state   = self.get_state(interaction.guild.id)
        state.text_channel = interaction.channel

        voice_client = interaction.guild.voice_client

        if voice_client:
            await voice_client.move_to(channel)
            state.voice_client = voice_client
        else:
            state.voice_client = await channel.connect()

        return state.voice_client

    async def add_to_queue(self, interaction: discord.Interaction, song: dict):
        """Adiciona uma música à fila e tenta tocá-la se o player estiver ocioso."""
        state = self.get_state(interaction.guild.id)
        state.queue.append(song)
        
        embed = discord.Embed(
            title="✅ Adicionado à fila",
            description=f"**[{song.get('title', 'Desconhecido')}]({song.get('webpage_url', '')})**",
            color=discord.Color.blue()
        )
        if song.get("thumbnail"):
            embed.set_thumbnail(url=song["thumbnail"])
            
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)

        vc = state.voice_client
        if vc and not vc.is_playing() and not vc.is_paused():
            await self.play_next(interaction.guild.id)

    async def play_fx(self, interaction: discord.Interaction, url: str):
        """Toca um efeito sonoro curto sem parar a música de fundo permanentemente."""
        state = self.get_state(interaction.guild.id)
        if not state.voice_client:
            vc = await self.connect_voice(interaction)
            if not vc: return
        
        # Se já estiver deferido ou respondido
        if not interaction.response.is_done():
            await interaction.response.send_message(f"🔊 Efeito sonoro acionado!", ephemeral=True)
        else:
            await interaction.followup.send(f"🔊 Efeito sonoro acionado!", ephemeral=True)
        
        song = await extract_song_info(url)
        if song:
            if state.voice_client.is_playing():
                # Re-adiciona a música atual no topo (após o FX) para continuar de onde parou 
                if state.current:
                    state.queue.insert(0, state.current)
                state.queue.insert(0, song)
                state.voice_client.stop() # Mata a atual para rodar o FX
            else:
                state.queue.insert(0, song)
                await self.play_next(interaction.guild.id)

    async def play_next(self, guild_id: int) -> None:
        """Processa a próxima música da fila para o servidor informado."""
        state = self.get_state(guild_id)
        vc    = state.voice_client

        if not vc or not vc.is_connected():
            return

        if state.current:
            if state.loop == LOOP_SONG:
                state.queue.insert(0, state.current)
            elif state.loop == LOOP_QUEUE:
                state.queue.append(state.current)

        if not state.queue:
            state.current = None
            if state.text_channel:
                await state.text_channel.send("A fila terminou. 🎵")
            if state.loop != LOOP_QUEUE and not state.radio_mode:
                await asyncio.sleep(IDLE_TIMEOUT)
                if vc and not vc.is_playing():
                    await vc.disconnect()
                    state.voice_client = None
            return

        song           = state.queue.pop(0)
        state.current  = song

        try:
            source = discord.FFmpegPCMAudio(song["source"], **FFMPEG_OPTIONS)
            source = discord.PCMVolumeTransformer(source, volume=state.volume)
            vc.play(
                source,
                after=lambda _: asyncio.run_coroutine_threadsafe(
                    self.play_next(guild_id), self.bot.loop
                ),
            )
            embed = discord.Embed(
                title="🎶 Tocando agora", 
                description=f"**[{song.get('title', 'Desconhecido')}]({song.get('webpage_url', '')})**", 
                color=discord.Color.green()
            )
            if song.get("thumbnail"):
                embed.set_thumbnail(url=song["thumbnail"])
            
            if state.text_channel:
                view = MusicControlView(self, guild_id)
                await state.text_channel.send(embed=embed, view=view)
        except Exception as exc:
            if state.text_channel:
                await state.text_channel.send(f"Erro ao tocar música: `{exc}`")
            state.current = None
            await self.play_next(guild_id)
