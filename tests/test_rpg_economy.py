import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.storage import load_rpg_data, save_rpg_data

def test_economy_logic():
    # Setup state
    test_data = {
        "party": {"gold": 200, "inventory": []},
        "pets": {}
    }
    save_rpg_data(test_data)
    
    # Teste Loja Comprar (Simula compra da Espada Longa, 150g)
    data = load_rpg_data()
    assert data["party"]["gold"] >= 150
    data["party"]["gold"] -= 150
    data["party"]["inventory"].append({"nome": "Espada Longa", "desc": "Corte", "peso": 1.5})
    save_rpg_data(data)
    
    loaded = load_rpg_data()
    assert loaded["party"]["gold"] == 50
    assert len(loaded["party"]["inventory"]) == 1
    assert loaded["party"]["inventory"][0]["nome"] == "Espada Longa"
    
    # Teste Pets
    data = load_rpg_data()
    pets = data.setdefault("pets", {})
    user_pets = pets.setdefault("miler", [])
    user_pets.append({"nome": "Rex", "especie": "Lobo", "hp": {"atual": 10, "max": 10}})
    save_rpg_data(data)
    
    loaded = load_rpg_data()
    assert len(loaded["pets"]["miler"]) == 1
    assert loaded["pets"]["miler"][0]["nome"] == "Rex"
    
    print("✅ Testes de Economia e Pets passaram!")

if __name__ == "__main__":
    test_economy_logic()
