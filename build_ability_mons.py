"""
One-time build: generate Pokémon menu icons + an ability→species mapping for the
Ability Catalog. NOT run by the app — run manually once (re-runnable):

    python build_ability_mons.py

Outputs (committed, read by app.py):
  - data/icons/<folder>.png   transparent 64x64 icon per species used by the catalog
  - data/snapshot/ability_mons.json   { ABILITY_ID: [ {name, icon, fallback?}, ... ] }

For each ability shown in the catalog, the species list is built in two tiers:
  1. Relevant species — the project's curated set (POKEMON_LIST in app.py), shown normally.
  2. Fallback — only when NO relevant species has the ability: up to 3 species from any
     generation (so signature/form abilities aren't blank), flagged "fallback": true.

Icons come from the fire-red-repainted decomp: each species entry names an .iconSprite
symbol, resolved via src/data/graphics/pokemon.h to a real PNG path. The PNG is a 32x64
indexed image (two stacked 32x32 frames); we crop the top frame, make the background
(palette index 0) transparent, and upscale x2 for crisp display.
"""
import json
import re
from pathlib import Path

from PIL import Image

BASE = Path(__file__).parent
REPO = BASE.parent / "fire-red-repainted"
FAMILIES_DIR = REPO / "src/data/pokemon/species_info"
POKEMON_GFX_H = REPO / "src/data/graphics/pokemon.h"
GFX_ROOT = REPO

ABILITIES_FILE = BASE / "data/snapshot/abilities_info.json"
APP_FILE = BASE / "app.py"
ICON_OUT = BASE / "data/icons"
MONS_OUT = BASE / "data/snapshot/ability_mons.json"

FALLBACK_LIMIT = 3

# Display-name (POKEMON_LIST) → SPECIES constant suffix for the few irregular spellings.
SPECIAL_SPECIES = {
    "NidoranF": "NIDORAN_F", "NidoranM": "NIDORAN_M",
    "MrMime": "MR_MIME", "Farfetchd": "FARFETCHD",
}


def load_pokemon_list() -> list:
    """Read POKEMON_LIST (the curated 170) straight from app.py, in order."""
    src = APP_FILE.read_text()
    body = re.search(r"POKEMON_LIST\s*=\s*\[(.*?)\]", src, re.DOTALL).group(1)
    return re.findall(r'"([^"]+)"', body)


def display_to_species(name: str) -> str:
    return SPECIAL_SPECIES.get(name, name.upper())


def load_icon_paths() -> dict:
    """Map iconSprite symbol (gMonIcon_X) → PNG path relative to the repo root."""
    text = POKEMON_GFX_H.read_text()
    paths = {}
    for sym, rel in re.findall(
        r'(gMonIcon_\w+)\[\]\s*=\s*INCGFX_U8\("([^"]+)"', text
    ):
        paths[sym] = rel
    return paths


def parse_species_entries() -> list:
    """Return [(species_id, [ability_ids], species_name, icon_symbol)] for all base entries."""
    text = ""
    for f in sorted(FAMILIES_DIR.glob("gen_*_families.h")):
        text += f.read_text()
    entries = []
    for sid, body in re.findall(
        r"\[SPECIES_([A-Z0-9_]+)\]\s*=\s*\{(.*?)\n    \},", text, re.DOTALL
    ):
        am = re.search(r"\.abilities\s*=\s*\{([^}]*)\}", body)
        if not am:
            continue
        abilities = [
            a.strip() for a in am.group(1).split(",")
            if a.strip() and a.strip() != "ABILITY_NONE"
        ]
        nm = re.search(r'\.speciesName\s*=\s*_\("([^"]*)"\)', body)
        name = nm.group(1) if nm else sid
        im = re.search(r"\.iconSprite\s*=\s*(gMonIcon_\w+)", body)
        icon_sym = im.group(1) if im else None
        entries.append((sid, abilities, name, icon_sym))
    return entries


