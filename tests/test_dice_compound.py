import os
import sys
import unittest
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.dice_engine import MAX_COMPOUND_TERMS, format_result, parse_roll


class TestCompoundDice(unittest.TestCase):
    """Expressões com várias parcelas: NdN + MdM + valor."""

    # ── Caminho feliz ────────────────────────────────────────────────────────

    @patch("utils.dice_engine.random.randint", return_value=4)
    def test_dice_plus_dice_plus_constant(self, _):
        # Arrange / Act
        res = parse_roll("2d6 + 1d4 + 3")
        # Assert: (4+4) + 4 + 3
        self.assertIsNotNone(res)
        self.assertEqual(res.total, 15)
        self.assertEqual(res.rolls, [4, 4, 4])
        self.assertEqual(res.notation, "2d6+1d4+3")

    @patch("utils.dice_engine.random.randint", return_value=10)
    def test_multiple_constants(self, _):
        res = parse_roll("1d20+5+2")
        self.assertEqual(res.total, 17)
        self.assertEqual(res.notation, "1d20+5+2")

    @patch("utils.dice_engine.random.randint", return_value=3)
    def test_subtraction_of_dice_and_constant(self, _):
        res = parse_roll("2d6-1d4-1")
        # 6 - 3 - 1
        self.assertEqual(res.total, 2)
        self.assertEqual(res.notation, "2d6-1d4-1")

    @patch("utils.dice_engine.random.randint", return_value=5)
    def test_simple_notation_still_uses_single_path(self, _):
        res = parse_roll("1d20+5")
        self.assertEqual(res.total, 10)
        self.assertEqual(res.notation, "1d20+5")

    def test_drop_term_inside_compound(self):
        res = parse_roll("4d6d1+2")  # caminho simples, regressão
        self.assertEqual(res.total, sum(sorted(res.rolls)[1:]) + 2)
        res2 = parse_roll("4d6d1+1d4+2")
        self.assertIsNotNone(res2)
        self.assertEqual(len(res2.dropped), 1)
        self.assertEqual(len(res2.rolls), 5)

    @patch("utils.dice_engine.random.randint", return_value=6)
    def test_exploded_flag_propagates(self, _):
        res = parse_roll("1d6!+1d4")
        self.assertTrue(res.exploded)

    def test_format_result_for_compound(self):
        res = parse_roll("1d20+1d4+1")
        text = format_result(res)
        self.assertIn("1D20+1D4+1", text)
        self.assertIn(f"**{res.total}**", text)

    # ── Casos de borda ───────────────────────────────────────────────────────

    def test_only_constants_is_invalid(self):
        self.assertIsNone(parse_roll("3+4"))

    def test_trailing_or_leading_operator_is_invalid(self):
        self.assertIsNone(parse_roll("1d20+"))
        self.assertIsNone(parse_roll("+1d20+3x"))
        self.assertIsNone(parse_roll("1d20++3"))

    def test_empty_and_garbage(self):
        self.assertIsNone(parse_roll(""))
        self.assertIsNone(parse_roll("   "))
        self.assertIsNone(parse_roll("abc+def"))

    def test_too_many_terms_is_invalid(self):
        expr = "+".join(["1d4"] * (MAX_COMPOUND_TERMS + 1))
        self.assertIsNone(parse_roll(expr))

    def test_at_term_limit_is_valid(self):
        expr = "+".join(["1d4"] * MAX_COMPOUND_TERMS)
        res = parse_roll(expr)
        self.assertIsNotNone(res)
        self.assertEqual(len(res.rolls), MAX_COMPOUND_TERMS)

    # ── Tratamento de erros ──────────────────────────────────────────────────

    def test_invalid_term_invalidates_whole_expression(self):
        self.assertIsNone(parse_roll("2d6+1d1+3"))     # d1 inválido (faces < 2)
        self.assertIsNone(parse_roll("2d6+0d4"))       # 0 dados

    @patch("utils.dice_engine.DICE_MAX_COUNT", 5)
    def test_total_dice_over_limit_is_invalid(self):
        self.assertIsNone(parse_roll("3d6+3d6+1"))

    def test_random_result_bounds(self):
        for _ in range(200):
            res = parse_roll("2d6+1d4+3")
            self.assertTrue(6 <= res.total <= 19)


if __name__ == "__main__":
    unittest.main()
