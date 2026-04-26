"""
cogs/rpg.py — Comandos de RPG com personagem Rilem/Miler via Gemini
====================================================================
"""

import asyncio

import discord
from discord.ext import commands
from google import genai

from config import GEMINI_ENABLED, GEMINI_MODEL, GOOGLE_API_KEY, RILEM_MILER_PROMPT

_INTRO_PROMPT = (
    "Apresente-se brevemente aos aventureiros que acabaram de te encontrar, "
    "mantendo sua personalidade."
)


class RpgCog(commands.Cog, name="RPG"):
    """Sessões de RPG imersivas com IA Gemini."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._sessions: dict[int, dict] = {}
        # Inicializa o cliente do novo SDK
        self._client = genai.Client(api_key=GOOGLE_API_KEY) if GEMINI_ENABLED else None

    # ── Listener: responde quando mencionado durante sessão ──────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.bot.user:
            return
        if not message.guild:
            return
        if message.guild.id not in self._sessions:
            return
        if not self.bot.user.mentioned_in(message):
            return

        prompt = (
            message.content
            .replace(f"<@!{self.bot.user.id}>", "")
            .replace(f"<@{self.bot.user.id}>", "")
            .strip()
        )
        if not prompt:
            return

        chat = self._sessions[message.guild.id]["chat"]
        async with message.channel.typing():
            try:
                response = await asyncio.to_thread(
                    chat.send_message, prompt
                )
                await message.reply(response.text)
            except Exception as exc:
                await message.channel.send(
                    f"Desculpe, meu cérebro de IA bugou. 💥 Erro: `{exc}`"
                )

    # ── Comandos ──────────────────────────────────────────────────────────────

    @commands.command(name="rpg_start")
    async def rpg_start(self, ctx: commands.Context) -> None:
        """Inicia uma sessão de RPG com o personagem Rilem/Miler."""
        if not GEMINI_ENABLED or not self._client:
            return await ctx.send(
                "❌ RPG desabilitado — configure `GOOGLE_API_KEY` no `.env`."
            )
        if ctx.guild.id in self._sessions:
            return await ctx.send(
                "Já há uma sessão ativa. Use `!rpg_stop` para encerrá-la."
            )

        try:
            chat = self._client.chats.create(
                model=GEMINI_MODEL,
                history=[{"role": "user", "parts": [RILEM_MILER_PROMPT]}],
            )
            inicial = await asyncio.to_thread(chat.send_message, _INTRO_PROMPT)
            self._sessions[ctx.guild.id] = {"chat": chat}

            await ctx.send(
                f"**Sessão de RPG iniciada!** O bot agora é **Rilem/Miler**.\n\n"
                f"> {inicial.text}\n\n"
                f"*Mencione-me (@{self.bot.user.name}) para interagir.*"
            )
        except Exception as exc:
            await ctx.send(f"Não foi possível iniciar o RPG. Erro: `{exc}`")

    @commands.command(name="rpg_stop")
    async def rpg_stop(self, ctx: commands.Context) -> None:
        """Encerra a sessão de RPG ativa."""
        if ctx.guild.id in self._sessions:
            del self._sessions[ctx.guild.id]
            await ctx.send("Sessão encerrada. Voltei ao modo normal. 🤖")
        else:
            await ctx.send("Nenhuma sessão de RPG está ativa.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RpgCog(bot))
