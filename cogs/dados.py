"""
cogs/dados.py — Comandos de rolagem de dados
=============================================
Toda a lógica de rolagem vive em utils/dice_engine.py.
Este Cog apenas interpreta os argumentos e formata as saídas.
"""

import re
from collections import Counter

from discord.ext import commands

from config import BULK_ROLL_LIMIT
from utils.dice_engine import format_result, parse_roll


class DadosCog(commands.Cog, name="Dados"):
    """Sistema avançado de rolagem de dados."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ── Comando principal ─────────────────────────────────────────────────────

    @commands.command(name="roll", aliases=["r"])
    async def roll(self, ctx: commands.Context, *, diceroll: str) -> None:
        """
        Rola dados. Formatos suportados:
          XdY         → padrão         ex: 4d6, d20
          XdY!        → explosivo       ex: d6!, 3d10!
          XdY!Z       → explode em Z+   ex: 3d10!8
          XdYdZ       → drop lowest Z   ex: 4d6d1
          N#XdY       → massa N vezes   ex: 6#4d6d1
        """
        diceroll = diceroll.lower().strip()

        # ── Rolagem em massa: N#notação ───────────────────────────────────────
        m = re.fullmatch(r"(\d+)#(.+)", diceroll)
        if m:
            await self._bulk_roll(ctx, int(m.group(1)), m.group(2))
            return

        # ── Rolagem simples ───────────────────────────────────────────────────
        result = parse_roll(diceroll)
        if result is None:
            return await ctx.send(
                "Formato inválido. Exemplos:\n"
                "`!roll d20`, `!roll 4d6`, `!roll 4d6d1`, `!roll d6!`, `!roll 6#4d6d1`"
            )
        await ctx.send(format_result(result))

    # ── Auxiliar para rolagem em massa ────────────────────────────────────────

    async def _bulk_roll(
        self, ctx: commands.Context, num_rolls: int, notation: str
    ) -> None:
        if num_rolls > BULK_ROLL_LIMIT:
            return await ctx.send(f"Limite: {BULK_ROLL_LIMIT} rolagens em massa por vez.")

        # Valida a notação antes de repetir
        test = parse_roll(notation)
        if test is None:
            return await ctx.send("Notação inválida para rolagem em massa.")

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

        await ctx.send(
            f"📊 **Massa {num_rolls}× {notation.upper()}**\n"
            f"```\n{chr(10).join(lines)}```"
            f"Mais frequentes: {top_str}"
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DadosCog(bot))
