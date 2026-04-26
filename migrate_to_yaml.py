#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  GOA'ULD LEXICON MIGRATION                                           ║
║  Consolidates 4 Markdown dictionaries → 1 unified YAML lexicon       ║
║  + extracts prose sections into LANGUAGE_GUIDE_{DE,EN}.md            ║
╚══════════════════════════════════════════════════════════════════════╝

Usage:
    python migrate_to_yaml.py --input-dir /path/to/mds --output-dir /path/to/output

Output:
    goauld_lexicon.yaml         — unified lexicon (Source of Truth for the app)
    LANGUAGE_GUIDE_DE.md        — German prose/lore sections
    LANGUAGE_GUIDE_EN.md        — English prose/lore sections
    migration_report.txt        — dedup stats, conflicts, unparseable rows
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ──────────────────────────────────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("migrate")


# ──────────────────────────────────────────────────────────────────────────
# SOURCE-FILE METADATA
# ──────────────────────────────────────────────────────────────────────────
# filename_glob → (register_default, gloss_lang, display_name)
SOURCE_META = {
    "Dictionary":  ("canon", "en", "Dictionary"),
    "Wörterbuch":  ("canon", "de", "Wörterbuch"),
    "Worterbuch":  ("canon", "de", "Wörterbuch"),   # ASCII variant
    "Fictionary":  ("fanon", "en", "Fictionary"),
    "Neologikum":  ("fanon", "de", "Neologikum"),
}


# ──────────────────────────────────────────────────────────────────────────
# PRIORITY / TIER ASSIGNMENT
# ──────────────────────────────────────────────────────────────────────────
# An 11-tier ranking system that decides which source "wins" in DE/EN→Goa'uld
# lookups when multiple Goa'uld terms gloss the same target word.
TIER_PRIORITY = {
    "canon_series":     100,  # SG-1 TV episodes — highest authority
    "canon_film":        95,  # 1994 Stargate film
    "canon_guide":       90,  # Ultimate Visual Guide
    "canon_rpg":         85,  # SG-1 Roleplaying Game + sourcebooks
    "canon_game":        80,  # Unleashed mobile game
    "canon_rda":         75,  # Richard Dean Anderson website dictionaries
    "abydonian":         70,  # Abydonian dialect (distinct but canon-adjacent)
    "fanon_strict":      60,  # Fictionary/Neologikum w/ full etymology chain
    "fanon_derived":     50,  # Fanon with partial/inferred derivation
    "fanon_synonym":     40,  # Pure synonym-expansion in reverse maps
    "user_contributed":  30,  # Future PRs, unreviewed
}

# Heuristic patterns to classify canon entries by their "Source / Episode" column
# Priority order matters: check specific→general.
_TIER_HEURISTICS = [
    # (regex, tier)
    (re.compile(r"Ultimate\s+Visual\s+Guide|UVG",            re.I), "canon_guide"),
    (re.compile(r"RPG|Rollenspiel|Sourcebook|Quellenbuch",   re.I), "canon_rpg"),
    (re.compile(r"Unleashed",                                re.I), "canon_game"),
    (re.compile(r"Film|1994|Kinofilm",                       re.I), "canon_film"),
    (re.compile(r"RDA|Richard\s+Dean\s+Anderson",            re.I), "canon_rda"),
    # Quoted episode title is the strongest signal for canon_series
    (re.compile(r"[\"„][^\"„“]+[\"“]"),                             "canon_series"),
    (re.compile(r"SGCommand|StargateWiki|GateWorld|Omnipedia",
                                                             re.I), "canon_rda"),
    (re.compile(r"Maj\s*C|Arduinna",                         re.I), "canon_rda"),
    (re.compile(r"Ägyptisch|Egyptian|Mythologie|mythology",  re.I), "canon_guide"),
]


def classify_canon_tier(meta_cell: str) -> str:
    """Map a 'Source/Episode' cell to one of the canon tiers."""
    if not meta_cell:
        return "canon_series"  # default when no metadata present
    for rx, tier in _TIER_HEURISTICS:
        if rx.search(meta_cell):
            return tier
    # Fallback: episode-like content usually has quotes or mixed caps
    return "canon_series"


# ──────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────
@dataclass
class RawSense:
    """One raw row extracted from a Markdown table, pre-merge."""
    goauld_raw: str            # as-written from the table, e.g. "Kree!"
    gloss_raw: str             # the 'Meaning/Bedeutung' cell content
    meta_raw: str              # the 3rd column (source/episode/derivation/category)
    section: str               # MD section header (semantic category)
    gloss_lang: str            # 'de' or 'en'
    table_type: str            # 'forward' or 'reverse'
    source_file: str           # filename
    register: str              # 'canon' | 'fanon' | 'abydonian'
    tier: str                  # one of TIER_PRIORITY keys


# ──────────────────────────────────────────────────────────────────────────
# KEY NORMALIZATION
# ──────────────────────────────────────────────────────────────────────────
def normalize_key(term: str) -> str:
    """Canonical lookup key: lowercase, apostrophes preserved, whitespace collapsed."""
    if not term:
        return ""
    # Strip bold markers, asterisks, trailing punctuation that's not part of the word
    s = term.strip()
    s = re.sub(r"^\*+|\*+$", "", s)          # remove leading/trailing *
    s = s.strip()
    # Normalize typographic apostrophes to ASCII '
    s = (s.replace("\u2019", "'")  # right single
           .replace("\u2018", "'")  # left single
           .replace("\u02bc", "'")  # modifier letter apostrophe
           .replace("`", "'"))
    # Normalize typographic double quotes to ASCII "
    # (so `„tac"` and `"tac"` produce the same key)
    s = (s.replace("\u201c", '"')  # left double
           .replace("\u201d", '"')  # right double
           .replace("\u201e", '"')  # German double low-9
           .replace("\u201f", '"')  # double high-reversed-9
           .replace("\u00ab", '"')  # «
           .replace("\u00bb", '"'))  # »
    s = s.lower()
    # Collapse internal whitespace
    s = re.sub(r"\s+", " ", s)
    # Strip trailing bang/question (they're stylistic, e.g. "Kree!")
    s = s.rstrip("!?.,;:")
    return s.strip()


def display_form(term: str) -> str:
    """Clean display form — strip markdown, preserve original casing."""
    s = term.strip()
    s = re.sub(r"^\*+|\*+$", "", s)
    s = s.strip()
    # Normalize typographic quotes for consistent display
    s = (s.replace("\u2019", "'")
           .replace("\u2018", "'")
           .replace("\u02bc", "'")
           .replace("\u201c", '"')
           .replace("\u201d", '"')
           .replace("\u201e", '"'))
    return s


# ──────────────────────────────────────────────────────────────────────────
# MARKDOWN PARSER
# ──────────────────────────────────────────────────────────────────────────

# Regex: a markdown table row with exactly 3 cells (most common schema)
_ROW_3COL = re.compile(r"^\s*\|([^|]+)\|([^|]+)\|([^|]+)\|\s*$")
# Regex: 2-col row (Kree-phrase section)
_ROW_2COL = re.compile(r"^\s*\|([^|]+)\|([^|]+)\|\s*$")
# Regex: separator line (| --- | --- | ---)
_SEPARATOR = re.compile(r"^\s*\|[\s:\-]+\|[\s:\-]+(\|[\s:\-]+)?\|\s*$")
# Regex: header line
_H2 = re.compile(r"^##\s+(.+?)\s*$")


def _is_table_header(cells: list[str]) -> bool:
    """Heuristic: are all cells short and non-bolded? (header rows don't have **...**)"""
    if not cells:
        return False
    joined = " ".join(cells).lower()
    # Header cells never contain bold markers or too many commas
    if "**" in joined:
        return False
    # Header cells are short
    return all(len(c.strip()) < 30 for c in cells)


def _classify_table(header_cells: list[str], section: str,
                    register: str, gloss_lang: str) -> tuple[str, int, int]:
    """
    Given a table header, return (table_type, goauld_col, gloss_col).

    table_type ∈ {'forward', 'reverse', 'abydonian'}
      - forward: Goa'uld is in col 0, gloss in col 1, meta in col 2
      - reverse: Language is in col 0, Goa'uld in col 1, category in col 2
      - abydonian: like forward, but register='abydonian'
    """
    cells = [c.strip().lower() for c in header_cells]
    col0 = cells[0] if cells else ""

    # Reverse-map tables
    if col0 in ("deutsch", "english"):
        return "reverse", 1, 0  # goauld@1, gloss@0

    # Abydonian dialect has its own column header
    if col0 in ("abydonisch", "abydonian"):
        return "abydonian", 0, 1

    # Everything else = forward (Goa'uld/Phrase/etc. in col 0)
    return "forward", 0, 1


