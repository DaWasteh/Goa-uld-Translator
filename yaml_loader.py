#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  GOA'ULD YAML LEXICON LOADER                                         ║
║  Loads goauld_lexicon.yaml → flat entry list compatible with the     ║
║  existing SearchEngine.                                              ║
╚══════════════════════════════════════════════════════════════════════╝

Drop-in usage inside goauld_translator.py:

    from yaml_loader import load_lexicon_yaml, LEXICON_YAML_CANDIDATES

    # Replace the old _load_mds() call with:
    yaml_path = find_lexicon_yaml()
    if yaml_path:
        entries, de_goauld_map, en_goauld_map, secondary_de, secondary_en = \\
            load_lexicon_yaml(yaml_path)
    else:
        entries, paths = _load_mds()       # old fallback

The loader produces entries with the exact same shape the existing
SearchEngine expects ({goauld, meaning, section, source, lang, ...}),
plus a small set of extra maps the app can use for:

  • de_goauld_map / en_goauld_map  — primary O(1) reverse lookup
  • secondary_de / secondary_en    — "auch:" alternative suggestions for
                                      polysemous words (canon wins primary,
                                      fanon/abydonian get listed as secondary)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml

log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────
# FILE DISCOVERY
# ──────────────────────────────────────────────────────────────────────────

LEXICON_YAML_CANDIDATES = (
    "goauld_lexicon.yaml",
    "goauld_lexicon.yml",
)


def find_lexicon_yaml(hint: Optional[str] = None,
                      search_dirs: Optional[list] = None) -> Optional[str]:
    """
    Locate goauld_lexicon.yaml. Search order:
      1. Explicit hint path (if provided and exists)
      2. Each directory in search_dirs (if provided)
      3. Current working directory
      4. Directory of the translator script (alongside the .py or the .exe)
    Returns absolute path string, or None if not found.
    """
    if hint:
        p = Path(hint)
        if p.is_file():
            return str(p.resolve())

    dirs: list[Path] = []
    if search_dirs:
        dirs.extend(Path(d) for d in search_dirs)
    dirs.append(Path.cwd())
    dirs.append(Path(__file__).parent)

    for d in dirs:
        for name in LEXICON_YAML_CANDIDATES:
            p = d / name
            if p.is_file():
                return str(p.resolve())
    return None


# ──────────────────────────────────────────────────────────────────────────
# REGISTER / TIER → SEARCH-ENGINE SOURCE STRING
# ──────────────────────────────────────────────────────────────────────────
# The existing SearchEngine uses a flat 'source' string to rank entries.
# We map YAML tiers to source strings the engine already recognizes, so
# the priority logic works unchanged. Canon tiers → 'Kanon' (high),
# Fanon tiers → 'Fanon' (medium), abydonian → 'Kanon-ext' (medium-high).

_TIER_TO_SOURCE = {
    "canon_series":     "SG1-Kanon",       # priority 3
    "canon_film":       "Kanon",           # priority 3
    "canon_guide":      "Kanon",           # priority 3
    "canon_rpg":        "RPG-Lexikon",     # priority 2
    "canon_game":       "Kanon-ext",       # priority 2
    "canon_rda":        "Kanon-ext",       # priority 2
    "abydonian":        "Kanon-ext",       # priority 2
    "fanon_strict":     "Fanon",           # priority 2
    "fanon_derived":    "Fanon",           # priority 2
    "fanon_synonym":    "Fanon",           # priority 2
    "user_contributed": "Gap-Fill",        # priority 2
}


# ──────────────────────────────────────────────────────────────────────────
# MAIN LOADER
# ──────────────────────────────────────────────────────────────────────────

