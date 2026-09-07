"""
Parse gen_9.h level-up learnsets into data/snapshot/gen_9_learnsets.json.
Run once to create the immutable original snapshot.
"""
import re
import json
import os
from pathlib import Path

REPO = Path(__file__).parent.parent / "fire-red-repainted"
SOURCE = REPO / "src/data/pokemon/level_up_learnsets/gen_9.h"
OUT_DIR = Path(__file__).parent / "data/snapshot"
OUT_FILE = OUT_DIR / "gen_9_learnsets.json"


def parse_learnsets(source: Path) -> dict:
    text = source.read_text()

    # Match each learnset block: s{Name}LevelUpLearnset[] = { ... };
    block_pattern = re.compile(
        r"static const struct LevelUpMove\s+s(\w+)LevelUpLearnset\[\]\s*=\s*\{([^}]+)\};",
        re.DOTALL,
    )
    move_pattern = re.compile(r"LEVEL_UP_MOVE\(\s*(\d+)\s*,\s*(MOVE_\w+)\s*\)")

    result = {}
    for match in block_pattern.finditer(text):
        name = match.group(1)
        body = match.group(2)
        moves = []
        for m in move_pattern.finditer(body):
            moves.append({"level": int(m.group(1)), "move": m.group(2)})
        if moves:
            result[name] = moves

    return result


def main():
    if not SOURCE.exists():
        print(f"ERROR: Source file not found: {SOURCE}")
        return

    if OUT_FILE.exists():
        print(f"Snapshot already exists at {OUT_FILE}. Delete it manually to regenerate.")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = parse_learnsets(SOURCE)
    OUT_FILE.write_text(json.dumps(data, indent=2))
    print(f"Snapshot written: {OUT_FILE}")
    print(f"  {len(data)} Pokémon parsed")


if __name__ == "__main__":
    main()
