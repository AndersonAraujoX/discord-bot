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
from discord.ext import commands

from config import FFMPEG_OPTIONS, IDLE_TIMEOUT, YTDL_OPTIONS

# Tipos de loop suportados
LOOP_SONG  = "song"
LOOP_QUEUE = "queue"
LOOP_OFF   = None


@dataclass
class GuildMusicState:
    """Estado de música isolado por servidor (guild)."""
    queue:        list[dict]             = field(default_factory=list)
    voice_client: Optional[discord.VoiceClient] = None
    current:      Optional[dict]         = None
    loop:         Optional[str]          = None   # LOOP_SONG | LOOP_QUEUE | None

    def clear(self) -> None:
        self.queue.clear()
        self.current = None
        self.loop    = None


class MusicaCog(commands.Cog, name="Música"):
    """Comandos para tocar músicas em canais de voz."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._states: dict[int, GuildMusicState] = {}

    # ── Utilitários internos ─────────────────────────────────────────────────

    def _state(self, guild_id: int) -> GuildMusicState:
        """Retorna (criando se necessário) o estado do servidor."""
        if guild_id not in self._states:
            self._states[guild_id] = GuildMusicState()
        return self._states[guild_id]

    async def _connect(self, ctx: commands.Context) -> Optional[discord.VoiceClient]:
        """Conecta ou move o bot ao canal de voz do autor."""
        if not ctx.author.voice:
            await ctx.send("Você não está em um canal de voz!")
            return None

        channel = ctx.author.voice.channel
        state   = self._state(ctx.guild.id)

        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
            state.voice_client = ctx.voice_client
        else:
            state.voice_client = await channel.connect()

        return state.voice_client

    async def _search_song(self, query: str) -> Optional[dict]:
        """Busca informações da música via yt-dlp de forma assíncrona."""
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            info = await loop.run_in_executor(
                None, lambda: ydl.extract_info(query, download=False)
            )
        if "entries" in info:
            info = info["entries"][0]
        return {"source": info["url"], "title": info["title"]}

    async def _play_next(self, ctx: commands.Context) -> None:
        """Toca a próxima música da fila, aplicando a lógica de loop."""
        state = self._state(ctx.guild.id)
        vc    = state.voice_client

        if not vc or not vc.is_connected():
            return

        # Reinsere a música atual conforme o modo de loop
        if state.current:
            if state.loop == LOOP_SONG:
                state.queue.insert(0, state.current)
            elif state.loop == LOOP_QUEUE:
                state.queue.append(state.current)

        if not state.queue:
            state.current = None
            await ctx.send("A fila terminou. 🎵")
            if state.loop != LOOP_QUEUE:
                await asyncio.sleep(IDLE_TIMEOUT)
                if vc and not vc.is_playing():
                    await vc.disconnect()
                    state.voice_client = None
            return

        song           = state.queue.pop(0)
        state.current  = song

        try:
            source = discord.FFmpegPCMAudio(song["source"], **FFMPEG_OPTIONS)
            vc.play(
                source,
                after=lambda _: asyncio.run_coroutine_threadsafe(
                    self._play_next(ctx), self.bot.loop
                ),
            )
            await ctx.send(f"🎶 Tocando agora: **{song['title']}**")
        except Exception as exc:
            await ctx.send(f"Erro ao tocar música: `{exc}`")
            state.current = None
            await self._play_next(ctx)

    # ── Comandos ──────────────────────────────────────────────────────────────

    @commands.command(name="join")
    async def join(self, ctx: commands.Context) -> None:
        """Entra no canal de voz do usuário."""
        vc = await self._connect(ctx)
        if vc:
            await ctx.send(f"Entrei em: **{ctx.author.voice.channel.name}** 🎙️")

    @commands.command(name="leave")
    async def leave(self, ctx: commands.Context) -> None:
        """Sai do canal de voz e limpa a fila."""
        if not ctx.voice_client:
            return await ctx.send("Eu não estou em um canal de voz.")
        await ctx.voice_client.disconnect()
        self._state(ctx.guild.id).clear()
        await ctx.send("Até mais! 👋")

    @commands.command(name="play")
    async def play(self, ctx: commands.Context, *, query: str) -> None:
        """Busca e adiciona uma música à fila (nome ou link direto)."""
        if not ctx.author.voice:
            return await ctx.send("Você precisa estar em um canal de voz.")

        state = self._state(ctx.guild.id)

        if not ctx.voice_client or not ctx.voice_client.is_connected():
            vc = await self._connect(ctx)
            if not vc:
                return
        else:
            state.voice_client = ctx.voice_client

        await ctx.send(f"🔎 Procurando por `{query}`...")
        try:
            song = await self._search_song(query)
        except Exception as exc:
            print(f"[ERRO play] {exc}")
            return await ctx.send(
                "Não consegui encontrar a música. "
                "Se for do YouTube, verifique se `cookies.txt` está presente."
            )

        state.queue.append(song)
        await ctx.send(f"✅ Adicionado à fila: **{song['title']}**")

        vc = state.voice_client
        if vc and not vc.is_playing() and not vc.is_paused():
            await self._play_next(ctx)

    @commands.command(name="pause")
    async def pause(self, ctx: commands.Context) -> None:
        """Pausa a música atual."""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("Música pausada. ⏸️")
        else:
            await ctx.send("Não há nada tocando agora.")

    @commands.command(name="resume")
    async def resume(self, ctx: commands.Context) -> None:
        """Retoma a música pausada."""
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("Música retomada. ▶️")
        else:
            await ctx.send("A música não está pausada.")

    @commands.command(name="skip")
    async def skip(self, ctx: commands.Context) -> None:
        """Pula para a próxima música."""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()   # dispara o callback after → _play_next
            await ctx.send("Música pulada. ⏭️")
        else:
            await ctx.send("Não há nada para pular.")

    @commands.command(name="queue", aliases=["q", "fila"])
    async def show_queue(self, ctx: commands.Context) -> None:
        """Exibe a fila de músicas."""
        state = self._state(ctx.guild.id)
        if not state.queue:
            return await ctx.send("A fila está vazia.")

        embed = discord.Embed(title="🎵 Fila de Músicas", color=discord.Color.blurple())
        embed.description = "\n".join(
            f"{i + 1}. **{song['title']}**"
            for i, song in enumerate(state.queue)
        )
        embed.set_footer(text=f"Loop: {state.loop or 'desligado'}")
        await ctx.send(embed=embed)

    @commands.command(name="loop")
    async def loop_cmd(self, ctx: commands.Context, mode: str = None) -> None:
        """Define o modo de loop: song | queue | off"""
        state = self._state(ctx.guild.id)

        if mode is None:
            current = state.loop or "desligado"
            return await ctx.send(f"🔁 Modo de loop atual: **{current}**")

        mode = mode.lower()
        if mode in ("song", "musica", "música"):
            state.loop = LOOP_SONG
            await ctx.send("🔁 Loop da **música atual** ativado.")
        elif mode in ("queue", "fila"):
            state.loop = LOOP_QUEUE
            await ctx.send("🔁 Loop da **fila** ativado.")
        elif mode in ("off", "desligar", "parar", "none"):
            state.loop = LOOP_OFF
            await ctx.send("🔁 Loop **desligado**.")
        else:
            await ctx.send("Modo inválido. Use: `song`, `queue` ou `off`.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MusicaCog(bot))
