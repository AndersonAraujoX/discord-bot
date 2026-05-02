import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.storage import load_rpg_data, save_rpg_data

# Simulamos a lógica de magia do RpgMagicCog diretamente em dados
def test_magic_logic():
    test_data = {"users": {"test_uid": {"mana": {"atual": 10, "max": 10}, "grimorio": []}}}
    save_rpg_data(test_data)
    
    # Simula /magia aprender
    data = load_rpg_data()
    grimorio = data["users"]["test_uid"].setdefault("grimorio", [])
    grimorio.append({"nome": "Bola de Fogo", "desc": "Causa dano de fogo.", "mana": 3})
    save_rpg_data(data)
    
    # Verifica aprender
    loaded = load_rpg_data()
    assert len(loaded["users"]["test_uid"]["grimorio"]) == 1
    assert loaded["users"]["test_uid"]["grimorio"][0]["nome"] == "Bola de Fogo"
    
    # Simula /magia castar
    data = load_rpg_data()
    mana_info = data["users"]["test_uid"]["mana"]
    magia = data["users"]["test_uid"]["grimorio"][0]
    
    assert mana_info["atual"] >= magia["mana"]
    mana_info["atual"] -= magia["mana"]
    save_rpg_data(data)
    
    # Verifica castar
    loaded = load_rpg_data()
    assert loaded["users"]["test_uid"]["mana"]["atual"] == 7
    
    print("✅ Testes de Magia passaram!")

if __name__ == "__main__":
    test_magic_logic()
