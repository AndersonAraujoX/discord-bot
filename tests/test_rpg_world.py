import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.storage import load_rpg_data, save_rpg_data

def test_world_logic():
    # Setup state
    test_data = {
        "hp": {"miler": {"atual": 10, "max": 20}},
        "users": {"123": {"mana": {"atual": 5, "max": 20}}},
        "statuses": {"miler": ["Envenenado"]}
    }
    save_rpg_data(test_data)
    
    # Teste Descanso Curto (recupera 25%)
    data = load_rpg_data()
    # Miler hp += max(1, 20//4) -> 5. Atual vai para 15
    data["hp"]["miler"]["atual"] += max(1, data["hp"]["miler"]["max"] // 4)
    data["users"]["123"]["mana"]["atual"] += max(1, data["users"]["123"]["mana"]["max"] // 4)
    save_rpg_data(data)
    
    loaded = load_rpg_data()
    assert loaded["hp"]["miler"]["atual"] == 15
    assert loaded["users"]["123"]["mana"]["atual"] == 10
    
    # Teste Descanso Longo
    data = load_rpg_data()
    data["hp"]["miler"]["atual"] = data["hp"]["miler"]["max"]
    data["users"]["123"]["mana"]["atual"] = data["users"]["123"]["mana"]["max"]
    data["statuses"] = {}
    save_rpg_data(data)
    
    loaded = load_rpg_data()
    assert loaded["hp"]["miler"]["atual"] == 20
    assert loaded["users"]["123"]["mana"]["atual"] == 20
    assert "miler" not in loaded["statuses"]
    
    print("✅ Testes de Mundo (Descanso) passaram!")

if __name__ == "__main__":
    test_world_logic()