def load_lexicon_yaml(yaml_path: str) -> tuple[list[dict], dict, dict,
                                                dict, dict]:
    """
    Load goauld_lexicon.yaml and expand it into the flat entry list
    the SearchEngine consumes, plus four reverse-lookup maps.

    Returns:
        entries          — list[dict], each {goauld, meaning, section,
                                             source, lang, register,
                                             priority, auto_filled, ...}
        de_goauld_map    — dict[str, str]  primary DE→Goa'uld lookup
                                            (highest-priority key wins)
        en_goauld_map    — dict[str, str]  primary EN→Goa'uld lookup
        secondary_de     — dict[str, list[str]]  alternatives for polysemous
                                                  DE words (excluding primary)
        secondary_en     — dict[str, list[str]]  same for EN
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "entries" not in data:
        raise ValueError(f"{yaml_path} has no 'entries' section")

    raw_entries = data["entries"]
    flat_entries: list[dict] = []

    # Per-gloss-language tracker so we can build primary + secondary maps:
    #   gloss_lower → list[(priority, goauld_term)]
    de_candidates: dict[str, list[tuple[int, str]]] = {}
    en_candidates: dict[str, list[tuple[int, str]]] = {}

    for key, entry in raw_entries.items():
        term = entry.get("term", key)
        register = entry.get("register", "fanon")
        priority = int(entry.get("priority", 0))

        for sense in entry.get("senses", []):
            category = sense.get("category") or "Uncategorized"
            pos = sense.get("pos")
            context = sense.get("context")
            source_info = sense.get("source", {}) or {}
            tier = source_info.get("tier", "fanon_derived")
            engine_source = _TIER_TO_SOURCE.get(tier, "Fanon")
            sense_priority = int(sense.get("priority", priority))
            glosses = sense.get("glosses", {}) or {}

            # Emit a flat entry per (language, gloss) pair.
            # The engine deduplicates by (goauld_lower, meaning_lower).
            for lang in ("de", "en"):
                for gloss in glosses.get(lang, []) or []:
                    flat_entries.append({
                        "goauld":   term,
                        "meaning":  gloss,
                        "section":  category,
                        "source":   engine_source,
                        "lang":     lang,
                        "pos":      pos,
                        "register": register,
                        "priority": sense_priority,
                        "tier":     tier,
                        "context":  context,
                        "auto_filled": sense.get("auto_filled") or [],
                    })
                    # Track for reverse map
                    target = de_candidates if lang == "de" else en_candidates
                    target.setdefault(gloss.lower().strip(), []).append(
                        (sense_priority, term)
                    )

    # Build primary + secondary maps
    de_map, secondary_de = _build_primary_secondary(de_candidates)
    en_map, secondary_en = _build_primary_secondary(en_candidates)

    log.info(
        "YAML lexicon loaded: %d flat entries  ·  DE primary=%d secondary-bearing=%d  "
        "·  EN primary=%d secondary-bearing=%d",
        len(flat_entries), len(de_map),
        sum(1 for v in secondary_de.values() if v),
        len(en_map),
        sum(1 for v in secondary_en.values() if v),
    )

    return flat_entries, de_map, en_map, secondary_de, secondary_en


def _build_primary_secondary(
    candidates: dict[str, list[tuple[int, str]]]
) -> tuple[dict[str, str], dict[str, list[str]]]:
    """
    For each gloss, pick the highest-priority Goa'uld term as the primary
    hit, and collect all other unique terms as secondary alternatives.
    """
    primary: dict[str, str] = {}
    secondary: dict[str, list[str]] = {}

    for gloss, cand_list in candidates.items():
        # Sort by priority DESC, then term ascending for stability
        sorted_cands = sorted(cand_list, key=lambda t: (-t[0], t[1]))
        # Dedupe while preserving order
        seen = set()
        ordered_unique_terms = []
        for _prio, term in sorted_cands:
            if term not in seen:
                seen.add(term)
                ordered_unique_terms.append(term)

        if not ordered_unique_terms:
            continue
        primary[gloss] = ordered_unique_terms[0]
        if len(ordered_unique_terms) > 1:
            secondary[gloss] = ordered_unique_terms[1:]

    return primary, secondary


# ──────────────────────────────────────────────────────────────────────────
# STANDALONE TEST
# ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO,
                        format="[%(levelname)s] %(message)s")

    yaml_path = sys.argv[1] if len(sys.argv) > 1 else find_lexicon_yaml()
    if not yaml_path:
        print("No goauld_lexicon.yaml found.", file=sys.stderr)
        sys.exit(1)

    entries, de_map, en_map, sec_de, sec_en = load_lexicon_yaml(yaml_path)

    print(f"\n  Total flat entries : {len(entries):,}")
    print(f"  DE→Goa'uld map     : {len(de_map):,}")
    print(f"  EN→Goa'uld map     : {len(en_map):,}")

    # Check well-known words
    print("\nPrimary lookups:")
    for probe in ("mensch", "krieger", "tapfer", "schnell", "befehl",
                  "human", "warrior", "brave", "fast", "command"):
        lookup_map = de_map if probe in de_map else en_map
        hit = lookup_map.get(probe, "—")
        sec_map = sec_de if probe in de_map else sec_en
        alts = sec_map.get(probe, [])
        alts_str = f"   (auch: {', '.join(alts[:3])})" if alts else ""
        print(f"  {probe!r:<14} → {hit!r}{alts_str}")
