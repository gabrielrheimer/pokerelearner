"""
pokerelearner — Level-up learnset editor for fire-red-repainted.
Streamlit UI: view original vs current moveset, edit, export gen_9.h patch.
"""
import json
import re
import copy
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = Path(__file__).parent
SNAPSHOT_LEARNSETS = BASE / "data/snapshot/gen_9_learnsets.json"
SNAPSHOT_MOVES = BASE / "data/snapshot/moves_info.json"
CURRENT_FILE = BASE / "data/current_learnsets.json"
REPO = BASE.parent / "fire-red-repainted"
GEN9_SOURCE = REPO / "src/data/pokemon/level_up_learnsets/gen_9.h"
OUTPUT_DIR = BASE / "output"

# ---------------------------------------------------------------------------
# Type colors (background, text)
# ---------------------------------------------------------------------------
TYPE_COLORS = {
    "Normal":   ("#A8A878", "#fff"),
    "Fighting": ("#C03028", "#fff"),
    "Flying":   ("#A890F0", "#fff"),
    "Poison":   ("#A040A0", "#fff"),
    "Ground":   ("#E0C068", "#333"),
    "Rock":     ("#B8A038", "#fff"),
    "Bug":      ("#A8B820", "#fff"),
    "Ghost":    ("#705898", "#fff"),
    "Steel":    ("#B8B8D0", "#333"),
    "Fire":     ("#F08030", "#fff"),
    "Water":    ("#6890F0", "#fff"),
    "Grass":    ("#78C850", "#fff"),
    "Electric": ("#F8D030", "#333"),
    "Psychic":  ("#F85888", "#fff"),
    "Ice":      ("#98D8D8", "#333"),
    "Dragon":   ("#7038F8", "#fff"),
    "Dark":     ("#705848", "#fff"),
    "Fairy":    ("#EE99AC", "#333"),
    "Stellar":  ("#40B5A5", "#fff"),
    "Mystery":  ("#68A090", "#fff"),
    "Unknown":  ("#888888", "#fff"),
}

CATEGORY_COLORS = {
    "Physical": ("#C92112", "#fff"),
    "Special":  ("#4459A6", "#fff"),
    "Status":   ("#888888", "#fff"),
}

CATEGORY_SHORT = {"Physical": "Phys", "Special": "Spec", "Status": "Stat"}

# ---------------------------------------------------------------------------
# Gen 1 + relevant Gen 2 evolutions — ordered by Pokédex number
# ---------------------------------------------------------------------------
POKEMON_LIST = [
    "Bulbasaur", "Ivysaur", "Venusaur",
    "Charmander", "Charmeleon", "Charizard",
    "Squirtle", "Wartortle", "Blastoise",
    "Caterpie", "Metapod", "Butterfree",
    "Weedle", "Kakuna", "Beedrill",
    "Pidgey", "Pidgeotto", "Pidgeot",
    "Rattata", "Raticate",
    "Spearow", "Fearow",
    "Ekans", "Arbok",
    "Pichu", "Pikachu", "Raichu",
    "Sandshrew", "Sandslash",
    "NidoranF", "Nidorina", "Nidoqueen",
    "NidoranM", "Nidorino", "Nidoking",
    "Cleffa", "Clefairy", "Clefable",
    "Vulpix", "Ninetales",
    "Igglybuff", "Jigglypuff", "Wigglytuff",
    "Zubat", "Golbat", "Crobat",
    "Oddish", "Gloom", "Vileplume", "Bellossom",
    "Paras", "Parasect",
    "Venonat", "Venomoth",
    "Diglett", "Dugtrio",
    "Meowth", "Persian",
    "Psyduck", "Golduck",
    "Mankey", "Primeape",
    "Growlithe", "Arcanine",
    "Poliwag", "Poliwhirl", "Poliwrath", "Politoed",
    "Abra", "Kadabra", "Alakazam",
    "Machop", "Machoke", "Machamp",
    "Bellsprout", "Weepinbell", "Victreebel",
    "Tentacool", "Tentacruel",
    "Geodude", "Graveler", "Golem",
    "Ponyta", "Rapidash",
    "Slowpoke", "Slowbro", "Slowking",
    "Magnemite", "Magneton",
    "Farfetchd",
    "Doduo", "Dodrio",
    "Seel", "Dewgong",
    "Grimer", "Muk",
    "Shellder", "Cloyster",
    "Gastly", "Haunter", "Gengar",
    "Onix", "Steelix",
    "Drowzee", "Hypno",
    "Krabby", "Kingler",
    "Voltorb", "Electrode",
    "Exeggcute", "Exeggutor",
    "Cubone", "Marowak",
    "Hitmonlee", "Hitmonchan", "Hitmontop",
    "Lickitung",
    "Koffing", "Weezing",
    "Rhyhorn", "Rhydon",
    "Chansey", "Blissey",
    "Tangela",
    "Kangaskhan",
    "Horsea", "Seadra", "Kingdra",
    "Goldeen", "Seaking",
    "Staryu", "Starmie",
    "MrMime",
    "Scyther", "Scizor",
    "Jynx",
    "Electabuzz",
    "Magmar",
    "Pinsir",
    "Tauros",
    "Magikarp", "Gyarados",
    "Lapras",
    "Ditto",
    "Eevee", "Vaporeon", "Jolteon", "Flareon", "Espeon", "Umbreon",
    "Porygon",
    "Omanyte", "Omastar",
    "Kabuto", "Kabutops",
    "Aerodactyl",
    "Togepi", "Togetic",
    "Snorlax",
    "Articuno", "Zapdos", "Moltres",
    "Dratini", "Dragonair", "Dragonite",
    "Mewtwo", "Mew",
    "Smoochum", "Elekid", "Magby",
]

# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------
@st.cache_data
def load_snapshot_learnsets() -> dict:
    if not SNAPSHOT_LEARNSETS.exists():
        return {}
    return json.loads(SNAPSHOT_LEARNSETS.read_text())


@st.cache_data
def load_moves_info() -> dict:
    if not SNAPSHOT_MOVES.exists():
        return {}
    return json.loads(SNAPSHOT_MOVES.read_text())


def load_current() -> dict:
    if CURRENT_FILE.exists():
        return json.loads(CURRENT_FILE.read_text())
    # Bootstrap from snapshot
    snapshot = load_snapshot_learnsets()
    return copy.deepcopy(snapshot)


def save_current(data: dict):
    CURRENT_FILE.parent.mkdir(parents=True, exist_ok=True)
    CURRENT_FILE.write_text(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# Export gen_9.h
# ---------------------------------------------------------------------------
def export_gen9(current: dict):
    if not GEN9_SOURCE.exists():
        st.error(f"Source not found: {GEN9_SOURCE}")
        return
    text = GEN9_SOURCE.read_text()

    def replace_block(name: str, moves: list, source_text: str) -> str:
        array_name = f"s{name}LevelUpLearnset"
        pattern = re.compile(
            rf"(static const struct LevelUpMove\s+{re.escape(array_name)}\[\]\s*=\s*\{{)"
            rf"[^}}]+"
            rf"\}};",
            re.DOTALL,
        )
        lines = [""]
        for entry in moves:
            lines.append(f"    LEVEL_UP_MOVE({entry['level']:2d}, {entry['move']}),")
        lines.append("    LEVEL_UP_END")
        lines.append("}")
        replacement = r"\1" + "\n".join(lines) + ";"
        return pattern.sub(replacement, source_text)

    for name, moves in current.items():
        text = replace_block(name, moves, text)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "gen_9.h"
    out_path.write_text(text)
    st.success(f"Exported to {out_path}")


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def type_badge(type_str: str) -> str:
    bg, fg = TYPE_COLORS.get(type_str, ("#888", "#fff"))
    return (
        f'<span style="background:{bg};color:{fg};padding:1px 6px;'
        f'border-radius:4px;font-size:0.78em;font-weight:bold;">{type_str}</span>'
    )


def cat_badge(cat_str: str) -> str:
    bg, fg = CATEGORY_COLORS.get(cat_str, ("#888", "#fff"))
    short = CATEGORY_SHORT.get(cat_str, cat_str[:4])
    return (
        f'<span style="background:{bg};color:{fg};padding:1px 6px;'
        f'border-radius:4px;font-size:0.78em;font-weight:bold;">{short}</span>'
    )


def move_row_html(entry: dict, moves_info: dict, highlight: bool = False) -> str:
    move_id = entry["move"]
    level = entry["level"]
    info = moves_info.get(move_id, {})
    name = info.get("name", move_id)
    type_str = info.get("type", "Unknown")
    cat_str = info.get("category", "Unknown")
    power = info.get("power", 0)
    accuracy = info.get("accuracy", 0)
    description = info.get("description", "")

    bg = "#fffde7" if highlight else "transparent"
    desc_row = (
        f'<tr style="background:{bg}">'
        f"<td></td>"
        f'<td colspan="5" style="font-size:0.78em;color:#888;padding-top:0;padding-bottom:4px">{description}</td>'
        f"</tr>"
    ) if description else ""
    return (
        f'<tr style="background:{bg}">'
        f"<td style='text-align:center;width:40px;vertical-align:top'>{level}</td>"
        f"<td style='width:120px'>{name}</td>"
        f"<td>{type_badge(type_str)}</td>"
        f"<td>{cat_badge(cat_str)}</td>"
        f"<td style='text-align:center'>{power if power else '—'}</td>"
        f"<td style='text-align:center'>{accuracy if accuracy else '—'}</td>"
        f"</tr>"
        f"{desc_row}"
    )


TABLE_HEADER = (
    "<table style='width:100%;border-collapse:collapse;font-size:0.88em'>"
    "<thead><tr style='border-bottom:1px solid #ccc'>"
    "<th>Lv</th><th>Move</th><th>Type</th><th>Cat</th><th>Pow</th><th>Acc</th>"
    "</tr></thead><tbody>"
)


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="pokerelearner", layout="wide")
    st.title("pokerelearner — Level-up Learnset Editor")

    if not SNAPSHOT_LEARNSETS.exists() or not SNAPSHOT_MOVES.exists():
        st.error("Snapshots not found. Run `make snapshot` first.")
        return

    snapshot = load_snapshot_learnsets()
    moves_info = load_moves_info()
    all_move_ids = sorted(moves_info.keys())

    # Session state: current learnsets + unsaved edits flag
    if "current" not in st.session_state:
        st.session_state.current = load_current()
    if "dirty" not in st.session_state:
        st.session_state.dirty = False

    # --- Pokémon selector ---
    available = [p for p in POKEMON_LIST if p in snapshot]
    selected = st.selectbox("Pokémon", available)

    original_moves = snapshot.get(selected, [])
    current_moves = st.session_state.current.get(selected, copy.deepcopy(original_moves))

    # Ensure current has an entry for this Pokémon
    if selected not in st.session_state.current:
        st.session_state.current[selected] = copy.deepcopy(original_moves)
        current_moves = st.session_state.current[selected]

    orig_set = [(e["level"], e["move"]) for e in original_moves]

    # --- Original vs Atual side by side ---
    col_orig, col_curr = st.columns(2)

    with col_orig:
        st.subheader("Original (snapshot)")
        rows = "".join(move_row_html(e, moves_info) for e in original_moves)
        st.markdown(TABLE_HEADER + rows + "</tbody></table>", unsafe_allow_html=True)

    with col_curr:
        st.subheader("Atual")
        rows_html = ""
        for entry in current_moves:
            is_changed = (entry["level"], entry["move"]) not in orig_set
            rows_html += move_row_html(entry, moves_info, highlight=is_changed)
        st.markdown(TABLE_HEADER + rows_html + "</tbody></table>", unsafe_allow_html=True)

    # --- Editable area below ---
    st.markdown("---")
    st.subheader("Editar moveset")

    def sync_edits():
        """Read all widget values and write directly into session state."""
        moves = st.session_state.current.get(selected, [])
        updated = []
        for i in range(len(moves)):
            lv_key = f"lv_{selected}_{i}"
            mv_key = f"mv_{selected}_{i}"
            if lv_key in st.session_state and mv_key in st.session_state:
                updated.append({
                    "level": st.session_state[lv_key],
                    "move": st.session_state[mv_key],
                })
        st.session_state.current[selected] = updated
        st.session_state.dirty = True

    rows_to_delete = []

    for i, entry in enumerate(current_moves):
        c_lv, c_move, c_del = st.columns([1, 4, 1])
        with c_lv:
            st.number_input(
                "Lv", min_value=0, max_value=100,
                value=entry["level"], key=f"lv_{selected}_{i}",
                label_visibility="collapsed",
                on_change=sync_edits,
            )
        with c_move:
            idx = all_move_ids.index(entry["move"]) if entry["move"] in all_move_ids else 0
            st.selectbox(
                "Move", all_move_ids, index=idx,
                key=f"mv_{selected}_{i}",
                label_visibility="collapsed",
                on_change=sync_edits,
            )
        with c_del:
            if st.button("✕", key=f"del_{selected}_{i}", help="Remover"):
                rows_to_delete.append(i)

    if rows_to_delete:
        updated = [e for i, e in enumerate(st.session_state.current[selected]) if i not in rows_to_delete]
        st.session_state.current[selected] = updated
        st.session_state.dirty = True
        st.rerun()

    if st.button("＋ Adicionar move"):
        st.session_state.current[selected].append({"level": 1, "move": "MOVE_TACKLE"})
        st.session_state.dirty = True
        st.rerun()

    # --- Save / Export ---
    st.markdown("---")
    c1, c2, c3 = st.columns([2, 2, 6])
    with c1:
        if st.button("💾 Salvar edições", disabled=not st.session_state.dirty):
            save_current(st.session_state.current)
            st.session_state.dirty = False
            st.success("Salvo em data/current_learnsets.json")

    with c2:
        if st.button("📤 Exportar gen_9.h"):
            export_gen9(st.session_state.current)

    if st.session_state.dirty:
        st.caption("⚠ Há alterações não salvas.")


if __name__ == "__main__":
    main()
