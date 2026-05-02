import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.storage import load_rpg_data, save_rpg_data

def test_advanced_logic():
    # Setup state
    test_data = {
        "party": {"gold": 100, "inventory": []},
        "faccoes": {"Ladrões": 0},
        "doom_clock": 10,
        "bestiario": {},
        "lore": {}
    }
    save_rpg_data(test_data)
    
    # Teste Facções
    data = load_rpg_data()
    data["faccoes"]["Ladrões"] += 5
    save_rpg_data(data)
    
    loaded = load_rpg_data()
    assert loaded["faccoes"]["Ladrões"] == 5
    
    # Teste Doom Clock (não passar de 12)
    data = load_rpg_data()
    data["doom_clock"] = max(0, min(12, data["doom_clock"] + 5))
    save_rpg_data(data)
    
    loaded = load_rpg_data()
    assert loaded["doom_clock"] == 12
    
    # Teste Bestiário & Lore
    data = load_rpg_data()
    data["bestiario"]["goblin"] = {"nome": "Goblin", "fraqueza": "Fogo", "descricao": "Pequeno."}
    data["lore"]["fundacao"] = {"titulo": "Fundacao", "conteudo": "Aconteceu há muito tempo."}
    save_rpg_data(data)
    
    loaded = load_rpg_data()
    assert "goblin" in loaded["bestiario"]
    assert loaded["lore"]["fundacao"]["titulo"] == "Fundacao"
    
    print("✅ Testes do RPG Avançado (Fase 3) passaram!")

if __name__ == "__main__":
    test_advanced_logic()
