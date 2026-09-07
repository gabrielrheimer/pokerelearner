"""
Parse moves_info.h into data/snapshot/moves_info.json.
Extracts: name, type, category, power, accuracy, pp for each move.
Run once to create the immutable original snapshot.
"""
import re
import json
from pathlib import Path

REPO = Path(__file__).parent.parent / "fire-red-repainted"
SOURCE = REPO / "src/data/moves_info.h"
OUT_DIR = Path(__file__).parent / "data/snapshot"
OUT_FILE = OUT_DIR / "moves_info.json"

# Maps C constant → friendly string
TYPE_MAP = {
    "TYPE_NORMAL": "Normal", "TYPE_FIGHTING": "Fighting", "TYPE_FLYING": "Flying",
    "TYPE_POISON": "Poison", "TYPE_GROUND": "Ground", "TYPE_ROCK": "Rock",
    "TYPE_BUG": "Bug", "TYPE_GHOST": "Ghost", "TYPE_STEEL": "Steel",
    "TYPE_FIRE": "Fire", "TYPE_WATER": "Water", "TYPE_GRASS": "Grass",
    "TYPE_ELECTRIC": "Electric", "TYPE_PSYCHIC": "Psychic", "TYPE_ICE": "Ice",
    "TYPE_DRAGON": "Dragon", "TYPE_DARK": "Dark", "TYPE_FAIRY": "Fairy",
    "TYPE_STELLAR": "Stellar", "TYPE_MYSTERY": "Mystery",
}

CATEGORY_MAP = {
    "DAMAGE_CATEGORY_PHYSICAL": "Physical",
    "DAMAGE_CATEGORY_SPECIAL": "Special",
    "DAMAGE_CATEGORY_STATUS": "Status",
}


def first_int(text: str) -> int | None:
    """Return the first integer literal found in text, or None."""
    m = re.search(r"\b(\d+)\b", text)
    return int(m.group(1)) if m else None


def parse_moves(source: Path) -> dict:
    text = source.read_text()

    # Split on move entries: [MOVE_XXX] = { ... },
    entry_pattern = re.compile(
        r"\[(\bMOVE_\w+\b)\]\s*=\s*\{([^[]+?)(?=\n\s*\[|\Z)",
        re.DOTALL,
    )

    result = {}
    for match in entry_pattern.finditer(text):
        move_id = match.group(1)
        body = match.group(2)

        # Name: COMPOUND_STRING("...")
        name_m = re.search(r'\.name\s*=\s*COMPOUND_STRING\("([^"]+)"\)', body)
        name = name_m.group(1) if name_m else move_id

        # Description: COMPOUND_STRING("..." "...") — may span multiple lines/strings
        desc_m = re.search(r'\.description\s*=\s*COMPOUND_STRING\((.*?)\)', body, re.DOTALL)
        if desc_m:
            parts = re.findall(r'"([^"]*)"', desc_m.group(1))
            description = " ".join(p for p in parts).replace(r"\n", " ").strip()
        else:
            description = ""

        # Type — handle ternary: pick first TYPE_* found on the .type line
        type_m = re.search(r"\.type\s*=\s*.+?(TYPE_\w+)", body)
        type_val = type_m.group(1) if type_m else None
        type_str = TYPE_MAP.get(type_val, type_val) if type_val else "Unknown"

        # Category
        cat_m = re.search(r"\.category\s*=\s*(DAMAGE_CATEGORY_\w+)", body)
        cat_val = cat_m.group(1) if cat_m else None
        cat_str = CATEGORY_MAP.get(cat_val, cat_val) if cat_val else "Unknown"

        # Power — take first numeric value on the .power line (handles #if blocks)
        power_m = re.search(r"\.power\s*=\s*(.+?)(?:,|\n)", body)
        power = first_int(power_m.group(1)) if power_m else 0

        # Accuracy — same approach
        acc_m = re.search(r"\.accuracy\s*=\s*(.+?)(?:,|\n)", body)
        accuracy = first_int(acc_m.group(1)) if acc_m else 0

        # PP
        pp_m = re.search(r"\.pp\s*=\s*(\d+)", body)
        pp = int(pp_m.group(1)) if pp_m else 0

        result[move_id] = {
            "name": name,
            "description": description,
            "type": type_str,
            "type_id": type_val,
            "category": cat_str,
            "power": power or 0,
            "accuracy": accuracy or 0,
            "pp": pp,
        }

    return result


def main():
    if not SOURCE.exists():
        print(f"ERROR: Source file not found: {SOURCE}")
        return

    if OUT_FILE.exists():
        print(f"Snapshot already exists at {OUT_FILE}. Delete it manually to regenerate.")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = parse_moves(SOURCE)
    OUT_FILE.write_text(json.dumps(data, indent=2))
    print(f"Snapshot written: {OUT_FILE}")
    print(f"  {len(data)} moves parsed")


if __name__ == "__main__":
    main()