def make_icon(src_png: Path, out_png: Path):
    """Crop top 32x32 frame, key out the background color, upscale x2 → save RGBA PNG."""
    im = Image.open(src_png)
    pal = im.getpalette()
    bg_idx = im.getpixel((0, 0))  # top-left of frame 0 is background
    bg_rgb = tuple(pal[bg_idx * 3: bg_idx * 3 + 3]) if pal else (0, 0, 0)
    top = im.crop((0, 0, 32, 32)).convert("RGBA")
    datas = []
    for r, g, b, a in top.getdata():
        datas.append((r, g, b, 0) if (r, g, b) == bg_rgb else (r, g, b, a))
    top.putdata(datas)
    top = top.resize((64, 64), Image.NEAREST)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    top.save(out_png)


def icon_slug(icon_sym: str, icon_paths: dict) -> str | None:
    """A stable filename slug for an icon symbol, e.g. gMonIcon_PinsirMega → pinsir_mega."""
    rel = icon_paths.get(icon_sym)
    if not rel:
        return None
    # rel like graphics/pokemon/pinsir/mega/icon.png → pinsir_mega
    parts = Path(rel).parts
    try:
        i = parts.index("pokemon")
    except ValueError:
        return None
    sub = parts[i + 1:-1]  # drop 'icon.png'
    return "_".join(sub) if sub else None


def main():
    pokemon_list = load_pokemon_list()
    relevant_sids = {display_to_species(n): n for n in pokemon_list}
    order = {display_to_species(n): i for i, n in enumerate(pokemon_list)}

    icon_paths = load_icon_paths()
    entries = parse_species_entries()
    catalog = json.loads(ABILITIES_FILE.read_text())

    # ability_id → list of relevant species records; and → list of any-gen records (fallback)
    relevant = {aid: [] for aid in catalog}
    anygen = {aid: [] for aid in catalog}

    icons_needed = {}  # slug → source PNG Path

    def record(sid, name, icon_sym):
        rel = icon_paths.get(icon_sym)
        if not rel:
            return None
        slug = icon_slug(icon_sym, icon_paths)
        src = GFX_ROOT / rel
        if not src.exists():
            return None
        icons_needed[slug] = src
        return {"name": name, "icon": slug}

    for sid, abilities, name, icon_sym in entries:
        is_relevant = sid in relevant_sids
        for aid in dict.fromkeys(abilities):  # de-dup, keep order
            if aid not in catalog:
                continue
            if is_relevant:
                rec = record(sid, relevant_sids[sid], icon_sym)
                if rec:
                    relevant[aid].append((order[sid], rec))
            else:
                if len(anygen[aid]) < 50:  # cap collection; we only need 3 later
                    rec = record(sid, name, icon_sym)
                    if rec:
                        anygen[aid].append(rec)

    # Assemble final mapping
    result = {}
    for aid in catalog:
        rel_sorted = [rec for _, rec in sorted(relevant[aid], key=lambda x: x[0])]
        rel, seen = [], set()
        for rec in rel_sorted:
            key = (rec["name"], rec["icon"])
            if key not in seen:
                seen.add(key)
                rel.append(rec)
        if rel:
            result[aid] = rel
        else:
            fb = []
            seen = set()
            for rec in anygen[aid]:
                if rec["name"] in seen:  # dedup by display name (forms share a name)
                    continue
                seen.add(rec["name"])
                fb.append({**rec, "fallback": True})
                if len(fb) >= FALLBACK_LIMIT:
                    break
            result[aid] = fb

    # Generate the icons actually referenced in the result
    used_slugs = {m["icon"] for mons in result.values() for m in mons}
    ICON_OUT.mkdir(parents=True, exist_ok=True)
    made = 0
    for slug in sorted(used_slugs):
        src = icons_needed.get(slug)
        if not src:
            continue
        make_icon(src, ICON_OUT / f"{slug}.png")
        made += 1

    MONS_OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    with_relevant = sum(1 for a in result if result[a] and not result[a][0].get("fallback"))
    with_fallback = sum(1 for a in result if result[a] and result[a][0].get("fallback"))
    empty = sum(1 for a in result if not result[a])
    print(f"Wrote {MONS_OUT.name}: {len(result)} abilities")
    print(f"  {with_relevant} with relevant mons, {with_fallback} fallback-only, {empty} empty")
    print(f"Generated {made} icons → {ICON_OUT}")


if __name__ == "__main__":
    main()
