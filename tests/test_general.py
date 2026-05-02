import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.rpg_core import get_hp_bar

def test_hp_bar():
    # Teste 100%
    bar = get_hp_bar(100, 100)
    assert "🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩" in bar
    assert "100/100" in bar
    
    # Teste 50%
    bar = get_hp_bar(50, 100)
    assert "🟩🟩🟩🟩🟩⬜⬜⬜⬜⬜" in bar
    assert "50/100" in bar
    
    # Teste 0%
    bar = get_hp_bar(0, 100)
    assert "⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜" in bar
    assert "0/100" in bar

    # Teste overflow (HP atual > Max)
    bar = get_hp_bar(150, 100)
    assert "🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩" in bar

    print("✅ Testes de HP Bar passaram!")

if __name__ == "__main__":
    test_hp_bar()