def parse_markdown(path: Path) -> tuple[list[RawSense], list[str]]:
    """
    Parse a dictionary MD file. Returns (raw_senses, prose_lines).
    prose_lines = all non-table, non-header content for the language guide.
    """
    # Figure out source metadata from filename
    stem = path.stem
    source_key = next((k for k in SOURCE_META if k in stem), None)
    if not source_key:
        raise ValueError(f"Unknown source file pattern: {path.name}")
    register_default, gloss_lang, display_name = SOURCE_META[source_key]

    log.info("Parsing %s  (register=%s, lang=%s)", path.name, register_default, gloss_lang)

    raw_senses: list[RawSense] = []
    prose_lines: list[str] = []

    current_section = "Uncategorized"
    in_table = False
    table_header: Optional[list[str]] = None
    table_type = "forward"
    goauld_col = 0
    gloss_col = 1
    override_register: Optional[str] = None  # for abydonian sub-sections

    lines = path.read_text(encoding="utf-8").splitlines()

    for i, raw_line in enumerate(lines):
        line = raw_line.rstrip()

        # Section header
        m = _H2.match(line)
        if m:
            current_section = m.group(1).strip()
            in_table = False
            table_header = None
            override_register = None
            # Detect abydonian sections by header keyword
            low = current_section.lower()
            if "abydon" in low:
                override_register = "abydonian"
            # Don't emit section headers as prose — they're navigation
            continue

        # Table separator line = we just saw a header
        if _SEPARATOR.match(line):
            if table_header is not None:
                eff_register = override_register or register_default
                table_type, goauld_col, gloss_col = _classify_table(
                    table_header, current_section, eff_register, gloss_lang
                )
                in_table = True
            continue

        # Table row?
        m3 = _ROW_3COL.match(line)
        m2 = _ROW_2COL.match(line) if not m3 else None
        row_cells: Optional[list[str]] = None
        if m3:
            row_cells = [m3.group(1), m3.group(2), m3.group(3)]
        elif m2:
            row_cells = [m2.group(1), m2.group(2), ""]  # 2-col: treat 3rd as empty

        if row_cells is not None:
            cells_stripped = [c.strip() for c in row_cells]
            # First row after a blank-to-pipe transition is the header
            if not in_table:
                if _is_table_header(cells_stripped):
                    table_header = cells_stripped
                # else: orphan row with no header — skip quietly
                continue

            # Data row — extract
            try:
                goauld_cell = cells_stripped[goauld_col]
                gloss_cell = cells_stripped[gloss_col]
                # meta cell = whichever of 0,1,2 is not goauld or gloss
                remaining = [k for k in (0, 1, 2) if k not in (goauld_col, gloss_col)]
                meta_cell = cells_stripped[remaining[0]] if remaining else ""
            except IndexError:
                continue

            if not goauld_cell or not gloss_cell:
                continue

            # Determine register for this row
            effective_register = override_register or register_default

            # Tier assignment
            if effective_register == "abydonian":
                tier = "abydonian"
            elif effective_register == "canon":
                if table_type == "reverse":
                    tier = "canon_rda"  # reverse maps are curated but not primary canon
                else:
                    tier = classify_canon_tier(meta_cell)
            else:  # fanon
                if table_type == "reverse":
                    tier = "fanon_synonym"
                else:
                    # Check if meta cell contains a real derivation
                    # (has "+", or starts with italic, or mentions "kanonisch")
                    if meta_cell and (
                        "+" in meta_cell
                        or "kanonisch" in meta_cell.lower()
                        or "canonical" in meta_cell.lower()
                        or re.search(r"\*[^*]+\*", meta_cell)
                    ):
                        tier = "fanon_strict"
                    else:
                        tier = "fanon_derived"

            raw_senses.append(RawSense(
                goauld_raw=goauld_cell,
                gloss_raw=gloss_cell,
                meta_raw=meta_cell,
                section=current_section,
                gloss_lang=gloss_lang,
                table_type=table_type,
                source_file=path.name,
                register=effective_register,
                tier=tier,
            ))
            continue

        # Non-table, non-header → prose
        if line.strip() and not line.startswith("|"):
            prose_lines.append(raw_line)
            in_table = False
            table_header = None
        elif line.strip() == "":
            # Empty line breaks table context
            prose_lines.append(raw_line)
            in_table = False
            table_header = None

    log.info("  extracted %d raw senses from %s", len(raw_senses), path.name)
    return raw_senses, prose_lines


# ──────────────────────────────────────────────────────────────────────────
# CELL-CONTENT SPLITTERS
# ──────────────────────────────────────────────────────────────────────────

def split_variants(goauld_cell: str) -> list[str]:
    """
    A Goa'uld cell may list alternate spellings separated by slash:
      'Na-nay / Ne'nai'         → ['Na-nay', 'Ne'nai']
      'Hok'tar / Hok'taur'      → ['Hok'tar', 'Hok'taur']
      'Ring kol nok / Rin'kal'noc' → ['Ring kol nok', "Rin'kal'noc"]
    """
    # Strip bold markers first
    s = re.sub(r"\*\*", "", goauld_cell).strip()
    # Split on standalone slash (not inside words)
    parts = re.split(r"\s*/\s*", s)
    # Filter empties & dedupe preserving order
    seen = set()
    out = []
    for p in parts:
        p = p.strip().strip("*").strip()
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def split_glosses(gloss_cell: str) -> list[str]:
    """
    Split a gloss cell into individual meanings.
    Canonical rows often have: "attention, listen, concentrate — context-dependent particle"
    Fanon rows often have:     "To hate, To despise, Hate"
    """
    s = gloss_cell.strip()
    # Remove surrounding bold/italic markers
    s = re.sub(r"^\*+|\*+$", "", s).strip()
    # Strip typographic quotes to normal quotes
    s = s.replace("„", '"').replace("\u201c", '"').replace("\u201d", '"')

    # Split on "em-dash" / "en-dash" / " - " → everything after is context, not a gloss
    split_ctx = re.split(r"\s+[—–−]\s+|\s+-\s+", s, maxsplit=1)
    head = split_ctx[0]

    # Parenthetical asides — keep them attached to the preceding gloss
    # (we don't split inside parentheses)
    # Split head on commas and semicolons, BUT not inside parentheses or quotes
    out = []
    buf = ""
    depth = 0
    in_quote = False
    for ch in head:
        if ch == '"':
            in_quote = not in_quote
            buf += ch
        elif ch in "([":
            depth += 1
            buf += ch
        elif ch in ")]":
            depth = max(0, depth - 1)
            buf += ch
        elif ch in ",;" and depth == 0 and not in_quote:
            if buf.strip():
                out.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        out.append(buf.strip())

    # Final cleanup
    cleaned = []
    for g in out:
        g = g.strip().strip('"').strip()
        # Strip trailing dots
        g = g.rstrip(".")
        if not g:
            continue
        # ── Slang/approx patterns: extract quoted core word ──
        # 'Slang for "human" (from Tau'ri)' → 'human'
        # 'Slang für "Mensch" (von Tau'ri)'  → 'Mensch'
        # 'Trespasser, defiler (approximate)' — handled by comma-split earlier
        slang_match = re.match(
            r"^slang\s+(?:for|für)\s+[\"\u201c\u201e]?([^\"\u201c\u201d\u201e)]+?)"
            r"[\"\u201c\u201d]?(?:\s*\([^)]*\))?\s*$",
            g, re.IGNORECASE)
        if slang_match:
            extracted = slang_match.group(1).strip().strip('"').strip()
            if extracted:
                cleaned.append(extracted)
                continue
        # ── "X (Y)" pattern: keep only X if Y is an etymology/source note ──
        # 'Trespasser (approximate)' → 'Trespasser'
        # 'Mother (honorific)' → 'Mother'
        # But keep 'Ear(s)' style → handled below via paren_match
        etym_match = re.match(
            r"^(.+?)\s*\((?:approximate|approximately|ungefähr|ungefähre|von\s|from\s|see\s|siehe\s|lit\.?\s|wörtlich|literally|honorific|ehrend|archaic|archaisch)[^)]*\)\s*$",
            g, re.IGNORECASE)
        if etym_match:
            cleaned.append(etym_match.group(1).strip())
            continue
        # ── Expand parenthetical number/plural variants: "Ear(s)" → ["Ear", "Ears"]
        paren_match = re.match(r"^(\w+?)\(([a-zA-Z]+)\)$", g)
        if paren_match:
            base = paren_match.group(1)
            suffix = paren_match.group(2)
            cleaned.append(base)
            cleaned.append(base + suffix)
        else:
            cleaned.append(g)
    return cleaned if cleaned else [s]  # fallback: keep whole cell


def classify_pos(section: str, category: str, gloss_lang: str) -> Optional[str]:
    """
    Infer part-of-speech from section header or reverse-map category column.
    Returns English POS label (noun/verb/adjective/...) or None.
    """
    if not section and not category:
        return None
    text = f"{section} {category}".lower()

    pos_map = [
        (r"pronomen|pronoun",                  "pronoun"),
        (r"hilfsverb|auxiliary",               "auxiliary"),
        (r"basisverb|^verb|verben|verb$",      "verb"),
        (r"adjektiv|adjective|descriptor",     "adjective"),
        (r"demonstrativ",                      "demonstrative"),
        (r"fragewort|interrogative",           "interrogative"),
        (r"verneinung|negation",               "negation"),
        (r"bejahung|affirmation",              "affirmation"),
        (r"zahl|number|quantifier",            "numeral"),
        (r"präposition|preposition|konjunktion|conjunction",
                                               "preposition"),
        (r"höflichkeit|politeness",            "interjection"),
        (r"interjektion|interjection|ausruf",  "interjection"),
        (r"begrüß|greeting|farewell|abschied", "interjection"),
        (r"befehl|command|imperativ",          "verb"),
        (r"phrase|dialog",                     "phrase"),
    ]
    for rx, pos in pos_map:
        if re.search(rx, text):
            return pos
    # If section mentions body-parts, tech, etc. → noun
    noun_hints = (
        "körperteil", "body", "tech", "technolog", "waffe", "weapon",
        "titel", "rank", "family", "familie", "kinship", "verwand",
        "farbe", "color", "geography", "animal", "tier", "food",
        "nahrung", "clothing", "kleidung", "architektur", "architecture",
        "rolle", "person",
    )
    if any(h in text for h in noun_hints):
        return "noun"
    return None


# ──────────────────────────────────────────────────────────────────────────
# MERGE RAW SENSES INTO UNIFIED ENTRIES
# ──────────────────────────────────────────────────────────────────────────
REGISTER_RANK = {"canon": 3, "abydonian": 2, "fanon": 1}


def build_lexicon(all_raw: list[RawSense]) -> tuple[dict, list[dict]]:
    """
    Merge raw senses by normalized key. Returns (entries_dict, conflict_list).
    """
    # Step 1: group by normalized key
    groups: dict[str, list[tuple[str, RawSense]]] = defaultdict(list)
    # Each tuple = (this_specific_goauld_variant, raw_sense)

    for rs in all_raw:
        for variant in split_variants(rs.goauld_raw):
            key = normalize_key(variant)
            if not key:
                continue
            groups[key].append((variant, rs))

    log.info("Merging %d raw senses into %d unique keys", len(all_raw), len(groups))

    entries: dict[str, dict] = {}
    for key, group in groups.items():
        entries[key] = _build_single_entry(key, group)

    # Step 2: conflict detection (DE/EN target → multiple Goa'uld terms)
    conflicts = _detect_conflicts(entries)

    return entries, conflicts


