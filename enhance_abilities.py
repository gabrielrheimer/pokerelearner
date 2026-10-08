"""
One-time enhancement: enrich data/snapshot/abilities_info.json with detailed
technical effect text from PokeAPI (https://pokeapi.co, open data / CC0-friendly).

This is NOT run by the app. Run it manually once:

    python enhance_abilities.py

It reads abilities_info.json, fetches each ability's English "effect" entry from
PokeAPI, and replaces the short in-game `description` with the detailed effect text.
Abilities not found on PokeAPI (custom ROM-hack abilities) keep their original
description. Progress is written incrementally and the script is resumable: entries
that already carry an `enhanced: true` flag are skipped on re-run.
"""
import json
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE = Path(__file__).parent
ABILITIES_FILE = BASE / "data/snapshot/abilities_info.json"
API = "https://pokeapi.co/api/v2/ability/{slug}"
DELAY_SECONDS = 0.3  # polite rate limit between requests


def slug_from_name(name: str) -> str:
    """Pikachu-style name -> PokeAPI slug, e.g. 'Speed Boost' -> 'speed-boost'."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def fetch_effect(slug: str) -> str | None:
    """Return the detailed English effect text for an ability slug, or None."""
    url = API.format(slug=slug)
    req = urllib.request.Request(url, headers={"User-Agent": "pokerelearner/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    for entry in data.get("effect_entries", []):
        if entry.get("language", {}).get("name") == "en":
            effect = entry.get("effect", "").strip()
            if effect:
                return re.sub(r"\s*\n\s*", " ", effect)
    # Fall back to short_effect if the long one is absent
    for entry in data.get("effect_entries", []):
        if entry.get("language", {}).get("name") == "en":
            short = entry.get("short_effect", "").strip()
            if short:
                return re.sub(r"\s*\n\s*", " ", short)
    return None


def main():
    if not ABILITIES_FILE.exists():
        print(f"ERROR: {ABILITIES_FILE} not found. Run `python parse_abilities.py` first.")
        return 1

    data = json.loads(ABILITIES_FILE.read_text())
    total = len(data)
    enhanced_count = sum(1 for v in data.values() if v.get("enhanced"))
    todo = [(k, v) for k, v in data.items() if not v.get("enhanced")]

    print(f"{total} abilities, {enhanced_count} already enhanced, {len(todo)} to fetch.")

    not_found = []
    for i, (ability_id, info) in enumerate(todo, 1):
        slug = slug_from_name(info["name"])
        effect = fetch_effect(slug)
        if effect:
            info["description"] = effect
            info["enhanced"] = True
            status = "ok"
        else:
            info["enhanced"] = True  # mark done so re-runs skip it; keep original desc
            not_found.append(info["name"])
            status = "not found (kept original)"
        print(f"  [{i}/{len(todo)}] {info['name']:<24} {status}")

        # Write incrementally so a crash/interrupt loses nothing.
        ABILITIES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        time.sleep(DELAY_SECONDS)

    print(f"\nDone. {len(todo) - len(not_found)} enhanced, {len(not_found)} kept original.")
    if not_found:
        print("Not on PokeAPI (likely custom abilities):")
        for name in not_found:
            print(f"  - {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
