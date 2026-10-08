"""
Parse abilities.h into data/snapshot/abilities_info.json.
Extracts: name, description for each ability.
Run once to create the immutable original snapshot.
"""
import re
import json
from pathlib import Path

REPO = Path(__file__).parent.parent / "fire-red-repainted"
SOURCE = REPO / "src/data/abilities.h"
OUT_DIR = Path(__file__).parent / "data/snapshot"
OUT_FILE = OUT_DIR / "abilities_info.json"

# Abilities excluded from the catalog (project does not use them). Also excluded:
# any ABILITY_EMBODY_ASPECT* (Ogerpon Tera-form, handled by prefix below).
EXCLUDE_ABILITIES = {
    "ABILITY_GULP_MISSILE", "ABILITY_ILLUMINATE", "ABILITY_PIERCING_DRILL",
    "ABILITY_POISON_PUPPETEER", "ABILITY_PRESSURE", "ABILITY_SLOW_START",
    "ABILITY_TERAFORM_ZERO", "ABILITY_FORECAST", "ABILITY_TERAVOLT",
    "ABILITY_TURBOBLAZE", "ABILITY_EELEVATE", "ABILITY_HONEY_GATHER",
    "ABILITY_ANTICIPATION", "ABILITY_COMMANDER", "ABILITY_FOREWARN",
    "ABILITY_SUPREME_OVERLORD", "ABILITY_SOUL_HEART", "ABILITY_UNSEEN_FIST",
    "ABILITY_MINDS_EYE",
    # Auras group
    "ABILITY_DARK_AURA", "ABILITY_FAIRY_AURA", "ABILITY_AURA_BREAK",
    "ABILITY_VESSEL_OF_RUIN", "ABILITY_SWORD_OF_RUIN", "ABILITY_TABLETS_OF_RUIN",
    # Form Change group
    "ABILITY_STANCE_CHANGE", "ABILITY_HUNGER_SWITCH",
}


def parse_abilities(source: Path) -> dict:
    text = source.read_text()

    # Split on ability entries: [ABILITY_XXX] = { ... },
    entry_pattern = re.compile(
        r"\[(\bABILITY_\w+\b)\]\s*=\s*\{([^[]+?)(?=\n\s*\[|\Z)",
        re.DOTALL,
    )

    result = {}
    for match in entry_pattern.finditer(text):
        ability_id = match.group(1)
        body = match.group(2)

        # Abilities the project does not use — excluded from the catalog entirely.
        if ability_id in EXCLUDE_ABILITIES or ability_id.startswith("ABILITY_EMBODY_ASPECT"):
            continue

        # Name: _("...")
        name_m = re.search(r'\.name\s*=\s*_\("([^"]*)"\)', body)
        name = name_m.group(1) if name_m else ability_id

        # Skip placeholder entries (e.g. "-", "-------")
        if name.strip("-") == "":
            continue

        # Description: COMPOUND_STRING("...") — may span multiple string literals
        desc_m = re.search(r'\.description\s*=\s*COMPOUND_STRING\((.*?)\)', body, re.DOTALL)
        if desc_m:
            parts = re.findall(r'"([^"]*)"', desc_m.group(1))
            description = " ".join(p for p in parts).replace(r"\n", " ").strip()
        else:
            description = ""

        result[ability_id] = {
            "name": name,
            "description": description,
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
    data = parse_abilities(SOURCE)
    OUT_FILE.write_text(json.dumps(data, indent=2))
    print(f"Snapshot written: {OUT_FILE}")
    print(f"  {len(data)} abilities parsed")


if __name__ == "__main__":
    main()
