"""
cogs/dados.py — Comandos de rolagem de dados
=============================================
Toda a lógica de rolagem vive em utils/dice_engine.py.
Este Cog apenas interpreta os argumentos e formata as saídas.
"""

import re
import discord
from collections import Counter

from discord.ext import commands

from config import BULK_ROLL_LIMIT
from utils.dice_engine import format_result, parse_roll


class DadosCog(commands.Cog, name="Dados"):
    """Sistema avançado de rolagem de dados."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ── Guia de Ajuda ─────────────────────────────────────────────────────────
    @commands.command(name="dados")
    async def help_dados(self, ctx: commands.Context) -> None:
        """Exibe o guia de como rolar dados."""
        help_text = (
            "🎲 **Guia de Rolagem de Dados**\n\n"
            "**Básico:**\n"
            "`d20` — Rola um dado de 20 faces.\n"
            "`3d6` — Rola 3 dados de 6 faces e soma tudo.\n\n"
            "**Variações Avançadas:**\n"
            "`d20+5` — Adiciona um bônus ao total.\n"
            "`4d6d1` — Rola 4 dados e **descarta (drop)** o menor (comum em D&D).\n"
            "`d6!` — Dado **Explosivo** (se tirar 6, rola outro e soma).\n"
            "`3d10!8` — Explode se tirar 8, 9 ou 10.\n\n"
            "**Rolagem em Massa:**\n"
            "`10#d20` — Faz 10 rolagens de d20 de uma vez.\n"
            "`6#4d6d1` — Gera 6 atributos de personagem (D&D).\n"
        )
        await ctx.send(help_text)

    # ── Auto-Roll: Detecta se a mensagem é apenas um dado ──────────────────────
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        content = message.content.lower().strip()

        # Rolagem em massa: N#notação
        m = re.fullmatch(r"(\d+)#(.+)", content)
        if m:
            # Verifica se a parte direita é uma notação de dados válida
            if re.fullmatch(r"(\d*d\d+.*)", m.group(2)):
                await self._bulk_roll(message, int(m.group(1)), m.group(2))
            return

        # Rolagem simples
        if re.fullmatch(r"(\d*d\d+.*)", content):
            result = parse_roll(content)
            if result:
                await message.channel.send(format_result(result))

    # ── Auxiliar para rolagem em massa ────────────────────────────────────────

    async def _bulk_roll(
        self, message: discord.Message, num_rolls: int, notation: str
    ) -> None:
        if num_rolls > BULK_ROLL_LIMIT:
            return await message.channel.send(f"Limite: {BULK_ROLL_LIMIT} rolagens em massa por vez.")

        # Valida a notação antes de repetir
        test = parse_roll(notation)
        if test is None:
            return await message.channel.send("Notação inválida para rolagem em massa.")

        totais = []
        lines  = []
        for i in range(num_rolls):
            r = parse_roll(notation)   # rola de novo a cada iteração
            totais.append(r.total)
            lines.append(f"Rolagem {i + 1}: **{r.total}**")

        # Estatísticas rápidas
        counter = Counter(totais)
        top_str = " · ".join(
            f"{v}×**{k}**"
            for k, v in sorted(counter.items(), key=lambda x: -x[1])[:5]
        )

        await message.channel.send(
            f"📊 **Massa {num_rolls}× {notation.upper()}**\n"
            f"```\n{chr(10).join(lines)}```"
            f"Mais frequentes: {top_str}"
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DadosCog(bot))
