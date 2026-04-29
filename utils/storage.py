import json
import os

RPG_DATA_FILE = "rpg_data.json"

def load_rpg_data():
    """Carrega os dados persistentes do RPG (fichas, macros, party, status, hp)."""
    if os.path.exists(RPG_DATA_FILE):
        try:
            with open(RPG_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Garante chaves básicas
                if "party" not in data:
                    data["party"] = {"gold": 0, "inventory": []}
                if "users" not in data:
                    data["users"] = {}
                if "hp" not in data:
                    data["hp"] = {}
                if "statuses" not in data:
                    data["statuses"] = {}
                return data
        except json.JSONDecodeError:
            pass
            
    return {
        "users": {}, 
        "party": {"gold": 0, "inventory": []},
        "hp": {},
        "statuses": {}
    }

def save_rpg_data(data):
    """Salva os dados persistentes do RPG no disco."""
    with open(RPG_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