def _build_single_entry(key: str, group: list[tuple[str, RawSense]]) -> dict:
    """Build one unified entry from all raw senses sharing the same key."""
    # Determine canonical display form: prefer canon-source's rendering
    display = None
    variants_seen: list[str] = []
    for variant, rs in group:
        d = display_form(variant)
        if d not in variants_seen:
            variants_seen.append(d)
        if display is None and rs.register == "canon" and rs.table_type == "forward":
            display = d
    if display is None:
        display = variants_seen[0]

    # Determine register: max over all raw senses
    registers = [rs.register for _, rs in group]
    if "canon" in registers:
        register = "canon"
    elif "abydonian" in registers:
        register = "abydonian"
    else:
        register = "fanon"

    # Determine priority (numeric) = max tier value across all raw senses
    max_tier = max(group, key=lambda t: TIER_PRIORITY.get(t[1].tier, 0))[1].tier
    priority = TIER_PRIORITY[max_tier]

    # Morphology inference
    morphology = _infer_morphology(key, display, group)

    # Build senses: group by (pos, primary_gloss_set) to merge duplicates across lang
    senses = _build_senses(key, group)

    # xref: extract component keys from morphology
    xref = sorted(set(morphology.get("components") or [])) if morphology.get("components") else []

    # compounds_in: will be filled in a second pass after all entries exist
    entry = {
        "term": display,
        "variants": [v for v in variants_seen if v != display],  # only alts
        "register": register,
        "priority": priority,
        "morphology": morphology,
        "senses": senses,
        "xref": xref,
        "compounds_in": [],  # populated post-hoc
    }
    return entry


def _infer_morphology(key: str, display: str, group: list[tuple[str, RawSense]]) -> dict:
    """Detect root vs. compound from apostrophe structure + derivation notes."""
    # Apostrophes in a single-word term → compound
    # Multi-word phrases (space-separated) → phrase
    if " " in key:
        return {"type": "phrase", "components": None, "derivation": None}

    has_apostrophe = "'" in key
    # Collect any derivation note from fanon meta cells
    derivation_note = None
    for _, rs in group:
        if rs.register == "fanon" and rs.table_type == "forward" and rs.meta_raw:
            derivation_note = rs.meta_raw.strip()
            break

    if has_apostrophe:
        parts = [p for p in key.split("'") if p]
        return {
            "type": "compound",
            "components": parts,
            "derivation": derivation_note,
        }

    return {"type": "root", "components": None, "derivation": derivation_note}


def _build_senses(key: str, group: list[tuple[str, RawSense]]) -> list[dict]:
    """
    Build sense objects. Strategy:
    - One sense per distinct (section_category, tier) combination
    - Glosses of the same language are merged into a list
    - Different languages populate different sub-keys of glosses
    """
    # Bucket by a "sense fingerprint" = (section-normalized, source_file)
    # This keeps Canon and Fanon senses separate even when they'd merge glosses.
    buckets: dict[tuple, dict] = defaultdict(
        lambda: {
            "pos": None,
            "category": None,
            "glosses": {"de": [], "en": []},
            "contexts": [],
            "sources": [],
            "tier": None,
            "priority": 0,
        }
    )

    for _variant, rs in group:
        # The "category" for a sense = section header simplified, or meta
        # (for reverse-map entries, meta IS the category)
        if rs.table_type in ("reverse", "abydonian"):
            category = rs.meta_raw or rs.section
        else:
            category = rs.section

        # Normalize the section name a bit for grouping
        bucket_key = (rs.register, category.lower().strip())
        b = buckets[bucket_key]

        # POS
        if not b["pos"]:
            b["pos"] = classify_pos(rs.section, rs.meta_raw, rs.gloss_lang)
        # Category
        if not b["category"]:
            b["category"] = category

        # Split glosses
        glosses = split_glosses(rs.gloss_raw)
        for g in glosses:
            if not g:
                continue
            # Case-insensitive dedup: skip if we already have this gloss
            # in any casing. Prefer whichever variant arrives first.
            existing_lower = {x.lower() for x in b["glosses"][rs.gloss_lang]}
            if g.lower() not in existing_lower:
                b["glosses"][rs.gloss_lang].append(g)

        # Context (portion after em-dash in the gloss cell)
        split_ctx = re.split(r"\s+[—–−]\s+|\s+-\s+", rs.gloss_raw.strip(), maxsplit=1)
        if len(split_ctx) > 1:
            ctx = split_ctx[1].strip().strip('"').strip()
            if ctx and ctx not in b["contexts"]:
                b["contexts"].append(ctx)

        # Source
        src = {
            "file": rs.source_file,
            "ref": rs.meta_raw if rs.table_type == "forward" else None,
            "tier": rs.tier,
        }
        b["sources"].append(src)

        # Tier tracking — keep the highest-priority tier
        rs_prio = TIER_PRIORITY.get(rs.tier, 0)
        if rs_prio > b["priority"]:
            b["priority"] = rs_prio
            b["tier"] = rs.tier

    # Convert buckets into ordered sense list, highest-priority first
    senses: list[dict] = []
    sense_id = 1
    for _, b in sorted(buckets.items(), key=lambda kv: -kv[1]["priority"]):
        # Skip buckets that have zero glosses in both languages (shouldn't happen)
        if not b["glosses"]["de"] and not b["glosses"]["en"]:
            continue
        sense = {
            "id": sense_id,
            "pos": b["pos"],
            "category": b["category"],
            "glosses": {
                lang: lst for lang, lst in b["glosses"].items() if lst
            },
            "context": b["contexts"][0] if b["contexts"] else None,
            "source": {
                "tier": b["tier"],
                "ref": b["sources"][0]["ref"] if b["sources"] else None,
                "files": sorted(set(s["file"] for s in b["sources"])),
            },
            "priority": b["priority"],
        }
        senses.append(sense)
        sense_id += 1
    return senses


def _detect_conflicts(entries: dict) -> list[dict]:
    """
    Find cases where one DE/EN target gloss maps to multiple Goa'uld keys,
    especially across registers (canon vs fanon).
    """
    # reverse_idx[lang][gloss_lower] → list of (key, priority, register)
    reverse_idx: dict[str, dict[str, list]] = {"de": defaultdict(list),
                                               "en": defaultdict(list)}

    for key, entry in entries.items():
        for sense in entry["senses"]:
            for lang, glosses in sense["glosses"].items():
                for g in glosses:
                    reverse_idx[lang][g.lower().strip()].append(
                        (key, sense["priority"], entry["register"])
                    )

    conflicts = []
    for lang, idx in reverse_idx.items():
        for gloss, raw_candidates in idx.items():
            # Collapse per-key: keep only the highest-priority occurrence per Goa'uld term
            by_key: dict[str, tuple[int, str]] = {}
            for k, p, r in raw_candidates:
                if k not in by_key or p > by_key[k][0]:
                    by_key[k] = (p, r)
            candidates = [(k, p, r) for k, (p, r) in by_key.items()]

            if len(candidates) < 2:
                continue
            registers = set(r for _, _, r in candidates)
            if len(registers) < 2:
                continue  # all same register — not really a conflict worth flagging
            # Sort by priority desc
            sorted_cands = sorted(candidates, key=lambda t: -t[1])
            conflicts.append({
                "lang": lang,
                "gloss": gloss,
                "candidates": [
                    {"key": k, "priority": p, "register": r}
                    for k, p, r in sorted_cands
                ],
            })
    return conflicts


def populate_compounds_in(entries: dict) -> None:
    """Second pass: for each entry, find compound keys that include it as a component."""
    key_to_compounds: dict[str, list[str]] = defaultdict(list)
    for key, entry in entries.items():
        comps = entry["morphology"].get("components")
        if comps:
            for c in comps:
                if c and c != key:
                    key_to_compounds[c].append(key)
    for key, entry in entries.items():
        compounds = sorted(set(key_to_compounds.get(key, [])))
        entry["compounds_in"] = compounds


def cross_sense_dedupe(entries: dict) -> int:
    """
    Post-merge pass: within each entry, drop glosses that already appear
    in an earlier sense (case-insensitive). If a sense ends up with zero
    glosses in all languages, drop the sense entirely.
    Returns number of glosses removed.
    """
    removed = 0
    for entry in entries.values():
        senses = entry.get("senses") or []
        seen_lower: dict[str, set] = {"de": set(), "en": set()}
        new_senses = []
        for s in senses:
            kept_any = False
            for lang in ("de", "en"):
                lst = s["glosses"].get(lang, []) or []
                kept = []
                for g in lst:
                    gl = g.lower().strip()
                    if gl in seen_lower[lang]:
                        removed += 1
                    else:
                        seen_lower[lang].add(gl)
                        kept.append(g)
                s["glosses"][lang] = kept
                if kept:
                    kept_any = True
            if kept_any:
                new_senses.append(s)
        # Renumber sense IDs
        for i, s in enumerate(new_senses, start=1):
            s["id"] = i
        entry["senses"] = new_senses
    return removed


# ──────────────────────────────────────────────────────────────────────────
# CROSS-LANGUAGE BRIDGE — auto-fill missing DE/EN translations
# ──────────────────────────────────────────────────────────────────────────
# Strategy: if Goa'uld-term X appears in both a DE reverse-map AND an EN
# reverse-map (across ANY of the four source files), then the DE-gloss and
# EN-gloss are mutual translation equivalents. We harvest these pairs into
# a global equivalence table, then use it to fill gaps in other entries.

def build_translation_bridge(entries: dict) -> tuple[dict, dict]:
    """
    Scan all entries. For every entry whose glosses span BOTH languages
    (across any of its senses), register each DE↔EN pair as a translation
    equivalence. Aggregating at the entry-level (not sense-level) captures
    the many cases where EN and DE live in separately-named sections —
    e.g. 'Core vocabulary' (EN) vs 'Kernvokabular' (DE).
    """
    de_to_en: dict[str, set] = defaultdict(set)
    en_to_de: dict[str, set] = defaultdict(set)

    for entry in entries.values():
        # Aggregate across all senses of this entry
        all_de = set()
        all_en = set()
        for sense in entry["senses"]:
            for g in sense["glosses"].get("de", []):
                all_de.add(g.lower().strip())
            for g in sense["glosses"].get("en", []):
                all_en.add(g.lower().strip())
        if all_de and all_en:
            for d in all_de:
                for e in all_en:
                    de_to_en[d].add(e)
                    en_to_de[e].add(d)

    return dict(de_to_en), dict(en_to_de)


