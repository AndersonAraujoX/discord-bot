"""
utils/dice_engine.py — Motor de rolagem de dados (sem dependências Discord)
============================================================================
Toda a lógica de rolagem fica aqui, tornando-a testável de forma isolada.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Optional

from config import DICE_MAX_COUNT, DICE_MAX_FACES, DICE_EXPLOSION_CAP


# ── Tipos de resultado ────────────────────────────────────────────────────────

@dataclass
class RollResult:
    """Resultado completo de uma rolagem."""
    notation: str          # notação normalizada (ex: "4d6d1")
    rolls: list[int]       # todos os dados rolados
    kept: list[int]        # dados que contam para o total
    dropped: list[int]     # dados descartados (drop mode)
    total: int
    exploded: bool = False


# ── Funções auxiliares ────────────────────────────────────────────────────────

def _roll_exploding(n: int, faces: int, explode_on: int) -> list[int]:
    """Rola n dados de `faces` lados com explosão a partir de `explode_on`."""
    results: list[int] = []
    to_roll = n
    total_count = 0

    while to_roll > 0:
        batch, next_explode = [], 0
        for _ in range(to_roll):
            r = random.randint(1, faces)
            batch.append(r)
            total_count += 1
            if r >= explode_on:
                next_explode += 1
        results.extend(batch)
        to_roll = next_explode
        if total_count >= DICE_EXPLOSION_CAP:
            break

    return results


# ── Parser de notações ────────────────────────────────────────────────────────

# Padrão: (N?)d(FACES)(drop?)(explode?)(mod?)
_RE_DROP    = re.compile(r"^(\d+)d(\d+)d(\d+)([+-]\d+)?$",      re.IGNORECASE)
_RE_EXPLODE = re.compile(r"^(\d*)d(\d+)(!(\d*))?([+-]\d+)?$",   re.IGNORECASE)


def parse_roll(notation: str) -> Optional[RollResult]:
    """
    Analisa uma notação de dado e retorna um RollResult.
    Retorna None se a notação for inválida.

    Formatos suportados:
      XdY          → padrão (ex: 4d6, d20)
      XdY+K        → com bônus (ex: 1d20+5)
      XdY-K        → com penalidade (ex: 1d20-2)
      XdY!         → explosivo no máximo (ex: d6!)
      XdY!Z        → explosivo a partir de Z (ex: 3d10!8)
      XdYdZ        → drop: rola X dados, descarta os Z menores (ex: 4d6d1)
    """
    notation = notation.strip().replace(" ", "").lower()

    # ── Drop: XdYdZ[+-K] ─────────────────────────────────────────────────────
    m = _RE_DROP.fullmatch(notation)
    if m:
        n, faces, drop = int(m.group(1)), int(m.group(2)), int(m.group(3))
        mod = int(m.group(4)) if m.group(4) else 0
        
        if drop >= n:
            return None   # inválido: descartaria tudo
        if n > DICE_MAX_COUNT or faces > DICE_MAX_FACES:
            return None

        rolls_sorted = sorted(random.randint(1, faces) for _ in range(n))
        dropped = rolls_sorted[:drop]
        kept    = rolls_sorted[drop:]
        
        final_notation = f"{n}d{faces}d{drop}"
        if mod: final_notation += f"{mod:+d}"

        return RollResult(
            notation=final_notation,
            rolls=rolls_sorted,
            kept=kept,
            dropped=dropped,
            total=sum(kept) + mod,
        )

    # ── Padrão / Explosivo: (N?)dY(!Z?)[+-K] ──────────────────────────────────
    m = _RE_EXPLODE.fullmatch(notation)
    if m:
        n        = int(m.group(1)) if m.group(1) else 1
        faces    = int(m.group(2))
        explode  = m.group(3) is not None
        expl_val = m.group(4)
        explode_on = int(expl_val) if (expl_val and expl_val != "") else faces
        mod      = int(m.group(5)) if m.group(5) else 0

        if n < 1 or faces < 2 or n > DICE_MAX_COUNT or faces > DICE_MAX_FACES:
            return None

        if explode:
            rolls = _roll_exploding(n, faces, explode_on)
        else:
            rolls = [random.randint(1, faces) for _ in range(n)]

        final_notation = f"{n}d{faces}"
        if explode: final_notation += f"!{explode_on if explode_on != faces else ''}"
        if mod: final_notation += f"{mod:+d}"

        return RollResult(
            notation=final_notation,
            rolls=rolls,
            kept=rolls,
            dropped=[],
            total=sum(rolls) + mod,
            exploded=explode,
        )

    return None


# ── Formatadores de mensagem ──────────────────────────────────────────────────

def format_result(result: RollResult) -> str:
    """Formata um RollResult para exibição no Discord."""
    if result.dropped:
        d_str = ", ".join(f"~~{d}~~" for d in result.dropped)
        k_str = ", ".join(str(k) for k in result.kept)
        return (
            f"⬇️ **{result.notation.upper()}**\n"
            f"Rolados: {d_str}, {k_str}\n"
            f"Total (mantido): **{result.total}**"
        )

    r_str = ", ".join(str(r) for r in result.rolls)
    icon  = "💥" if result.exploded else "🎲"
    return (
        f"{icon} **{result.notation.upper()}**\n"
        f"Resultados: ({r_str})\n"
        f"Total: **{result.total}**"
    )
