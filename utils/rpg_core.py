import os
import json

XP_TABLE = {
    1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500, 
    6: 14000, 7: 23000, 8: 34000, 9: 48000, 10: 64000
}

TABLES_FILE = "rpg_tables.json"

def load_rpg_tables():
    if os.path.exists(TABLES_FILE):
        try:
            with open(TABLES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"encounters": {}, "loot": {}, "facts": []}

def get_hp_bar(atual: int, maximo: int) -> str:
    """Retorna uma barra de progresso em emoji e a porcentagem."""
    if maximo <= 0:
        return "⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ (0/0) — 0%"
    size = 10
    filled = max(0, min(size, round((atual / maximo) * size)))
    bar = "🟩" * filled + "⬜" * (size - filled)
    percent = (atual / maximo) * 100
    return f"{bar} ({atual}/{maximo}) — {percent:.0f}%"