def _lookup_translation(gloss: str, bridge: dict, manual: dict) -> list:
    """
    Look up a gloss in the translation tables. On miss, try splitting
    slash-separated variants like 'Tooth / teeth' and translating each part.
    Returns a list of found translations (possibly empty).
    """
    gl = gloss.lower().strip()
    hits: list[str] = []
    # Direct lookup first
    for src_dict in (bridge, manual):
        for t in (src_dict.get(gl) or ()):
            if t not in hits:
                hits.append(t)
    if hits:
        return hits

    # Slash-split fallback: "Ear(s)" already handled in split_glosses;
    # here we handle phrase-level slashes: "Tooth / teeth", "What? / What is happening?"
    if "/" in gl:
        parts = [p.strip() for p in gl.split("/") if p.strip()]
        translated_parts: list[str] = []
        for part in parts:
            part_hits = []
            for src_dict in (bridge, manual):
                for t in (src_dict.get(part) or ()):
                    if t not in part_hits:
                        part_hits.append(t)
            if part_hits:
                translated_parts.append(part_hits[0])  # pick first translation
        if translated_parts:
            # Return individually + a joined form
            for p in translated_parts:
                if p not in hits:
                    hits.append(p)
    return hits


def fill_language_gaps(entries: dict) -> tuple[int, int, list[str]]:
    """
    For each sense that has glosses in only ONE language, try to fill the other.

    Two strategies (in order):
    1. Cross-bridge: lookup the existing gloss in the harvested DE↔EN table.
    2. Fallback: MANUAL_DE_EN / MANUAL_EN_DE table for frequent words.
    3. Slash-split fallback: for phrases like 'Tooth / teeth', translate parts.

    Returns (filled_count, unfilled_count, unfilled_examples).
    """
    de_to_en, en_to_de = build_translation_bridge(entries)
    log.info("Translation bridge: %d DE→EN pairs, %d EN→DE pairs",
             len(de_to_en), len(en_to_de))

    filled = 0
    unfilled = 0
    unfilled_samples: list[str] = []

    for key, entry in entries.items():
        for sense in entry["senses"]:
            de_gl = sense["glosses"].get("de", [])
            en_gl = sense["glosses"].get("en", [])

            # Case: DE present, EN missing → fill EN
            if de_gl and not en_gl:
                added = []
                for d in de_gl:
                    hits = _lookup_translation(d, de_to_en, MANUAL_DE_EN)
                    for h in hits:
                        if h not in added:
                            added.append(h)
                if added:
                    sense["glosses"]["en"] = added
                    sense["auto_filled"] = sense.get("auto_filled", []) + ["en"]
                    filled += 1
                else:
                    unfilled += 1
                    if len(unfilled_samples) < 30:
                        unfilled_samples.append(f"{key}  [de→en]  {de_gl}")

            # Case: EN present, DE missing → fill DE
            elif en_gl and not de_gl:
                added = []
                for e in en_gl:
                    hits = _lookup_translation(e, en_to_de, MANUAL_EN_DE)
                    for h in hits:
                        if h not in added:
                            added.append(h)
                if added:
                    sense["glosses"]["de"] = added
                    sense["auto_filled"] = sense.get("auto_filled", []) + ["de"]
                    filled += 1
                else:
                    unfilled += 1
                    if len(unfilled_samples) < 30:
                        unfilled_samples.append(f"{key}  [en→de]  {en_gl}")

    return filled, unfilled, unfilled_samples


# Manual DE↔EN mapping for words not covered by the cross-Goa'uld bridge.
# Curated from the actual corpus of monolingual glosses identified during
# migration. Extend this dict as new entries reveal new gaps.
MANUAL_DE_EN = {
    # ── Pronouns / function words ─────────────────────────────────────
    "ich": ("I",), "du": ("you",),
    "er": ("he",), "sie": ("she", "they"), "es": ("it",),
    "wir": ("we",), "ihr": ("you all",),
    "er / sie / es": ("he / she / it",),
    "sie / ihnen": ("they / them",),
    "dies": ("this",), "dies (nah)": ("this (near)",),
    "das": ("that",), "jenes (fern)": ("that (far)",),
    "wer?": ("who?",), "wer": ("who",),
    "was?": ("what?",), "was passiert?": ("what is happening?",),
    "wo?": ("where?",), "wohin?": ("whither?",), "wo": ("where",),
    "wie?": ("how?",), "in welchem zustand?": ("in what condition?",),
    "wie": ("how",),
    "bin": ("am",), "bist": ("are",), "ist": ("is",), "sind": ("are",),
    # ── Body parts ────────────────────────────────────────────────────
    "arm": ("arm",), "bein": ("leg",), "fuß": ("foot",),
    "hand": ("hand",), "kopf": ("head",), "herz": ("heart",),
    "mund": ("mouth",), "nase": ("nose",), "auge": ("eye",),
    "augen": ("eyes",), "ohr": ("ear",), "ohren": ("ears",),
    "zahn": ("tooth",), "zähne": ("teeth",),
    "haut": ("skin",), "haar": ("hair",), "blut": ("blood",),
    "knochen": ("bone",), "fleisch": ("flesh", "meat"),
    "bauch": ("belly", "stomach"), "magen": ("stomach",),
    "horn": ("horn",), "stoßzahn": ("tusk",),
    # ── Nature ─────────────────────────────────────────────────────────
    "asche": ("ash",), "glut": ("cinder",),
    "rinde": ("bark",), "äußere schale": ("outer shell",),
    "vogel": ("bird",), "fisch": ("fish",),
    "baum": ("tree",), "blatt": ("leaf",),
    "wurzel": ("root",), "samen": ("seed",),
    "ei": ("egg",),
    "tag": ("day", "daytime"),
    "nacht": ("night",), "dunkelheit": ("darkness",),
    "sonne": ("sun",), "mond": ("moon",),
    "stern": ("star",), "lichtpunkt": ("point of light",),
    "berg": ("mountain",), "gipfel": ("peak",),
    "erde": ("earth",), "boden": ("ground",), "sand": ("sand",),
    "stein": ("stone",), "fels": ("rock",),
    "ozean": ("ocean",), "meer": ("sea",),
    "wasser": ("water",),
    "eis": ("ice",), "schnee": ("snow",),
    "regen": ("rain",), "wind": ("wind",), "sturm": ("storm",),
    "blitz": ("lightning",),
    "laus": ("louse",), "parasit": ("parasite",), "ungeziefer": ("pest",),
    # ── Adjectives ────────────────────────────────────────────────────
    "groß": ("big", "great", "large"),
    "klein": ("small", "little"), "gering": ("minor",),
    "lang": ("long",), "kurz": ("short",),
    "weich": ("soft",), "biegsam": ("pliable",),
    "heiß": ("hot",), "kalt": ("cold",),
    "dunkel": ("dark",), "lichtlos": ("lightless",),
    "tot": ("dead",), "leblos": ("lifeless",),
    "lebendig": ("alive",),
    "voll": ("full",), "vollständig": ("complete",),
    "neu": ("new",), "frisch": ("fresh",), "jung": ("young",),
    "alt": ("old",), "antik": ("ancient",), "verwittert": ("weathered",),
    "tapfer": ("brave", "courageous", "fearless"),
    # ── Verbs ─────────────────────────────────────────────────────────
    "beißen": ("to bite", "bite"),
    "bauen": ("to build", "build"), "erschaffen": ("to create", "create"),
    "brennen": ("to burn", "burn"), "verbrennen": ("to burn",),
    "zerstören": ("to destroy", "destroy"),
    "fliegen": ("to fly", "fly"),
    "geben": ("to give", "give"), "nehmen": ("to take", "take"),
    "wachsen": ("to grow", "grow"), "entwickeln": ("to develop",),
    "erinnern": ("to remember", "remember", "to recall"),
    "schlafen": ("to sleep", "sleep"),
    "stehen": ("to stand", "stand"), "standhaft sein": ("to stand firm",),
    "schwimmen": ("to swim", "swim"),
    "denken": ("to think", "think"), "überlegen": ("to reason",),
    "berühren": ("to touch", "touch"), "handhaben": ("to handle",),
    "gehen": ("to walk", "walk"), "laufen": ("walk",),
    "voranschreiten": ("to proceed",),
    "fühlen": ("to feel", "feel"),
    "wissen": ("to know", "know", "knowledge"),
    "kennen": ("to know",),
    "sterben": ("to die",), "töten": ("to kill",),
    "leben": ("to live",), "kämpfen": ("to fight",),
    "kommen": ("to come",),
    "hören": ("to hear", "listen"), "sprechen": ("to speak",),
    "sehen": ("to see",), "warten": ("to wait",),
    "reisen": ("to travel",), "aufbrechen": ("to depart",),
    "losziehen": ("to set out", "depart"),
    "gehorchen": ("to obey",),
    "bewahren": ("to preserve",),
    "kaufen": ("to buy", "purchase"),
    "erwerben": ("to acquire",),
    "handeln": ("to trade", "act"),
    "fortsetzen": ("continue", "resume"),
    "weitermachen": ("to continue",),
    "abmelden": ("log off", "sign off"),
    # ── Numbers ───────────────────────────────────────────────────────
    "eins": ("one",), "zwei": ("two",), "drei": ("three",),
    "vier": ("four",), "fünf": ("five",),
    "alle": ("all", "every"), "jeder": ("every",), "gesamt": ("whole",),
    "viele": ("many",), "zahlreich": ("numerous",),
    "wenige": ("few",), "eine handvoll": ("a handful",),
    # ── Persons / kinship / social ────────────────────────────────────
    "mann": ("man",), "erwachsener mann": ("adult male",),
    "männlich": ("male",),
    "frau": ("woman",), "erwachsene frau": ("adult female",),
    "weiblich": ("female",),
    "meister": ("master",), "diener": ("servant",),
    "krieger": ("warrior",), "feind": ("enemy",),
    "freund": ("friend",), "verräter": ("traitor",),
    "gott": ("god",), "gottheit": ("deity",),
    "ahne": ("ancestor", "forebear"), "vorfahre": ("ancestor",),
    "assassine": ("assassin",), "mörder": ("killer", "murderer"),
    "rebell": ("rebel",), "widerstandskämpfer": ("resistance fighter",),
    "händler": ("trader", "merchant"), "kaufmann": ("merchant", "trader"),
    "navigator": ("navigator",), "pilot": ("pilot",),
    "steuermann": ("helmsman",),
    # ── Abstracts ─────────────────────────────────────────────────────
    "ehre": ("honor",), "trinkspruch": ("toast",),
    "zum wohl": ("cheers",),
    "verzeihung": ("pardon", "forgiveness"), "abschied": ("farewell",),
    "höflichkeit": ("politeness",),
    "verstanden": ("understood",), "gerechtigkeit": ("justice",),
    "wahrheit": ("truth",), "ordnung": ("order",),
    "schönheit": ("beauty",), "chaos": ("chaos",),
    "eindringling": ("intruder", "trespasser"),
    "frei": ("free",), "freiheit": ("freedom",),
    "mutig": ("brave",), "stark": ("strong",), "schwach": ("weak",),
    "gut": ("good",), "böse": ("evil",),
    "wahr": ("true",), "falsch": ("false",),
    "halt": ("halt", "stop"), "stopp": ("stop",),
    "achtung": ("attention",), "vielleicht": ("maybe", "perhaps"),
    "seele": ("soul",),
    "anfang": ("beginning",),
    "name": ("name",),
    "allianz": ("alliance",), "bund": ("alliance", "covenant"),
    "erfolg": ("success",), "misserfolg": ("failure",),
    "richtiges ergebnis": ("correct result",),
    "fehler": ("error",), "fehler (ergebnis)": ("error (result)",),
    "gefahr": ("danger",), "bedrohung": ("threat",),
    "tödliche bedrohung": ("lethal threat",),
    "warnung": ("warning",), "warnsignal": ("warning signal",),
    "alarm": ("alarm",),
    "sklaverei": ("slavery",), "gefangenschaft": ("captivity",),
    "bann": ("exile", "banishment"),
    "gegenwart": ("present",), "dieser moment": ("this moment",),
    # ── Special: replaced-by-specialization ────────────────────────────
    "beeile dich": ("hurry up",),
    "ich sterbe frei": ("i die free",),
    # ── Interrogative phrases with punctuation ─────────────────────────
    "how? / in what condition?": ("wie? / in welchem zustand?",),
    "where? / whither?": ("wo? / wohin?",),
    "what? / what is happening?": ("was? / was passiert?",),
    # ── Technology ────────────────────────────────────────────────────
    "computer": ("computer",), "rechner": ("computer",),
    "rechenanlage": ("computing device",),
    "daten": ("data",), "digitales wissen": ("digital knowledge",),
    "bildschirm": ("screen", "display"),
    "display": ("display", "screen"),
    "monitor": ("monitor",),
    "passwort": ("password",), "zugangsschlüssel": ("access key",),
    "zugangscode": ("access code",),
    "netzwerk": ("network",), "verbindung": ("connection",),
    "verbindungsnetz": ("communication network",),
    "speicher": ("storage", "memory"), "archiv": ("archive",),
    "roboter": ("robot",), "drohne": ("drone",),
    "maschine": ("machine",),
    "ende der übertragung": ("end of transmission",),
    # ── Astronomy / space ─────────────────────────────────────────────
    "himmelskörper": ("celestial body",),
    "meteor": ("meteor",),
    "fallender stern": ("shooting star", "falling star"),
    # ── Jaffa-specific lore (keep as-is, compound translations) ───────
    "automatische ferngesteuerte zielsuchende waffe":
        ("automatic remote heat-seeking weapon",),
    "säure für folter": ("acid used for torture",),
    "hochzeitsnacht-ritual mit einer scharfen klinge":
        ("wedding night ritual involving a sharp blade",),
    "ein jaffa-gebäck/dessert": ("a jaffa food/dessert",),
}

