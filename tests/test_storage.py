import sys
import os
import json
# Adiciona o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.storage import load_rpg_data, save_rpg_data

def test_storage_cycle():
    # Cria dado de teste
    test_data = {
        "users": {"123": {"fichas": {"forca": 10}, "titles": ["Novato"]}},
        "party": {"gold": 500, "inventory": ["Espada"], "xp": 100, "level": 1},
        "hp": {"miler": {"atual": 20, "max": 20}},
        "statuses": {"miler": ["Bênção"]},
        "stats": {"crits": {"123": 5}}
    }
    
    # Salva
    save_rpg_data(test_data)
    
    # Carrega e compara
    loaded = load_rpg_data()
    assert loaded["users"]["123"]["fichas"]["forca"] == 10
    assert "Novato" in loaded["users"]["123"]["titles"]
    assert loaded["party"]["xp"] == 100
    assert loaded["stats"]["crits"]["123"] == 5
    assert loaded["party"]["gold"] == 500
    assert "Espada" in loaded["party"]["inventory"]
    assert loaded["hp"]["miler"]["atual"] == 20
    assert "Bênção" in loaded["statuses"]["miler"]
    
    print("✅ Teste de persistência passou!")

if __name__ == "__main__":
    test_storage_cycle()
