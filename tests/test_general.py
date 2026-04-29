import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cogs.rpg_manager import RpgManagerCog

# Mock do bot para inicializar o Cog
class MockBot:
    pass

def test_hp_bar():
    cog = RpgManagerCog(MockBot())
    
    # Teste 100%
    bar = cog._get_hp_bar(100, 100)
    assert "🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩" in bar
    assert "100/100" in bar
    
    # Teste 50%
    bar = cog._get_hp_bar(50, 100)
    assert "🟩🟩🟩🟩🟩⬜⬜⬜⬜⬜" in bar
    assert "50/100" in bar
    
    # Teste 0%
    bar = cog._get_hp_bar(0, 100)
    assert "⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜" in bar
    assert "0/100" in bar

    # Teste overflow (HP atual > Max)
    bar = cog._get_hp_bar(150, 100)
    assert "🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩" in bar

    print("✅ Testes de HP Bar passaram!")

if __name__ == "__main__":
    test_hp_bar()