# Auto-build reverse mapping from DE→EN
MANUAL_EN_DE: dict[str, tuple] = {}
for _de, _en_tup in MANUAL_DE_EN.items():
    for _en in _en_tup:
        k = _en.lower()
        existing = MANUAL_EN_DE.get(k, tuple())
        if _de not in existing:
            MANUAL_EN_DE[k] = existing + (_de,)


# ──────────────────────────────────────────────────────────────────────────
# PER-SENSE MANUAL TRANSLATIONS
# ──────────────────────────────────────────────────────────────────────────
# After cross_sense_dedupe + fill_language_gaps, a small residue of senses
# remains monolingual because their glosses are either (a) complex phrases
# the Bridge can't match as single tokens, or (b) meanings that genuinely
# don't exist elsewhere in the lexicon. This table covers every one of them
# with a hand-curated translation, keyed by (goauld_key, sense_id).

PER_SENSE_TRANSLATIONS: dict[str, dict] = {
    # ─── Canonical core vocabulary ────────────────────────────────────
    "kree": {
        2: {"de": ["allgemeiner imperativ: achtung! hört zu! halt! tut es!"]},
        3: {"de": ["gehorchen"]},
        4: {"de": ["erlass", "dekret"]},
    },
    "kek": {
        2: {"de": ["töten", "erschlagen"]},
        3: {"de": ["tot", "schwach"]},
        4: {"de": ["konflikt", "feindschaft", "krieg"]},
        5: {"en": ["to kill"]},
    },
    "kel": {
        2: {"de": ["wann?", "welcher"]},
        3: {"de": ["wer", "wo"]},
    },
    "shal": {
        2: {"de": ["was ist", "wann", "fragewort: wo"]},
    },
    "nok": {
        2: {"de": ["gerade", "zurzeit", "momentan"]},
        3: {"de": ["denn", "seit", "weil"]},
    },
    "mel":  {2: {"de": ["feuer"]}},
    "hol":  {2: {"de": ["halt", "stehen", "stillstehen"]}},
    "tal":  {2: {"de": ["warten", "geduldig sein"]}},
    "tak":  {2: {"de": ["lüge", "täuschung", "illusion"]}},
    "ta": {
        2: {"de": ["ich", "mich"]},
        3: {"de": ["ich habe"]},
        4: {"en": ["i have"]},
    },
    "lo":    {2: {"de": ["du"]}},
    "lop":   {2: {"de": ["ihr alle", "ihr (plural)"]}},
    "tap":   {2: {"de": ["wir", "uns"]}},
    "tel":   {2: {"de": ["mich", "ich (pronomen)"]}},
    "ka":    {2: {"de": ["nicht tun", "nein (schroff)"]}},
    "re":    {2: {"de": ["kommen"]}},
    "leaa":  {2: {"de": ["hören", "zuhören"]}},
    "onak":  {2: {"de": ["groß", "mächtig", "gewaltig"]}},
    "shree": {2: {"de": ["eindringling", "entweiher"]}},
    "noc":   {2: {"de": ["nicht tun", "nein (schroff)"]}},
    "nokia": {2: {"en": ["before", "prior"]}},

    # ─── Canonical phrases & key terms ────────────────────────────────
    "dal shakka mel": {2: {"de": ["ich sterbe frei"]}},
    "mol kek":        {2: {"de": ["töten", "vernichten", "zerstören"]}},
    "rin'kal'noc":    {2: {"de": ["schlachtplan", "taktik"]}},
    "ring kol nok":   {2: {"de": ["schlachtplan", "taktik"]}},
    "tal shak":       {2: {"de": ["kämpfen"]}},
    "ral tora ke":    {2: {"de": ["alles gute", "beste wünsche"]}},
    "kree hol":       {2: {"de": ["gehen", "laufen"]}},
    "dal'shak kree":  {2: {"de": ["schweigen", "stille", "ruhe"]}},
    "shol'va":        {2: {"de": ["verräter"]}},
    "cal mah":        {2: {"de": ["tempel"]}},
    "kheb":           {2: {"de": ["unterwelt", "jenseits"]}},
    "jaffa":          {2: {"de": ["krieger", "kämpfer", "soldat"]}},
    "tau'ri":         {2: {"de": ["erde"]}},
    "teal'c":         {2: {"de": ["stark"]}},

    # ─── Fanon: basic verbs & body ────────────────────────────────────
    "meta":        {2: {"de": ["sprechen", "sagen"]}},
    "meta'tal":    {2: {"de": ["sprache", "idiom", "redewendung"]}},
    "meta'hol":    {2: {"de": ["schweig!", "halt den mund!", "ruhe!"]}},
    "shac":        {2: {"de": ["beißen"]}},
    "shac'kor":    {2: {"de": ["zahn", "zähne"]}},
    "yu'yu":       {2: {"de": ["sehen"]}},
    "ko":          {2: {"de": ["geben", "nehmen"]}},
    "ko'ren":      {2: {"de": ["berühren"]}},
    "kor'hol":     {2: {"de": ["stehen"]}},
    "kor'vol":     {2: {"de": ["grau"]}},
    "met'tal":     {2: {"de": ["schwimmen"]}},
    "pac'ryn":     {2: {"de": ["fliegen"]}},
    "ren'ryn":     {2: {"de": ["atmen"]}},
    "sha'meta":    {2: {"de": ["denken", "nachdenken"]}},
    "sha'ryn":     {2: {"de": ["fühlen", "empfinden"]}},
    "shakka":      {2: {"de": ["sterben"]}},
    "dormata":     {2: {"de": ["schlafen"]}},
    "eetium":      {2: {"de": ["wissen", "kennen"]}},
    "dan'ryn":     {2: {"de": ["bauen", "erschaffen"]}},
    "dan'ryn'le":  {2: {"de": ["erschaffen", "kreieren"]}},
    "kek'mel":     {2: {"de": ["verbrennen", "zerstören"]}},
    "kek'mel'ryn": {2: {"de": ["verbrennen"]}},
    "kal'ryn":     {2: {"de": ["erinnern", "sich erinnern"]}},
    "tak'ryn":     {2: {"de": ["täuschen", "betrügen"]}},
    "ska'ryn":     {3: {"de": ["wachsen", "gedeihen"]}},
    "ska'nat":     {2: {"de": ["speichern", "sichern"]}},
    "hol'sha":     {2: {"de": ["in manchen kontexten auch 'sterben'"]}},

    # ─── Fanon: tech / society / abstract ─────────────────────────────
    "gal'a'quel":   {2: {"de": ["herunterladen", "übertragen"]}},
    "hakorr":       {2: {"de": ["löschen", "entfernen"]}},
    "in'trom":      {2: {"de": ["einloggen", "eintreten"]}},
    "delmac'tal":   {2: {"en": ["computer", "calculator"]}},
    "nokia'le":     {2: {"de": ["ewig", "unendlich", "unsterblich"]}},
    "kal'ma":       {2: {"de": ["kind", "kinder"]}},
    "kal'ma'tar":   {2: {"de": ["elternteil"]}},
    "lok'tar":      {2: {"de": ["verbündeter"]}},
    "shim'roa'tar": {2: {"de": ["partner", "gefährte"]}},
    "tap'tar":      {2: {"de": ["menschen", "volk", "leute"]}},
    "met'kor'tal":  {2: {"de": ["gletscher", "eisfeld"]}},
    "sha'meta'kal": {2: {"de": ["philosophie", "weltanschauung"]}},
    "sha'meta'tar": {2: {"de": ["denker", "gelehrter", "philosoph"]}},
    "dan'kal'sha":  {2: {"de": ["frieden", "ruhe"]}},
    "mel'sha": {
        2: {"de": ["falls", "sollte", "vorausgesetzt"]},
        3: {"de": ["kummer", "trauer"]},
    },
    "shak'sha":     {2: {"de": ["zorn", "wut"]}},
    "mel'tok'sha":  {2: {"de": ["krieg", "konflikt", "feindschaft"]}},
    "sha'hol'tal":  {2: {"de": ["innere ruhe", "gelassenheit", "seelenfrieden"]}},
    "unas'paca":    {2: {"de": ["ungeziefer", "schädling"]}},
    "skanat'ryn":   {2: {"de": ["nahrung", "mahlzeit", "essen (subst.)"]}},
    "skanat'kal":   {2: {"de": ["essen (verb)"]}},
    "mel'shak'tar": {2: {"de": ["dienerkrieger", "symbionten-inkubator"]}},
    "hol'met'le":   {2: {"de": ["ozean"]}},
    "kree'dan'lok": {2: {"de": ["allgemeiner imperativ: achtung! hört zu! halt! tut es!",
                                "achtung", "hört zu", "konzentriert euch"]}},
    "dan'mel":      {2: {"de": ["jetzt", "zurzeit"]}},
    "mel'nok'sha":  {2: {"de": ["später", "bald"]}},
    "tok'nok":      {2: {"de": ["widerstehen"]}},
    "kel'nok": {
        2: {"de": ["wann"]},
        3: {"en": ["where", "what", "interrogative: where", "who", "what is"]},
        4: {"de": ["was ist", "was", "fragewort: wo"]},
    },
    "kal'kek'sha":  {2: {"de": ["jaffa-jenseits", "ort der erleuchtung"]}},
    "hak'tal":      {2: {"en": ["hideout", "hiding place"]}},
    "mel'nok'tal":  {2: {"de": ["zukunft"]}},
    "melnok":       {2: {"de": ["danach", "später"]}},
    "nokia'tal":    {2: {"de": ["vergangenheit"]}},
    "tak'tal":      {2: {"de": ["trick", "unehrlichkeit", "täuschung"]}},
}


