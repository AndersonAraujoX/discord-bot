"""
cogs/musica.py — Comandos de música (yt-dlp + FFmpeg)
======================================================
Estado de cada servidor encapsulado na classe GuildMusicState.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional

import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands

from config import FFMPEG_OPTIONS, IDLE_TIMEOUT, YTDL_OPTIONS, PLAYLISTS, RADIO_URL
from utils.music_helper import extract_song_info, search_songs, get_yt_suggestions

# Tipos de loop suportados
LOOP_SONG  = "song"
LOOP_QUEUE = "queue"
LOOP_OFF   = None

AMBIENT_SOUNDS = {
    "Chuva": "https://www.youtube.com/watch?v=mPZkdNFkNps",
    "Taverna": "https://www.youtube.com/watch?v=hBpcovn0kb4",
    "Floresta": "https://www.youtube.com/watch?v=xNN7iTA57jM",
    "Combate": "https://www.youtube.com/watch?v=17X2fB-M880",
    "Suspense": "https://www.youtube.com/watch?v=S_S7p6tFmXU"
}

class MusicControlView(discord.ui.View):
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


class MusicaCog(commands.Cog, name="Música"):
    """Comandos para tocar músicas em canais de voz."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._states: dict[int, GuildMusicState] = {}

    # ── Utilitários internos ─────────────────────────────────────────────────

    def _state(self, guild_id: int) -> GuildMusicState:
        if guild_id not in self._states:
            self._states[guild_id] = GuildMusicState()
        return self._states[guild_id]

    async def music_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Callback para sugestões do YouTube em tempo real."""
        if not current or len(current) < 3: return [] # Só busca após 3 caracteres
        suggestions = await get_yt_suggestions(current)
        return [
            app_commands.Choice(name=s, value=s)
            for s in suggestions[:25]
        ]

    async def _connect(self, interaction: discord.Interaction) -> Optional[discord.VoiceClient]:
        if not interaction.user.voice:
            await interaction.followup.send("Você não está em um canal de voz!")
            return None

        channel = interaction.user.voice.channel
        state   = self._state(interaction.guild.id)
        state.text_channel = interaction.channel

        voice_client = interaction.guild.voice_client

        if voice_client:
            await voice_client.move_to(channel)
            state.voice_client = voice_client
        else:
            state.voice_client = await channel.connect()

        return state.voice_client

    async def _add_to_queue(self, interaction: discord.Interaction, song: dict):
        state = self._state(interaction.guild.id)
        state.queue.append(song)
        
        embed = discord.Embed(
            title="✅ Adicionado à fila",
            description=f"**[{song['title']}]({song.get('webpage_url', '')})**",
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
            await self._play_next(interaction.guild.id)

class MusicSearchView(discord.ui.View):
    def __init__(self, cog, results):
        super().__init__(timeout=60)
        self.cog = cog
        self.results = results

        options = []
        for i, res in enumerate(results):
            # Limita título para 100 chars (limite do Select)
            title = res['title'][:100]
            options.append(discord.SelectOption(label=title, value=str(i), description=f"Duração: {res.get('duration', 0)}s"))

        self.select = discord.ui.Select(placeholder="Escolha uma música...", options=options)
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        idx = int(self.select.values[0])
        song = self.results[idx]
        await self.cog._add_to_queue(interaction, song)
        self.stop()


    async def _play_next(self, guild_id: int) -> None:
        state = self._state(guild_id)
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
                    self._play_next(guild_id), self.bot.loop
                ),
            )
            embed = discord.Embed(
                title="🎶 Tocando agora", 
                description=f"**[{song['title']}]({song.get('webpage_url', '')})**", 
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
            await self._play_next(guild_id)

    # ── Comandos ──────────────────────────────────────────────────────────────

    @app_commands.command(name="join", description="Entra no canal de voz atual.")
    async def join(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        vc = await self._connect(interaction)
        if vc:
            await interaction.followup.send(f"Entrei em: **{interaction.user.voice.channel.name}** 🎙️")

    @app_commands.command(name="leave", description="Sai do canal de voz e limpa a fila.")
    async def leave(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        voice_client = interaction.guild.voice_client
        if not voice_client:
            return await interaction.followup.send("Eu não estou em um canal de voz.")
        await voice_client.disconnect()
        self._state(interaction.guild.id).clear()
        await interaction.followup.send("Até mais! 👋")

    @app_commands.command(name="play", description="Busca e adiciona uma música à fila.")
    @app_commands.autocomplete(query=music_autocomplete)
    async def play(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer()
        
        if not interaction.user.voice:
            return await interaction.followup.send("Você precisa estar em um canal de voz.")

        state = self._state(interaction.guild.id)
        voice_client = interaction.guild.voice_client

        if not voice_client or not voice_client.is_connected():
            vc = await self._connect(interaction)
            if not vc: return
        else:
            state.voice_client = voice_client
            state.text_channel = interaction.channel

        # Se for link direto, toca logo
        if query.startswith("http"):
            song = await extract_song_info(query)
            if song:
                await self._add_to_queue(interaction, song)
            else:
                await interaction.followup.send("Não consegui carregar esse link.")
            return

        # Busca múltiplos resultados
        results = await search_songs(query)
        if not results:
            return await interaction.followup.send(f"❌ Nenhuma música encontrada para `{query}`.")

        view = MusicSearchView(self, results)
        await interaction.followup.send(f"🔎 Resultados para `{query}`:", view=view)

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
        state = self._state(interaction.guild.id)
        if not state.queue:
            return await interaction.response.send_message("A fila está vazia.")

        embed = discord.Embed(title="🎵 Fila de Músicas", color=discord.Color.blurple())
        embed.description = "\n".join(
            f"{i + 1}. **{song['title']}**"
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
        state = self._state(interaction.guild.id)

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
        state = self._state(interaction.guild.id)
        state.radio_mode = not state.radio_mode
        
        if state.radio_mode:
            state.loop = LOOP_SONG
            await interaction.followup.send("📻 **Modo Rádio 24/7 Ativado!** O bot não vai se desconectar por inatividade.")
            
            if not interaction.user.voice:
                return await interaction.channel.send("Você precisa estar em um canal de voz para ouvir a rádio.")

            voice_client = interaction.guild.voice_client
            if not voice_client or not voice_client.is_connected():
                vc = await self._connect(interaction)
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
                    await self._play_next(interaction.guild.id)
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

        state = self._state(interaction.guild.id)
        voice_client = interaction.guild.voice_client

        if not voice_client or not voice_client.is_connected():
            vc = await self._connect(interaction)
            if not vc:
                return
        else:
            state.voice_client = voice_client
            state.text_channel = interaction.channel

        for link in links:
            try:
                song = await extract_song_info(link)
                state.queue.append(song)
                await interaction.channel.send(f"✅ Adicionado à fila: **{song['title']}**")
            except Exception as exc:
                print(f"[ERRO playlist] {exc}")
                
            vc = state.voice_client
            if vc and not vc.is_playing() and not vc.is_paused():
                await self._play_next(interaction.guild.id)

    @app_commands.command(name="ambiente", description="Toca sons de ambiente para imersão (Chuva, Taverna, etc).")
    @app_commands.choices(som=[
        app_commands.Choice(name=k, value=v) for k, v in AMBIENT_SOUNDS.items()
    ])
    async def ambiente(self, interaction: discord.Interaction, som: app_commands.Choice[str]) -> None:
        await self.play(interaction, som.value)
        state = self._state(interaction.guild.id)
        state.loop = LOOP_SONG # Força loop na música de ambiente
        await interaction.channel.send(f"🌌 **Clima alterado para:** {som.name}")

    @app_commands.command(name="volume", description="Ajusta o volume da música (0-100).")
    async def volume(self, interaction: discord.Interaction, nivel: int) -> None:
        state = self._state(interaction.guild.id)
        state.volume = nivel / 100
        
        if state.voice_client and state.voice_client.source:
            if not isinstance(state.voice_client.source, discord.PCMVolumeTransformer):
                state.voice_client.source = discord.PCMVolumeTransformer(state.voice_client.source)
            state.voice_client.source.volume = state.volume
        
        await interaction.response.send_message(f"🔊 Volume ajustado para **{nivel}%**")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MusicaCog(bot))
