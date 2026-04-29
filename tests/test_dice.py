import sys
import os
# Adiciona o diretório raiz ao path para encontrar os módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.dice_engine import parse_roll

def test_single_die():
    res = parse_roll("d20")
    assert res is not None
    assert 1 <= res.total <= 20
    assert len(res.rolls) == 1

def test_multiple_dice():
    res = parse_roll("3d6")
    assert res is not None
    assert 3 <= res.total <= 18
    assert len(res.rolls) == 3

def test_modifier():
    # Rola 1 dado e soma 5. O total deve ser entre 6 e 25.
    res = parse_roll("1d20+5")
    assert res is not None
    assert 6 <= res.total <= 25
    assert "+5" in res.notation

def test_invalid_notation():
    assert parse_roll("abc") is None
    assert parse_roll("d") is None
    assert parse_roll("") is None

def test_drop_lowest():
    # 4d6d1 rola 4 dados de 6 e descarta o menor
    res = parse_roll("4d6d1")
    assert res is not None
    assert len(res.rolls) == 4
    # O total deve ser a soma dos 3 maiores
    sorted_dice = sorted(res.rolls)
    assert res.total == sum(sorted_dice[1:])

if __name__ == "__main__":
    # Simples runner manual se não tiver pytest instalado
    print("Executando testes de dados...")
    test_single_die()
    test_multiple_dice()
    test_modifier()
    test_invalid_notation()
    test_drop_lowest()
    print("✅ Todos os testes de dados passaram!")