def apply_manual_translations(entries: dict) -> int:
    """
    Apply PER_SENSE_TRANSLATIONS to fill any senses the Bridge + MANUAL_*
    couldn't. Marks each filled sense with 'auto_filled: [lang:manual]'
    so you can audit which ones came from this curated source.
    Returns number of (sense, language) pairs filled.
    """
    filled = 0
    missing_keys: list[str] = []
    missing_senses: list[tuple] = []

    for key, sense_map in PER_SENSE_TRANSLATIONS.items():
        if key not in entries:
            missing_keys.append(key)
            continue
        entry = entries[key]
        for sid, lang_glosses in sense_map.items():
            target = next((s for s in entry["senses"] if s["id"] == sid), None)
            if target is None:
                missing_senses.append((key, sid))
                continue
            for lang, glosses in lang_glosses.items():
                if not target["glosses"].get(lang):
                    target["glosses"][lang] = list(glosses)
                    marker = f"{lang}:manual"
                    existing_flags = target.get("auto_filled") or []
                    if marker not in existing_flags:
                        existing_flags.append(marker)
                    target["auto_filled"] = existing_flags
                    filled += 1

    if missing_keys:
        log.warning("PER_SENSE_TRANSLATIONS: %d key(s) not in lexicon: %s",
                    len(missing_keys), missing_keys[:5])
    if missing_senses:
        log.warning("PER_SENSE_TRANSLATIONS: %d sense-id(s) not found: %s",
                    len(missing_senses), missing_senses[:5])
    return filled


# ──────────────────────────────────────────────────────────────────────────
# SPECIALIZATION FIXES
# ──────────────────────────────────────────────────────────────────────────
# Manual overrides to sharpen Canon glosses that compete with Fanon
# specializations. For each key, specify which glosses to REPLACE with
# sharper alternatives — the canon entry stays alive (so it's still
# found by Goa'uld→DE/EN lookup), but the Fanon alternative becomes the
# primary hit for the *removed* gloss in DE/EN→Goa'uld lookup.
SPECIALIZATION_FIXES = {
    # 'shor'wai'e' is really an imperative ("hurry up!"), not the adjective
    # "fast". Replace the adjective glosses with the imperative.
    "shor'wai'e": {
        "de": {"schnell": "beeile dich"},
        "en": {"fast": "hurry up", "quick": "hurry up"},
    },
    # 'kalach' canonically means "soul" (from Kalach shal tek = "soul returns
    # home"). The adjectival "tapfer/brave" sense was an over-reach of the
    # reverse-map — drop it so the systematic Fanon 'kor'dan' wins "brave".
    "kalach": {
        "de": {"tapfer": None},   # None = remove
        "en": {"brave": None, "courageous": None, "fearless": None,
               "valiant": None},
    },
}


def apply_specialization_fixes(entries: dict) -> tuple[int, int]:
    """
    Apply replace-or-remove overrides to canon entries. Returns
    (replaced_count, removed_count).
    """
    replaced = 0
    removed = 0
    for key, lang_map in SPECIALIZATION_FIXES.items():
        if key not in entries:
            log.warning("SPECIALIZATION_FIXES: key '%s' not in lexicon", key)
            continue
        entry = entries[key]
        for sense in entry["senses"]:
            for lang, mapping in lang_map.items():
                old_list = sense["glosses"].get(lang, [])
                new_list = []
                for g in old_list:
                    key_norm = g.lower().strip()
                    # Check case-insensitive match in mapping
                    hit = None
                    for k_map in mapping:
                        if k_map.lower() == key_norm:
                            hit = k_map
                            break
                    if hit is not None:
                        replacement = mapping[hit]
                        if replacement is None:
                            removed += 1
                            # drop this gloss
                        else:
                            replaced += 1
                            if replacement not in new_list:
                                new_list.append(replacement)
                    else:
                        if g not in new_list:
                            new_list.append(g)
                sense["glosses"][lang] = new_list
        # Drop senses that ended up with zero glosses in ALL languages
        entry["senses"] = [
            s for s in entry["senses"]
            if any(s["glosses"].get(lang) for lang in ("de", "en"))
        ]
        # If the entire entry is now empty, keep it alive with a placeholder
        # (this shouldn't happen with current fixes, but guard anyway)
        if not entry["senses"]:
            log.warning("SPECIALIZATION_FIXES drained all senses from '%s'", key)
    return replaced, removed


# ──────────────────────────────────────────────────────────────────────────
# CONFLICT CLASSIFICATION
# ──────────────────────────────────────────────────────────────────────────
# Each detected conflict gets categorized into one of four types, with a
# handling recommendation. This output drives the manual review decision.

def classify_conflicts(conflicts: list[dict], entries: dict) -> list[dict]:
    """
    For each conflict, add:
      - 'type': 'canon_polysemy' | 'fanon_redundant' | 'fanon_specialization'
                | 'dialect_variant'
      - 'recommendation': human-readable action suggestion
      - 'canon_key' / 'fanon_keys' / 'abydonian_keys': classified candidate sets
    """
    classified = []
    for c in conflicts:
        cands = c["candidates"]
        canon_cands = [x for x in cands if x["register"] == "canon"]
        abyd_cands = [x for x in cands if x["register"] == "abydonian"]
        fanon_cands = [x for x in cands if x["register"] == "fanon"]

        # Get the canon entry (if any) to check its polysemy
        canon_entry = None
        if canon_cands:
            canon_key = canon_cands[0]["key"]
            canon_entry = entries.get(canon_key)

        # Count how many glosses the canon entry carries total across all senses
        canon_gloss_count = 0
        if canon_entry:
            for s in canon_entry["senses"]:
                for lst in s["glosses"].values():
                    canon_gloss_count += len(lst)

        # Classification logic
        if canon_cands and abyd_cands and not fanon_cands:
            ctype = "dialect_variant"
            rec = (f"Keep both — '{canon_cands[0]['key']}' is Standard-Goa'uld, "
                   f"others are Abydonian dialect variants. No action needed.")

        elif canon_cands and fanon_cands:
            # Is the canon word a polysem (e.g. kree with 20+ meanings)?
            if canon_gloss_count >= 8:
                ctype = "canon_polysemy"
                rec = (f"Keep both — '{canon_cands[0]['key']}' is polysemous "
                       f"({canon_gloss_count} glosses). Fanon term "
                       f"'{fanon_cands[0]['key']}' is a legitimate specialization.")
            else:
                # Check if fanon term has extra semantic dimension
                fanon_key = fanon_cands[0]["key"]
                fanon_entry = entries.get(fanon_key, {})
                fanon_gloss_count = sum(
                    len(lst) for s in fanon_entry.get("senses", [])
                    for lst in s["glosses"].values()
                )
                if fanon_gloss_count <= 2:
                    # Fanon only has 1-2 glosses, none of them extend canon → redundant
                    ctype = "fanon_redundant"
                    rec = (f"Consider REMOVING fanon '{fanon_cands[0]['key']}' — "
                           f"canon '{canon_cands[0]['key']}' already covers this meaning "
                           f"and fanon offers no additional semantic range.")
                else:
                    ctype = "fanon_specialization"
                    rec = (f"Keep both, but SHARPEN fanon '{fanon_cands[0]['key']}' "
                           f"glosses to reflect its specialized meaning vs. the "
                           f"broader canon term '{canon_cands[0]['key']}'.")
        elif len(fanon_cands) >= 2 and not canon_cands:
            ctype = "fanon_internal"
            rec = "Multiple fanon terms for the same gloss — consider consolidating."
        else:
            ctype = "uncategorized"
            rec = "Review manually."

        c_enriched = dict(c)
        c_enriched["type"] = ctype
        c_enriched["recommendation"] = rec
        c_enriched["canon_keys"] = [x["key"] for x in canon_cands]
        c_enriched["fanon_keys"] = [x["key"] for x in fanon_cands]
        c_enriched["abydonian_keys"] = [x["key"] for x in abyd_cands]
        classified.append(c_enriched)
    return classified


# ──────────────────────────────────────────────────────────────────────────
# CUSTOM YAML EMITTER
# ──────────────────────────────────────────────────────────────────────────
# Hand-rolled for pixel-perfect formatting: inline short arrays, block-style
# senses, category dividers between entry groups.

def _yaml_scalar(v) -> str:
    """Serialize a scalar as YAML."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    # Quote if contains special chars OR looks like another type OR has leading/trailing space
    # NB: ? , [ ] { } are YAML flow-indicators and MUST be quoted inside flow sequences.
    needs_quote = (
        any(c in s for c in [':', '#', '&', '*', '!', '|', '>', "'", '"',
                             '%', '@', '`', '?', ',', '[', ']', '{', '}'])
        or s.strip() != s
        or s == ""
        or s.lower() in ("null", "true", "false", "yes", "no", "on", "off")
        or re.match(r"^-?\d", s)
    )
    if needs_quote:
        # Prefer double-quoted with \" escapes
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return s


def _yaml_inline_list(items: list) -> str:
    """Inline flow-style list: [a, b, c]"""
    if not items:
        return "[]"
    return "[" + ", ".join(_yaml_scalar(x) for x in items) + "]"


def _yaml_key(k: str) -> str:
    """Emit a mapping key, quoting if it contains apostrophe or special chars."""
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", str(k)):
        return str(k)
    return _yaml_scalar(k)


def emit_entry_yaml(key: str, entry: dict, indent: int = 2) -> str:
    """Emit one full entry as YAML text."""
    ind = " " * indent
    ind2 = " " * (indent + 2)
    ind3 = " " * (indent + 4)
    ind4 = " " * (indent + 6)
    out = []
    out.append(f"{ind}{_yaml_key(key)}:")
    out.append(f"{ind2}term: {_yaml_scalar(entry['term'])}")
    if entry["variants"]:
        out.append(f"{ind2}variants: {_yaml_inline_list(entry['variants'])}")
    out.append(f"{ind2}register: {entry['register']}")
    out.append(f"{ind2}priority: {entry['priority']}")

    # morphology block
    morph = entry["morphology"]
    out.append(f"{ind2}morphology:")
    out.append(f"{ind3}type: {morph['type']}")
    if morph.get("components"):
        out.append(f"{ind3}components: {_yaml_inline_list(morph['components'])}")
    if morph.get("derivation"):
        out.append(f"{ind3}derivation: {_yaml_scalar(morph['derivation'])}")

    # senses list
    out.append(f"{ind2}senses:")
    for s in entry["senses"]:
        out.append(f"{ind3}- id: {s['id']}")
        if s.get("pos"):
            out.append(f"{ind4}pos: {s['pos']}")
        if s.get("category"):
            out.append(f"{ind4}category: {_yaml_scalar(s['category'])}")
        # glosses
        out.append(f"{ind4}glosses:")
        for lang, lst in s["glosses"].items():
            out.append(f"{ind4}  {lang}: {_yaml_inline_list(lst)}")
        if s.get("auto_filled"):
            out.append(f"{ind4}auto_filled: {_yaml_inline_list(s['auto_filled'])}  # translated via cross-bridge — please verify")
        if s.get("context"):
            out.append(f"{ind4}context: {_yaml_scalar(s['context'])}")
        # source
        src = s["source"]
        out.append(f"{ind4}source:")
        out.append(f"{ind4}  tier: {src['tier']}")
        if src.get("ref"):
            out.append(f"{ind4}  ref: {_yaml_scalar(src['ref'])}")
        if src.get("files"):
            out.append(f"{ind4}  files: {_yaml_inline_list(src['files'])}")
        out.append(f"{ind4}priority: {s['priority']}")

    # xref / compounds_in — inline lists
    if entry["xref"]:
        out.append(f"{ind2}xref: {_yaml_inline_list(entry['xref'])}")
    if entry["compounds_in"]:
        out.append(f"{ind2}compounds_in: {_yaml_inline_list(entry['compounds_in'])}")

    return "\n".join(out)


def emit_yaml(entries: dict, conflicts: list, output_path: Path,
              source_files: list[str]) -> None:
    """Emit the full YAML lexicon with header, meta block, and grouped entries."""
    from datetime import datetime, timezone

    lines = []
    # ── Header ───────────────────────────────────────────────────────
    lines.append("# " + "═" * 69)
    lines.append("#  GOA'ULD UNIFIED LEXICON  ·  Schema v1.0")
    lines.append("#  Consolidated from 4 source dictionaries — see source_files below.")
    lines.append("#  Edit freely: this file is the Source of Truth for the translator app.")
    lines.append("# " + "═" * 69)
    lines.append("")

    # ── Meta block ───────────────────────────────────────────────────
    total = len(entries)
    canon_count = sum(1 for e in entries.values() if e["register"] == "canon")
    abyd_count = sum(1 for e in entries.values() if e["register"] == "abydonian")
    fanon_count = sum(1 for e in entries.values() if e["register"] == "fanon")

    lines.append("meta:")
    lines.append('  schema_version: "1.0"')
    lines.append(f'  generated_at: "{datetime.now(timezone.utc).isoformat(timespec="seconds")}"')
    lines.append("  source_files:")
    for sf in source_files:
        lines.append(f"    - {_yaml_scalar(sf)}")
    lines.append(f"  counts: {{ total: {total}, canon: {canon_count}, "
                 f"abydonian: {abyd_count}, fanon: {fanon_count} }}")
    lines.append("  conflicts_detected: " + str(len(conflicts)))
    lines.append("")

    # ── Conflict log (as comment block) ──────────────────────────────
    if conflicts:
        type_counts: dict = defaultdict(int)
        for c in conflicts:
            type_counts[c.get("type", "uncategorized")] += 1

        lines.append("# " + "─" * 69)
        lines.append("# CANON↔FANON CONFLICTS  (classified, with recommendations)")
        lines.append(f"# {len(conflicts)} target glosses map to multiple Goa'uld terms.")
        lines.append("# ")
        for t, n in sorted(type_counts.items(), key=lambda kv: -kv[1]):
            lines.append(f"#   {t:<22s}  {n}")
        lines.append("# ")
        lines.append("# Runtime lookup prefers the highest-priority entry; alternatives")
        lines.append("# remain accessible as secondary suggestions.  Full details in")
        lines.append("# migration_report.txt.")
        lines.append("# " + "─" * 69)
        for c in conflicts[:40]:
            cands = ", ".join(f"{x['key']}({x['priority']},{x['register']})"
                              for x in c["candidates"])
            lines.append(f"# [{c['lang']}] \"{c['gloss']}\"  ({c.get('type','?')})")
            lines.append(f"#    → {cands}")
        if len(conflicts) > 40:
            lines.append(f"# ... and {len(conflicts) - 40} more (see migration_report.txt)")
        lines.append("")

    # ── Entries, grouped by register then by primary category ────────
    lines.append("entries:")
    lines.append("")

    # Group entries by (register, primary_category) for nicer section dividers
    def group_sort_key(item):
        key, entry = item
        register_rank = {"canon": 0, "abydonian": 1, "fanon": 2}[entry["register"]]
        primary_cat = (entry["senses"][0]["category"] if entry["senses"] else "") or ""
        return (register_rank, primary_cat.lower(), key)

    sorted_entries = sorted(entries.items(), key=group_sort_key)

    last_group = None
    for key, entry in sorted_entries:
        primary_cat = (entry["senses"][0]["category"] if entry["senses"] else "") or "Uncategorized"
        group_label = f"{entry['register'].upper()} · {primary_cat}"
        if group_label != last_group:
            lines.append("")
            # Pad to 68 chars total after the "# ─── " prefix, always at least 3 trailing dashes
            pad = max(3, 68 - len(group_label) - 7)
            lines.append(f"  # ─── {group_label} " + "─" * pad)
            last_group = group_label

        lines.append(emit_entry_yaml(key, entry, indent=2))
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("Wrote %s (%d entries, %d bytes)",
             output_path, total, output_path.stat().st_size)


# ──────────────────────────────────────────────────────────────────────────
# LANGUAGE GUIDE EXTRACTION
# ──────────────────────────────────────────────────────────────────────────

def extract_language_guide(md_paths: list[Path], lang: str,
                           output_path: Path) -> None:
    """
    Compile prose sections (non-table content) from the given MDs into a single
    LANGUAGE_GUIDE_{lang}.md file.
    """
    guide_lines = []
    title = "Goa'uld Language Guide" if lang == "en" else "Goa'uld-Sprachleitfaden"
    guide_lines.append(f"# {title}")
    guide_lines.append("")
    intro = (
        "This document contains the linguistic/lore commentary that accompanies the "
        "Goa'uld vocabulary. The vocabulary itself lives in `goauld_lexicon.yaml`."
        if lang == "en" else
        "Dieses Dokument enthält die linguistischen und lore-bezogenen Kommentare, "
        "die das Goa'uld-Vokabular begleiten. Das Vokabular selbst lebt in "
        "`goauld_lexicon.yaml`."
    )
    guide_lines.append(intro)
    guide_lines.append("")

    for path in md_paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        guide_lines.append(f"<!-- ═══ from {path.name} ═══ -->")
        guide_lines.append("")

        in_table = False
        for line in lines:
            if _SEPARATOR.match(line):
                in_table = True
                continue
            if line.strip().startswith("|"):
                in_table = True
                continue
            if in_table and not line.strip():
                in_table = False
                continue
            if in_table:
                continue
            guide_lines.append(line)
        guide_lines.append("")
        guide_lines.append("---")
        guide_lines.append("")

    output_path.write_text("\n".join(guide_lines), encoding="utf-8")
    log.info("Wrote %s (%d lines)", output_path, len(guide_lines))


# ──────────────────────────────────────────────────────────────────────────
# REPORT
# ──────────────────────────────────────────────────────────────────────────

def write_report(entries: dict, conflicts: list, raw_count: int,
                 source_files: list[str], output_path: Path,
                 filled: int = 0, unfilled: int = 0,
                 manual_filled: int = 0,
                 unfilled_samples: Optional[list[str]] = None) -> None:
    """Human-readable migration report with stats and conflict listing."""
    lines = []
    lines.append("═" * 72)
    lines.append("GOA'ULD LEXICON MIGRATION — REPORT")
    lines.append("═" * 72)
    lines.append("")
    lines.append("Source files:")
    for sf in source_files:
        lines.append(f"  • {sf}")
    lines.append("")

    lines.append(f"Raw senses parsed : {raw_count:,}")
    lines.append(f"Unique entries    : {len(entries):,}")
    lines.append(f"Dedup ratio       : {raw_count / max(1, len(entries)):.2f}x")
    lines.append("")

    lines.append("Language gap fill:")
    lines.append(f"  Senses filled via cross-bridge   : {filled:,}")
    lines.append(f"  Senses filled via manual table   : {manual_filled:,}")
    lines.append(f"  Remaining monolingual            : {max(0, unfilled - manual_filled):,}")
    lines.append("")

    # Breakdown by register
    by_reg = defaultdict(int)
    by_tier = defaultdict(int)
    for e in entries.values():
        by_reg[e["register"]] += 1
        for s in e["senses"]:
            by_tier[s["source"]["tier"]] += 1

    lines.append("By register:")
    for r, n in sorted(by_reg.items()):
        lines.append(f"  {r:<12s}  {n:>6,}")
    lines.append("")

    lines.append("By tier (sense-level):")
    for tier in sorted(TIER_PRIORITY, key=lambda k: -TIER_PRIORITY[k]):
        if by_tier[tier]:
            lines.append(f"  {tier:<20s} ({TIER_PRIORITY[tier]:>3d})  {by_tier[tier]:>6,}")
    lines.append("")

    # Morphology breakdown
    by_morph = defaultdict(int)
    for e in entries.values():
        by_morph[e["morphology"]["type"]] += 1
    lines.append("By morphology:")
    for t, n in sorted(by_morph.items()):
        lines.append(f"  {t:<12s}  {n:>6,}")
    lines.append("")

    # Conflicts grouped by type
    type_counts: dict = defaultdict(int)
    for c in conflicts:
        type_counts[c.get("type", "uncategorized")] += 1

    lines.append(f"Canon↔Fanon conflicts detected: {len(conflicts)}")
    for t, n in sorted(type_counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {t:<25s}  {n}")
    lines.append("")

    if conflicts:
        lines.append("─" * 72)
        lines.append("CONFLICT DETAILS (grouped by type)")
        lines.append("─" * 72)
        # Group by type for easier review
        by_type: dict = defaultdict(list)
        for c in conflicts:
            by_type[c.get("type", "uncategorized")].append(c)

        for ctype in ("fanon_redundant", "fanon_specialization",
                      "canon_polysemy", "dialect_variant",
                      "fanon_internal", "uncategorized"):
            items = by_type.get(ctype, [])
            if not items:
                continue
            lines.append("")
            lines.append(f"═══ {ctype.upper()} — {len(items)} cases ═══")
            if items:
                lines.append(f"    → {items[0].get('recommendation', '').splitlines()[0] if items[0].get('recommendation') else ''}")
            lines.append("")
            for c in items:
                lines.append(f"[{c['lang']}] \"{c['gloss']}\"")
                for cand in c["candidates"]:
                    marker = "★" if cand == c["candidates"][0] else " "
                    lines.append(
                        f"    {marker} {cand['key']:<28s}  p={cand['priority']:>3d}  "
                        f"{cand['register']}"
                    )
                lines.append("")

    # Unfilled language gaps
    if unfilled_samples:
        lines.append("")
        lines.append("─" * 72)
        lines.append(f"STILL MONOLINGUAL  ({unfilled} senses — samples below)")
        lines.append("─" * 72)
        for s in unfilled_samples:
            lines.append(f"  {s}")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("Wrote %s", output_path)


# ──────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────

def find_source_files(input_dir: Path) -> list[Path]:
    """Locate the 4 source MDs — supports both apostrophe and underscore variants."""
    candidates = []
    patterns = [
        "Goauld-Dictionary.md",  "Goauld-Dictionary.md",
        "Goauld-Woerterbuch.md",  "Goauld-Woerterbuch.md",
        "Goauld-Fictionary.md",  "Goauld-Fictionary.md",
        "Goauld-Neologikum.md",  "Goauld-Neologikum.md",
    ]
    seen_stems = set()
    for pat in patterns:
        p = input_dir / pat
        if p.exists():
            stem_sig = next((k for k in SOURCE_META if k in p.stem), None)
            if stem_sig and stem_sig not in seen_stems:
                candidates.append(p)
                seen_stems.add(stem_sig)
    return candidates


def main() -> int:
    ap = argparse.ArgumentParser(description="Migrate 4 Goa'uld MDs → 1 unified YAML lexicon")
    ap.add_argument("--input-dir", type=Path, required=True,
                    help="Directory containing the 4 source MD dictionaries")
    ap.add_argument("--output-dir", type=Path, required=True,
                    help="Where to write the YAML + language guides + report")
    args = ap.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    md_files = find_source_files(args.input_dir)
    if len(md_files) != 4:
        log.warning("Expected 4 source files, found %d: %s",
                    len(md_files), [p.name for p in md_files])

    # ── Parse all MDs ────────────────────────────────────────────────
    all_raw: list[RawSense] = []
    prose_by_lang: dict[str, list[tuple[Path, list[str]]]] = defaultdict(list)

    for md in md_files:
        raw_senses, prose = parse_markdown(md)
        all_raw.extend(raw_senses)
        # Determine language from source meta
        key = next((k for k in SOURCE_META if k in md.stem), None)
        if key:
            lang = SOURCE_META[key][1]
            prose_by_lang[lang].append((md, prose))

    # ── Build lexicon ────────────────────────────────────────────────
    entries, conflicts = build_lexicon(all_raw)
    populate_compounds_in(entries)

    # ── Apply specialization fixes BEFORE gap-fill ──────────────────
    # (so the removed canon glosses don't leak back through the bridge)
    replaced, removed = apply_specialization_fixes(entries)
    log.info("Specialization fixes: %d gloss(es) replaced, %d removed",
             replaced, removed)

    # ── Cross-sense dedupe FIRST ────────────────────────────────────
    # Remove glosses that already appear in an earlier sense of the
    # same entry. This can leave some senses monolingual — we fix that
    # in the next step.
    deduped = cross_sense_dedupe(entries)
    log.info("Cross-sense dedup: removed %d duplicate gloss(es)", deduped)

    # ── Fill language gaps LAST ─────────────────────────────────────
    # Running this AFTER dedupe ensures every sense that survived
    # dedupe gets its missing-language gloss filled in. Final state:
    # every sense is bilingual.
    filled, unfilled, unfilled_samples = fill_language_gaps(entries)
    log.info("Language gap fill: %d senses filled, %d remain monolingual",
             filled, unfilled)

    # ── Second gap-fill pass with manual translations for the stragglers
    # The Bridge can't help if a gloss simply doesn't appear in any
    # bilingual entry. For those, we fall back to a curated translation
    # dictionary covering every remaining monolingual case.
    still = 0
    if unfilled > 0:
        still = apply_manual_translations(entries)
        log.info("Manual translations: filled %d remaining senses", still)

    # ── Re-detect conflicts AFTER all mutations ──────────────────────
    # The conflicts list from build_lexicon reflects the pre-narrowed
    # state. Recompute from the final entries so resolved specialization
    # cases drop off the list.
    conflicts = _detect_conflicts(entries)
    log.info("Conflicts after narrowing: %d", len(conflicts))

    # ── Classify conflicts with handling recommendations ─────────────
    conflicts = classify_conflicts(conflicts, entries)

    # ── Emit YAML ────────────────────────────────────────────────────
    yaml_path = args.output_dir / "goauld_lexicon.yaml"
    emit_yaml(entries, conflicts, yaml_path,
              source_files=[p.name for p in md_files])

    # ── Extract language guides ──────────────────────────────────────
    for lang in ("de", "en"):
        if prose_by_lang[lang]:
            md_paths = [p for p, _ in prose_by_lang[lang]]
            guide_path = args.output_dir / f"LANGUAGE_GUIDE_{lang.upper()}.md"
            extract_language_guide(md_paths, lang, guide_path)

    # ── Report ───────────────────────────────────────────────────────
    report_path = args.output_dir / "migration_report.txt"
    write_report(entries, conflicts, len(all_raw),
                 [p.name for p in md_files], report_path,
                 filled=filled, unfilled=unfilled,
                 manual_filled=still,
                 unfilled_samples=unfilled_samples)

    log.info("✔ Migration complete")
    log.info("  YAML    : %s", yaml_path)
    log.info("  Report  : %s", report_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
