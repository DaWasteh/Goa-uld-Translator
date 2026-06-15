#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║   STARGATE — GOA'ULD LINGUISTIC INTERFACE  v0.2.6                ║
║   SGC Xenolinguistics Division  ·  Classification: LEVEL 28      ║
╚══════════════════════════════════════════════════════════════════╝

Bidirektionaler Übersetzer für die Goa'uld-Sprache aus der
Stargate-Franchise. Liest automatisch das Markdown-Wörterbuch ein
und kombiniert es mit dem eingebetteten Vokabular.

Anforderungen:
    pip install customtkinter

Verwendung:
    python goauld_translator_gui.py
    python goauld_translator_gui.py --md /pfad/zum/dictionary.md
    python goauld_translator_gui.py --cli --dir goa2de --text "Jaffa kree"
"""

import argparse
import difflib
import logging
import re
import sys
from pathlib import Path
from typing import Optional

_YAML_LOADER_WARNING: str | None = None
try:
    from yaml_loader import find_lexicon_yaml, load_lexicon_yaml
    YAML_LOADER_AVAILABLE = True
except ImportError:
    YAML_LOADER_AVAILABLE = False
    # HINWEIS: `log` ist hier noch nicht definiert (Setup passiert weiter unten).
    # Warnung wird nach dem Logging-Setup erneut ausgegeben.
    _YAML_LOADER_WARNING = "yaml_loader.py nicht gefunden — falle auf MD-Loader zurück"

# ── Logging Setup ─────────────────────────────────────────────────────────────
# Bei --noconsole (PyInstaller) gibt es kein stdout — Ausgabe in Logdatei.
def _setup_logging() -> logging.Logger:
    _frozen = getattr(sys, 'frozen', False)
    handlers: list[logging.Handler] = []
    if _frozen:
        # Logdatei neben der .exe ablegen
        _log_dir = Path(sys.executable).parent
        _log_file = _log_dir / "goauld_translator.log"
        try:
            handlers.append(logging.FileHandler(_log_file, encoding="utf-8"))
        except OSError:
            pass  # Wenn auch das nicht klappt, still ignorieren
    else:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(message)s",
        handlers=handlers,
    )
    return logging.getLogger(__name__)

log = _setup_logging()

# Verspätete Warnung, falls der YAML-Loader-Import scheiterte
if _YAML_LOADER_WARNING:
    log.warning(_YAML_LOADER_WARNING)


# ── Dependency Check ──────────────────────────────────────────────────────────

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    # Auto-install NUR im Entwicklungskontext — NIEMALS in einer gepackten .exe.
    # sys.frozen wird von PyInstaller auf True gesetzt; ohne diesen Guard würde
    # subprocess.run(sys.executable) die .exe rekursiv in einer Endlosschleife
    # neu starten (~1000x/min → PC-Absturz).
    if not getattr(sys, 'frozen', False):
        try:
            import subprocess
            log.info("CustomTkinter nicht gefunden — versuche automatische Installation…")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "customtkinter", "--quiet"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0:
                import customtkinter as ctk  # type: ignore[import-untyped]  # noqa: I001
                CTK_AVAILABLE = True
                log.info("CustomTkinter erfolgreich installiert!")
            else:
                log.warning("CustomTkinter konnte nicht automatisch installiert werden.")
                log.warning("Manuelle Installation: python -m pip install customtkinter")
                log.warning("Falls pip defekt ist: python -m ensurepip --upgrade")
        except Exception as _install_err:
            log.warning("Auto-Install fehlgeschlagen: %s", _install_err)
            log.warning("Manuelle Installation: python -m pip install customtkinter")
    else:
        log.warning("CustomTkinter nicht im Bundle — GUI fällt auf Standard-Tkinter zurück.")

try:
    import tkinter as tk
    import tkinter.filedialog as filedialog
    import tkinter.messagebox as messagebox
    import tkinter.ttk as ttk
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False

# Tkinter availability is checked at GUI launch time, not here —
# CLI mode works without Tkinter.


# ─────────────────────────────────────────────────────────────────────────────
# DESIGN-KONSTANTEN  (SGC-Terminal  ·  Dark / Gold / Orange)
# ─────────────────────────────────────────────────────────────────────────────

C = {
    # Backgrounds
    "bg_root":      "#07090C",
    "bg_panel":     "#0B0F18",
    "bg_card":      "#101820",
    "bg_input":     "#0D1420",
    "bg_hover":     "#162030",
    "bg_select":    "#1A2D48",
    "bg_sentence":  "#0A1828",
    "bg_alt":       "#0E1822",
    # Gold palette
    "gold":         "#C8A040",
    "gold_dim":     "#604E1E",
    "gold_bright":  "#F0C050",
    "gold_text":    "#DEB850",
    # Orange / chevron-lit
    "orange":       "#C87020",
    "orange_bright":"#E89040",
    "orange_dim":   "#7A4010",
    "chevron":      "#D06820",
    # Blue / event horizon
    "blue_dim":     "#0A1828",
    "blue_mid":     "#133058",
    "blue_gate":    "#1A5898",
    "blue_bright":  "#2A80D8",
    # Gate-locked / found
    "locked":       "#226840",
    "locked_bright":"#38B060",
    "locked_dim":   "#143820",
    # Text
    "text_hi":      "#EAE0C8",
    "text_mid":     "#9A9080",
    "text_lo":      "#484030",
    "text_gold":    "#C8A040",
    "text_blue":    "#6898C8",
    "text_locked":  "#38B060",
    "text_kek":     "#904030",
    # Borders / separators
    "border":       "#1A1A10",
    "border_gold":  "#302818",
    "border_blue":  "#1A2840",
    "sep":          "#221E12",
    # Status colors
    "found":        "#40A060",
    "warn":         "#C87020",
    "error":        "#A03020",

    # NEU: SGC-Terminal Screen-Effekte
    "scanline":     "#00000010",    # Scanline-Overlay (transparent)
    "glow_gold":    "#F0C05030",    # Gold-Glow (transparent)
    "glow_blue":    "#2A80D820",    # Blau-Glow (transparent)
    "screen_tint":  "#0A182810",    # Gesamter Screen-Tint

    # NEU: SGC-spezifisch
    "sgc_green":    "#30A030",      # SGC Terminal-Grün (für Status)
    "sgc_green_dim":"#1A4020",      # Gedämpftes Grün
    "warning_red":  "#C03020",      # Warnung/Rot
    "warning_red_dim":"#401810",    # Gedämpftes Rot
    "card_border":  "#1A2840",      # Karten-Rand (blau)
    "card_border_g":"#302818",      # Karten-Rand (gold)

    # NEU v0.2.5: Classification Bar (TOP SECRET)
    "class_bg":     "#3A0A0A",      # Dunkles Rot — Background
    "class_border": "#601818",      # Rand der Classification-Bar
    "class_text":   "#F0A0A0",      # Heller roter Text
    "class_block":  "#904030",      # Block-Quadrate ■ ■ ■
    # NEU v0.2.5: Militär-Akzente
    "mil_amber":    "#D89020",      # Signal-Amber für Operator-ID
    "mil_text_dim": "#888070",      # Gedämpfter Military-Grau
    "phosphor_grn": "#40B060",      # Phosphor-Grün für LEDs
}

# Font helpers (tuples for Tkinter)
def F(size: int, weight: str = "normal", family: str = "Courier") -> tuple:
    return (family, size, weight)

FONT = {
    "display":  F(20, "bold"),
    "subtitle": F(10),
    "section":  F(11, "bold"),
    "label":    F(10),
    "body":     F(11),
    "body_bold":F(11, "bold"),
    "small":    F(9),
    "mono":     F(11),
    "entry":    F(13),
    "result":   F(12),
    "detail":   F(11),
    "tag":      F(9),
}

# Glyph decorations
GLYPH_SECTION  = "◈"
GLYPH_ARROW    = "→"
GLYPH_BULLET   = "▸"
GLYPH_SEP      = "─"
GLYPH_STAR     = "✦"
GLYPH_RING     = "◎"
GLYPH_GATE     = "⊕"
GLYPH_CHEVRON  = "▽"
GLYPH_LOCKED   = "◆"
GLYPH_FOUND    = "◉"
GLYPH_KEK      = "☓"

# Candidate MD filenames to try automatically
# Beide Schreibweisen: Apostroph (Windows/Mac) und Unterstrich (Linux/Mount)
MD_CANDIDATES_EN = [
    "Goauld-Dictionary.md",
    "Goauld-Fictionary.md",
]
MD_CANDIDATES_DE = [
    "Goauld-Woerterbuch.md",
    "Goauld-Neologikum.md",
]

# Legacy single-file candidates (backwards-compat for --md flag)
MD_CANDIDATES = MD_CANDIDATES_EN + MD_CANDIDATES_DE


# ─────────────────────────────────────────────────────────────────────────────
# MARKDOWN PARSER
# ─────────────────────────────────────────────────────────────────────────────

# Header cells we skip (those are the table-header rows, not data)
_SKIP_FIRST = {"goa'uld", "phrase", "abydonian", "goauld", "deutsch"}
_SKIP_SECOND = {"meaning", "english", "translation", "compound analysis",
                "context", "notes", "episode", "speaker", "source / episode",
                "bedeutung", "goa'uld", "goauld", "kontext", "kategorie"}

# Section headings that signal reversed columns (Deutsch/English → Goa'uld).
#
# FIX (v0.2.5): Früher war das ein exact-match Set mit festen Strings wie
# "deutsch → goa'uld: direktzuordnung".  Dadurch wurde die Sektion
# "## Deutsch → Goa'uld: Direktzuordnung (Neologikum)" aus dem Neologikum
# NICHT erkannt — der Zusatz "(Neologikum)" ließ den Exact-Match fehlschlagen.
# Konsequenz: 1200+ Einträge wurden umgekehrt eingelesen (goauld-Feld bekam
# deutsche Wörter, meaning-Feld bekam Goa'uld-Wörter), was die Engine-Suche
# und das DE_GOAULD_MAP verfälschte (z.B. "tap'tar" → "menschheit" statt
# umgekehrt).  Dasselbe Problem bestand symmetrisch für "English → Goa'uld"
# im Fictionary.
#
# Jetzt: Regex-basiert.  Erkennt alle Varianten:
#   "Deutsch → Goa'uld"
#   "Deutsch → Goa'uld: Direktzuordnung"
#   "Deutsch → Goa'uld: Direktzuordnung (Neologikum)"
#   "DE → Goa'uld"
#   "English → Goa'uld: Direct lookup"
#   "EN → Goa'uld"
# Erlaubte Pfeile: →, ->, =>, -->
# Erlaubte Apostrophe in "Goa'uld": ', ’, ´, ` (Unicode-tolerant)
_DE_GOA_SECTION_RE = re.compile(
    r"^\s*(deutsch|de|english|en)\s*(?:→|->|-->|=>)\s*goa['\u2019\u00b4`]?uld\b",
    re.IGNORECASE,
)

# Legacy-Alias — falls irgendwo noch referenziert.  Die Regex ist jetzt
# die Single Source of Truth.
_DE_GOA_SECTION_MARKERS: frozenset[str] = frozenset()


def _clean(text: str) -> str:
    """Strip **bold** markers, inline code, and whitespace."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = text.strip().strip('"').strip("'")
    return text.strip()


def parse_markdown_dictionary(filepath: str) -> list[dict]:
    """
    Parse a Goa'uld markdown dictionary and return a list of entries.

    Each entry is a dict:
        goauld   – the Goa'uld word / phrase
        meaning  – the translation (German or English)
        section  – which section of the dictionary
        source   – episode / source reference (optional)

    Also handles reversed sections (Deutsch → Goa'uld) where col0 is the
    German word and col1 is the Goa'uld target — these are returned with
    goauld/meaning swapped so the engine sees them correctly.
    """
    entries: list[dict] = []
    try:
        with open(filepath, encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError as exc:
        log.warning("Markdown-Datei nicht lesbar: %s", exc)
        return entries

    current_section = "Allgemein"
    reversed_section = False   # True inside a Deutsch→Goa'uld table

    for raw in lines:
        line = raw.rstrip("\n")

        # Track section headings
        if line.startswith("## ") or line.startswith("# "):
            current_section = line.lstrip("#").strip()
            # FIX (v0.2.5): Regex-basierte Erkennung statt exact-match Set.
            # Fängt jetzt auch "Direktzuordnung (Neologikum)", "Direct lookup"
            # und englische Varianten ab.
            reversed_section = bool(_DE_GOA_SECTION_RE.match(current_section))
            continue

        # Only process table rows
        if not line.startswith("|"):
            continue

        # Skip separator rows (| --- | --- |)
        if re.search(r"\|\s*[-:]+\s*\|", line):
            continue

        parts = [_clean(p) for p in line.split("|")]
        parts = [p for p in parts if p]

        if len(parts) < 2:
            continue

        col0 = parts[0]
        col1 = parts[1]
        col2 = parts[2] if len(parts) > 2 else ""

        # Skip header rows
        if col0.lower() in _SKIP_FIRST:
            continue
        if col1.lower() in _SKIP_SECOND:
            continue
        if not col0 or not col1:
            continue

        if reversed_section:
            # col0 = Deutsch, col1 = Goa'uld  → swap so engine is consistent
            entries.append({
                "goauld":  col1,
                "meaning": col0,
                "section": current_section,
                "source":  col2,
                "de_map":  True,   # marker: used to rebuild DE_GOAULD_MAP
            })
        else:
            entries.append({
                "goauld":  col0,
                "meaning": col1,
                "section": current_section,
                "source":  col2,
            })

    return entries


def parse_de_map_from_entries(entries: list[dict]) -> dict[str, str]:
    """
    Baut das DE→Goa'uld-Direktwörterbuch aus den geladenen MD-Einträgen.

    Zwei Quellen:
    1. Explizite de_map-Einträge (Wörterbuch: Deutsch→Goa'uld-Direktzuordnung)
    2. Auto-Reverse: DE-Einträge (lang=="de") mit einwortigem deutschem Bedeutungsfeld
       → ermöglicht Satz-Übersetzung aus Neologikum/Fictionary ohne manuelle de_map-Tags.
    """
    result: dict[str, str] = {}

    # Quelle 1: Explizit markierte Direktzuordnungen (höchste Priorität)
    for e in entries:
        if e.get("de_map"):
            key = e["meaning"].lower().strip()
            result[key] = e["goauld"].strip()

    # Quelle 2: Auto-Reverse aus einfachen DE-Einträgen
    # Aus jeder Bedeutung den ersten deutschen Term extrahieren:
    #   "Kind (geschlechtsneutral)"  → "kind"
    #   "Fehler, Alarm, Warnsignal"  → "fehler" + "alarm" + "warnsignal"
    #   "Zukunft, das Kommende"       → "zukunft"
    import re as _re2
    _split_re  = _re2.compile(r"[,;]")
    _paren_re  = _re2.compile(r"\s*\(.*?\)")
    _word_ok   = _re2.compile(r"^[\w\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df\'\-]+$", _re2.UNICODE)
    for e in entries:
        if e.get("lang") != "de":
            continue
        if e.get("de_map"):
            continue  # bereits in Quelle 1 erfasst
        goauld = e["goauld"].strip()
        parts  = _split_re.split(e["meaning"].strip())
        for part in parts:
            term = _paren_re.sub("", part).strip()
            key  = term.lower()
            # Nur aufnehmen wenn einwortig und noch nicht belegt
            if " " not in term and _word_ok.match(term) and key not in result:
                result[key] = goauld

    return result


def _build_reverse_map_for_lang(entries: list[dict], lang: str) -> dict[str, str]:
    """Best-effort reverse map used only by the Markdown fallback loader."""
    result: dict[str, str] = {}
    ranked: dict[str, tuple[int, str]] = {}
    for entry in entries:
        if entry.get("lang") != lang:
            continue
        meaning = _normalize_lookup(str(entry.get("meaning", "")))
        goauld = str(entry.get("goauld", "")).strip()
        if not meaning or not goauld:
            continue
        priority = int(entry.get("priority", 0) or 0)
        if meaning not in ranked or priority > ranked[meaning][0]:
            ranked[meaning] = (priority, goauld)
    for meaning, (_priority, goauld) in ranked.items():
        result[meaning] = goauld
    return result


# ─────────────────────────────────────────────────────────────────────────────
# SEARCH ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class SearchEngine:
    """
    Bidirektionale Suche mit exaktem Matching, Präfix-Matching und Fuzzy-Matching.
    """

    # Quellen-Priorität: Haupt-Wörterbuch > Fictionary > Neologikum
    _SOURCE_PRIORITY: dict[str, int] = {
        "Goauld-Woerterbuch.md": 3,
        "Goauld-Dictionary.md": 3,
        "Goauld-Fictionary.md": 2,
        "Goauld-Neologikum.md": 1,
        "Gap-Fill": 2,
        "Kanon": 3,
        "Kanon-ext": 2,
        "Fanon": 2,
        "Fanon/RPG": 2,
        "RPG-Lexikon": 2,
        "SG1-Kanon": 3,
        "Egyptian-Substrate": 1,
    }

    def __init__(self, entries: list[dict]) -> None:
        self.entries = entries
        # FIX 1 (translation-bugs-findings.md): Deduplikation mit Quellen-Priorität
        # Bei gleichem (goauld_lower, meaning_lower) behalten wir den Eintrag
        # mit der höheren Quellen-Priorität.
        seen: dict[tuple, tuple[int, dict]] = {}
        for e in entries:
            key = (e["goauld"].lower(), e["meaning"].lower())
            src = e.get("source", "")
            priority = self._SOURCE_PRIORITY.get(src, 0)
            if key not in seen:
                seen[key] = (priority, e)
            else:
                old_priority = seen[key][0]
                if priority > old_priority:
                    seen[key] = (priority, e)
        self.entries = [e for _, e in seen.values()]

    # ─── public api ──────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        direction: str = "goa2de",
        max_results: int = 80,
        fuzzy_threshold: float = 0.45,
        lang_pref: str = "de",
        prefer_short_target: bool = False,
        min_score: int = 0,
    ) -> list[dict]:
        """
        direction:           'goa2de' → suche in goauld-Spalte
                             'de2goa' → suche in meaning-Spalte
        lang_pref:           'de' → deutsche Einträge zuerst
                             'en' → englische Einträge zuerst
        prefer_short_target: True → bevorzuge Einträge mit einwortigem Ziel
        min_score:           Mindest-Score (vor Boni) — Treffer unterhalb werden
                             verworfen. Für de2goa empfohlen: 50 (nur echte Wort-
                             Matches, keine fuzzy-Zufallstreffer).
        """
        q = query.strip()
        if not q:
            return []
        q_low = q.lower()

        field = "goauld" if direction == "goa2de" else "meaning"

        results: list[tuple[float, dict]] = []

        for e in self.entries:
            val = e[field].lower()
            # FIX 3 (translation-bugs-findings.md): Dynamischen Fuzzy-Threshold für kurze Wörter
            eff_threshold = fuzzy_threshold
            if len(q_low) <= 6:
                eff_threshold = max(fuzzy_threshold, 0.7)  # Höherer Threshold für kurze Wörter
            base_score = self._score(q_low, val, fuzzy_threshold=eff_threshold, direction=direction)
            if base_score > 0 and base_score >= min_score:
                # Sprach-Bonus: bevorzugte Sprache +8 Punkte
                lang_bonus = 8 if e.get("lang", "de") == lang_pref else 0
                # Einzelwort-Bonus: bei Einzelwort-Eingabe kurze Übersetzungen bevorzugen
                # (vermeidet dass "liebe" → "Pal tiem shree tal ma" statt "mel")
                short_bonus = 0
                if prefer_short_target:
                    target_field = "goauld" if direction == "de2goa" else "meaning"
                    target_val = e[target_field].strip()
                    if " " not in target_val:   # einwortiges Ziel
                        short_bonus = 15
                # de2goa-Bonus: exakte/partielle Übereinstimmung priorisieren
                de2goa_bonus = 0
                if direction == "de2goa":
                    # Exakter oder Prefix-Match in meaning → Bonus
                    if val == q_low or val.startswith(q_low):
                        de2goa_bonus = 10
                    # Whole-word match in meaning → Bonus
                    if re.search(rf"\b{re.escape(q_low)}\b", val, re.IGNORECASE):
                        de2goa_bonus = max(de2goa_bonus, 5)
                # FIX 5 (translation-bugs-findings.md): Sekundäre Quellen strafen
                source_penalty = 0
                src = e.get("source", "")
                if src in ("Goauld-Fictionary.md", "Goauld-Neologikum.md"):
                    source_penalty = 15  # -15 Punkte für Fictionary/Neologikum
                final_score = base_score + lang_bonus + short_bonus + de2goa_bonus - source_penalty
                # FIX 4 (translation-bugs-findings.md): Debug-Logging für fehlende Wörter
                if base_score == 0 and q_low in ("stirb", "vernichten", "deine", "mensch", "human"):
                    log.warning("FEHLER: '%s' hat base_score=0 für Eintrag: %s", q_low, e)
                results.append((final_score, e))

        results.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in results[:max_results]]

    def search_all(self, query: str, max_results: int = 80) -> list[dict]:
        """Suche in beiden Feldern gleichzeitig."""
        q = query.strip()
        if not q:
            return []
        q_low = q.lower()
        # FIX P5c: Index statt id(e) — id() kann bei GC recycelt werden
        best: dict[int, tuple[int, dict]] = {}  # index → (score, entry)

        for idx, e in enumerate(self.entries):
            score_g = self._score(q_low, e["goauld"].lower())
            score_m = self._score(q_low, e["meaning"].lower())
            score = max(score_g, score_m)
            if score > 0:
                if idx not in best or best[idx][0] < score:
                    best[idx] = (score, e)

        results = sorted(best.values(), key=lambda x: x[0], reverse=True)
        return [e for _, e in results[:max_results]]

    # ─── private ─────────────────────────────────────────────────────────────

    @staticmethod
    def _score(query: str, value: str, fuzzy_threshold: float = 0.42,
               direction: str = "goa2de") -> int:
        """
        Bewertungsfunktion für Similarity-Score.

        Strategie (priorisiert):
        1. Exakter Match (100)
        2. Prefix-Match (85)
        3. Whole-word match (75)
        4. Teilwort-Match (65)
        5. Wort-Level-Match (55-60)
        6. Fuzzy-Match (0-45)

        Bonus für Längen-Ähnlichkeit: Kürzere, passende Treffer erhalten
        einen zusätzlichen Score-Bonus.

        direction: 'de2goa' → höhere Schwellenwerte für meaningful matches
        """
        if value == query:
            return 100
        if value.startswith(query):
            return 85
        # Whole-word match: query als ganzes Wort in value
        if re.search(rf"\b{re.escape(query)}\b", value, re.IGNORECASE):
            return 75
        if query in value:
            return 65
        # word-level match
        value_words = re.split(r"[\s,;/!?()]+", value)
        if any(w.startswith(query) for w in value_words if w):
            return 60
        if any(query in w for w in value_words if w):
            return 55
        # Substring match mit Längen-Bonus
        if len(query) > 3:
            for w in value_words:
                if w and query[:max(4, len(query)//2)] in w:
                    return 45
        # fuzzy
        ratio = difflib.SequenceMatcher(None, query, value).ratio()
        if ratio >= fuzzy_threshold:
            # Längen-Bonus: ähnliche Längen erhalten höheren Score
            len_ratio = min(len(query), len(value)) / max(len(query), len(value))
            return int(ratio * 45 * (0.5 + 0.5 * len_ratio))
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# STOP WORDS  (Deutsche Funktionswörter ohne Goa'uld-Äquivalent)
# ─────────────────────────────────────────────────────────────────────────────

# Goa'uld hat keine Artikel, keine Hilfsverben im deutschen Sinne und kaum
# Präpositionen — diese Wörter werden bei DE→Goa'uld stumm übersprungen.
def _normalize_lookup(text: str) -> str:
    """Normalize lookup keys while preserving Goa'uld glottal stops."""
    normalized = text.strip().lower()
    normalized = normalized.replace("’", "'").replace("´", "'").replace("`", "'")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _de_lemma_candidates(word: str) -> list[str]:
    """
    Gibt mögliche Grundformen für ein deutsches Wort zurück.
    Deckt häufige Verb-Konjugation und Nominalflexion ab, damit
    DE_MAP-Lookups für Imperativ/Plural/Genitiv-Formen funktionieren.

    Beispiele:
      zerstör  → [zerstör, zerstöre, zerstören]
      liebst   → [liebst, lieben, liebe, lieb]
      raumschiffe → [raumschiffe, raumschiff]

    Erweiterungen:
      - Umlaut-Varianten: ä→a, ö→o, ü→u
      - Kompositvorschläge: "frei" → auch "Freiheit" prüfen
      - Reduplikation: "sterbe" → "sterben", "sterbt"
      - Genitiv: "dem" → "der"
      - Kompositvorschläge: "zerstör" → "Zerstörung"
      - Kontraktionen: "im" → "in dem", "zum" → "zu dem"
    """
    w = word.lower().strip()
    candidates = [w]

    # ── Verb: Imperativ-Ergänzungen ──────────────────────────────────────────
    # "zerstör" → "zerstöre", "zerstören"
    # Nur für kurze Wörter und keine offensichtlichen Nomen-Plurale
    _is_noun_plural = (
        w.endswith("e") and len(w) > 6
        and not w.endswith("che")
        and not w.endswith("sse")
        and not w.endswith("phe")
        and not w.endswith("nte")
        and not w.endswith("ste")
    )
    if not _is_noun_plural:
        if not w.endswith("e"):
            candidates.append(w + "e")
        if not w.endswith("en"):
            candidates.append(w + "en")
    else:
        # Für Nomen-Plurale: nur Singular-Form hinzufügen
        candidates.append(w[:-1])

    # ── Verb: Präsens → Infinitiv ─────────────────────────────────────────────
    # "zerstörst" → "zerstör" → "zerstören"
    # Nur für Verben, nicht für Nomen-Plurale
    if not _is_noun_plural:
        if w.endswith("st"):
            stem = w[:-2]
            candidates += [stem, stem + "en", stem + "e"]
        if w.endswith("t") and len(w) > 3:
            stem = w[:-1]
            candidates += [stem, stem + "en", stem + "e"]
        if w.endswith("est"):
            stem = w[:-3]
            candidates += [stem, stem + "en", stem + "e"]
        # 1. Person Singular → Infinitiv
        if w.endswith("e") and len(w) > 3:
            stem = w[:-1]
            if stem:
                candidates += [stem + "en", stem + "st", stem + "t"]
        # Imperativ Singular → Infinitiv
        if len(w) > 4 and not w.endswith("e") and not w.endswith("en"):
            candidates += [w + "st", w + "t"]

    # ── Nomen: Plural-Formen → Singular ──────────────────────────────────────
    # "raumschiffe" → "raumschiff"
    if w.endswith("e") and len(w) > 3:
        candidates.append(w[:-1])
    # "götter" → "gott"  (not perfect but helps)
    if w.endswith("er") and len(w) > 4:
        candidates.append(w[:-2])
    if w.endswith("en") and len(w) > 4:
        candidates.append(w[:-2])
    if w.endswith("nen") and len(w) > 5:
        candidates.append(w[:-3])

    # ── Nomen: Genitiv → Nominativ ────────────────────────────────────────────
    # "hauses" → "haus"
    if w.endswith("es") and len(w) > 3:
        candidates.append(w[:-2])
    if w.endswith("s") and len(w) > 2:
        candidates.append(w[:-1])

    # ── Adjektiv-Endungen → Stamm ─────────────────────────────────────────────
    for suffix in ("em", "en", "er", "es", "sten", "test"):
        if w.endswith(suffix) and len(w) > len(suffix) + 2:
            candidates.append(w[: -len(suffix)])

    # ── Superlativ/Comparativ → Positiv ───────────────────────────────────────
    if w.endswith("sten") and len(w) > 5:
        candidates.append(w[:-4])  # "meisten" → "meist"
    if w.endswith("test") and len(w) > 5:
        candidates.append(w[:-4])  # "am besten" → "best"

    # ── Umlaut-Varianten ──────────────────────────────────────────────────────
    # ä→a, ö→o, ü→u, ß→ss (für DE_MAP-Lookup)
    umlaut_map = str.maketrans("äöü", "aou")
    plain = w.translate(umlaut_map).replace("ß", "ss")
    if plain != w:
        candidates.append(plain)
        # Auch Plural/Verb-Formen des Stamms
        if not plain.endswith("e"):
            candidates.append(plain + "e")
        if not plain.endswith("en"):
            candidates.append(plain + "en")

    # ── Rückwärts-Umlaut: a→ä, o→ö, u→ü, ss→ß ────────────────────────────────
    # Hilfreich wenn DE_MAP Umlaute hat, aber Eingabe nicht
    # Nur einfache 1:1 Mapping, ss→ß ist komplexer
    reverse_chars = {"a": "ä", "o": "ö", "u": "ü"}
    umlauted = "".join(reverse_chars.get(c, c) for c in w)
    if "ss" in w:
        umlauted_ss = umlauted.replace("ss", "ß")
        candidates.append(umlauted_ss)
    if umlauted != w and len(umlauted) == len(w):
        candidates.append(umlauted)

    # ── Kontraktionen auflösen ────────────────────────────────────────────────
    _kontraktionen: dict[str, str] = {
        "im": "in dem", "zum": "zu dem", "ans": "an das",
        "ams": "an dem", "ins": "in das",
        "beim": "bei dem", "vom": "von dem",
    }
    if w in _kontraktionen:
        candidates.extend(_kontraktionen[w].split())

    # ── Kompositvorschläge (häufige Suffixe) ─────────────────────────────────
    # "frei" → "Freiheit", "Stärke" → "stark"
    for suffix in ("heit", "keit", "ung", "bar", "sam", "lich", "isch", "haft", "los", "voll"):
        if w.endswith(suffix):
            stem = w[:-len(suffix)]
            if stem:
                candidates.append(stem)
    # "sterbe" → "sterben" (bereits oben), aber auch "tot" prüfen
    if w.endswith("e") and len(w) > 3:
        verb_inf = w[:-1] + "en"
        if verb_inf not in candidates:
            candidates.append(verb_inf)

    # ── Häufige Komposita-Brücken ────────────────────────────────────────────
    # "zerstör" → auch "Zerstörer", "Zerstörung" prüfen
    # Ersetzt das Suffix statt anzuhängen
    _komposita_repl: dict[str, str] = {
        "ör": "örer",       # zerstör → Zerstörer
        "ung": "ung",      # zerstör → Zerstörung (nur anhängen)
        "bar": "er",       # zerstörbar → Zerstörer
        "lich": "keit",    # freilich → Freiheit
        "isch": "keit",    # herrlich → Herrlichkeit
    }
    for suffix, replacement in _komposita_repl.items():
        if w.endswith(suffix):
            stem = w[:-len(suffix)]
            if stem:
                candidates.append(stem + replacement)
    # Suffix-Anhängen für -ung Varianten
    if w.endswith("ung"):
        candidates.extend([w + "en", w + "e", w + "er"])
    elif w.endswith("er") and len(w) > 4:
        candidates.extend([w + "e", w + "en"])

    # Deduplizieren, Reihenfolge erhalten (ursprüngliches Wort zuerst)
    seen: set[str] = set()
    result: list[str] = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            result.append(c)
    return result


def _en_lemma_candidates(word: str) -> list[str]:
    """Small English lemmatizer for low-resource direct lookup."""
    w = _normalize_lookup(word)
    candidates = [w]

    irregular: dict[str, list[str]] = {
        "am": ["be"],
        "are": ["be"],
        "is": ["be"],
        "was": ["be"],
        "were": ["be"],
        "i'm": ["i"],
        "you're": ["you"],
        "we're": ["we"],
        "they're": ["they"],
        "don't": ["do not", "not"],
        "dont": ["do not", "not"],
        "doesn't": ["does not", "not"],
        "doesnt": ["does not", "not"],
        "didn't": ["did not", "not"],
        "didnt": ["did not", "not"],
    }
    candidates.extend(irregular.get(w, []))

    if w.endswith("ies") and len(w) > 4:
        candidates.append(w[:-3] + "y")
    if w.endswith("es") and len(w) > 3:
        candidates.append(w[:-2])
    if w.endswith("s") and len(w) > 3 and not w.endswith("ss"):
        candidates.append(w[:-1])
    if w.endswith("ing") and len(w) > 5:
        stem = w[:-3]
        candidates.extend([stem, stem + "e"])
    if w.endswith("ed") and len(w) > 4:
        stem = w[:-2]
        candidates.extend([stem, stem + "e"])

    seen: set[str] = set()
    result: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            result.append(candidate)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# FUNKTIONSWÖRTER UND TRANSFER-KLASSEN
# ─────────────────────────────────────────────────────────────────────────────

# Nur echte Funktionswörter werden stumm übersprungen. Semantische Marker
# wie Negation (nicht/kein/not/no), Ja/Nein und koordinierende Konjunktionen
# bleiben übersetzbar und werden über die YAML-Maps aufgelöst.
GERMAN_ARTICLES: frozenset[str] = frozenset({
    "der", "die", "das", "dem", "den", "des",
    "ein", "eine", "einen", "einem", "einer", "eines",
})
GERMAN_PREPOSITIONS: frozenset[str] = frozenset({
    "in", "im", "an", "am", "auf", "bei", "mit", "nach", "seit", "von",
    "vor", "zu", "zum", "zur", "durch", "für", "gegen", "ohne", "um",
    "über", "unter", "zwischen", "aus", "bis", "hinter", "neben",
})
GERMAN_AUXILIARIES: frozenset[str] = frozenset({
    "bin", "bist", "ist", "sind", "seid", "sein", "sei", "war", "waren",
    "wart", "gewesen", "habe", "hast", "hat", "haben", "habt", "hatte",
    "hatten", "werde", "wirst", "wird", "werden", "werdet", "würde",
    "würden",
})
GERMAN_MODAL_SEMANTIC: frozenset[str] = frozenset({
    "kann", "kannst", "können", "könnt", "muss", "musst", "müssen",
    "soll", "sollen", "sollst",
})
GERMAN_LIGHT_PARTICLES: frozenset[str] = frozenset({
    "auch", "nur", "schon", "noch", "doch", "sondern", "denn", "als",
    "sehr", "gar", "mal", "nun", "so",
})
GERMAN_STOP_WORDS: frozenset[str] = (
    GERMAN_ARTICLES | GERMAN_PREPOSITIONS | GERMAN_AUXILIARIES | GERMAN_LIGHT_PARTICLES
)

ENGLISH_ARTICLES: frozenset[str] = frozenset({"a", "an", "the"})
ENGLISH_PREPOSITIONS: frozenset[str] = frozenset({
    "in", "on", "at", "by", "with", "from", "for", "to", "of", "into",
    "onto", "over", "under", "between", "through", "before", "after",
    "within", "without", "as",
})
ENGLISH_AUXILIARIES: frozenset[str] = frozenset({
    "am", "are", "is", "be", "being", "been", "was", "were", "do", "does",
    "did", "have", "has", "had", "will", "would",
})
ENGLISH_MODAL_SEMANTIC: frozenset[str] = frozenset({
    "shall", "should", "can", "could", "may", "might", "must",
})
ENGLISH_LIGHT_PARTICLES: frozenset[str] = frozenset({"just", "very", "already", "still"})
ENGLISH_STOP_WORDS: frozenset[str] = (
    ENGLISH_ARTICLES | ENGLISH_PREPOSITIONS | ENGLISH_AUXILIARIES | ENGLISH_LIGHT_PARTICLES
)

STOP_WORDS_BY_LANG: dict[str, frozenset[str]] = {
    "de": GERMAN_STOP_WORDS,
    "en": ENGLISH_STOP_WORDS,
}


# ─────────────────────────────────────────────────────────────────────────────
# SENTENCE ANALYZER  (Wort-für-Wort Analyse mit Alternativen)
# ─────────────────────────────────────────────────────────────────────────────

class SentenceAnalyzer:
    """
    Analysiert Sätze Token für Token.
    Gibt für jedes Wort primäre Übersetzung + Alternativen zurück.
    """

    _WORD_RE = re.compile(r"^[\w'äöüÄÖÜß]+$", re.UNICODE)

    def __init__(self, engine: SearchEngine) -> None:
        self.engine = engine

    def is_sentence(self, text: str) -> bool:
        """True wenn der Text mehr als ein Wort enthält."""
        return len(text.strip().split()) > 1

    def _language_order(self, lang_pref: str) -> list[str]:
        primary = "en" if lang_pref == "en" else "de"
        secondary = "de" if primary == "en" else "en"
        return [primary, secondary]

    @staticmethod
    def _stop_reason(token: str, lang: str) -> str:
        low = _normalize_lookup(token)
        if lang == "en":
            if low in ENGLISH_ARTICLES:
                return "article"
            if low in ENGLISH_AUXILIARIES:
                return "auxiliary"
            if low in ENGLISH_PREPOSITIONS:
                return "preposition"
            return "function"
        if low in GERMAN_ARTICLES:
            return "Artikel"
        if low in GERMAN_AUXILIARIES:
            return "Hilfsverb"
        if low in GERMAN_PREPOSITIONS:
            return "Präposition"
        return "Funktionswort"

    def _is_stop_word(self, token: str, lang_pref: str) -> bool:
        lang = "en" if lang_pref == "en" else "de"
        return _normalize_lookup(token) in STOP_WORDS_BY_LANG[lang]

    def _lemma_candidates(self, token: str, lang: str) -> list[str]:
        return _en_lemma_candidates(token) if lang == "en" else _de_lemma_candidates(token)

    @staticmethod
    def _entry_rank(entry: dict, lang_pref: str) -> tuple[int, int, int, int]:
        lang_bonus = 10 if entry.get("lang") == lang_pref else 0
        priority = int(entry.get("priority", 0) or 0)
        source = str(entry.get("source", ""))
        source_priority = SearchEngine._SOURCE_PRIORITY.get(source, 0)
        exact_phrase = 1 if entry.get("phrase_exact") else 0
        return priority, source_priority, lang_bonus, exact_phrase

    def _find_entry_metadata(self, goauld: str, meaning_key: str, lang: str) -> Optional[dict]:
        goauld_low = _normalize_lookup(goauld)
        meaning_low = _normalize_lookup(meaning_key)
        candidates = [
            e for e in self.engine.entries
            if _normalize_lookup(str(e.get("goauld", ""))) == goauld_low
            and _normalize_lookup(str(e.get("meaning", ""))) == meaning_low
            and e.get("lang") == lang
        ]
        if not candidates:
            candidates = [
                e for e in self.engine.entries
                if _normalize_lookup(str(e.get("goauld", ""))) == goauld_low
                and e.get("lang") == lang
            ]
        if not candidates:
            return None
        return max(candidates, key=lambda e: self._entry_rank(e, lang))

    def _synthetic_map_entry(self, token: str, matched_key: str, goauld: str,
                             lang: str, confidence: float = 0.94) -> dict:
        metadata = self._find_entry_metadata(goauld, matched_key, lang)
        entry = dict(metadata) if metadata else {
            "goauld": goauld,
            "meaning": token,
            "section": "YAML primary map",
            "source": "YAML",
            "lang": lang,
        }
        entry.update({
            "goauld": goauld,
            "meaning": token,
            "lang": lang,
            "matched_key": matched_key,
            "match_type": "primary_map",
            "confidence": confidence,
        })
        return entry

    @staticmethod
    def _select_lexical_override(matched_key: str, goauld: str, lang: str,
                                 context_words: list[str]) -> str:
        """Rule-based lexical selection for high-conflict glosses."""
        del lang  # rules are currently key/context based, not UI-language based
        key = _normalize_lookup(matched_key)
        ctx = {_normalize_lookup(w) for w in context_words}

        collective = {
            "menschheit", "menschenvolk", "volk der menschen", "menschliche rasse",
            "humanity", "humankind", "human race", "human people", "race", "rasse",
        }
        generic = {
            "menschlich", "generischer mensch", "mensch als gattung", "person",
            "generic human", "human as species", "human person", "person", "human (generic)",
        }
        slave_status = {"menschlicher sklave", "sklave", "diener", "human slave", "slave", "servant"}
        human_default = {"mensch", "menschen", "human", "humans", "erdmensch", "erdmenschen"}
        if key in collective or ctx.intersection(collective):
            return "Tap'tar"
        if key in slave_status or ctx.intersection(slave_status):
            return "Lo'taur"
        if key in generic:
            return "Tar"
        if key in human_default:
            return "Tau'ri"

        if key in {"nicht", "not", "don't", "dont", "do not", "does not", "did not"}:
            return "ia"
        if key in {"kein", "keine", "keinen", "keinem", "keiner", "keines", "nein", "no", "none", "not any"}:
            return "Ka"

        if key in {"groß", "grosse", "große", "gross", "big", "large"}:
            physical_context = {
                "körper", "koerper", "physisch", "schiff", "haus", "raum", "tor",
                "body", "physical", "ship", "house", "room", "gate",
            }
            divine_context = {"gott", "goa'uld", "macht", "mächtig", "god", "power", "powerful"}
            if ctx.intersection(physical_context):
                return "Tun'le"
            if ctx.intersection(divine_context):
                return "Onak"

        return goauld

    def _lookup_primary_map(self, token: str, lang_pref: str,
                            context_words: list[str], *,
                            allow_lemma: bool) -> tuple[Optional[dict], list[dict]]:
        token_key = _normalize_lookup(token)
        for lang in self._language_order(lang_pref):
            keys = [token_key]
            if allow_lemma and " " not in token_key:
                keys = self._lemma_candidates(token_key, lang)
            for key in keys:
                goauld = PRIMARY_GOAULD_MAPS.get(lang, {}).get(key)
                if not goauld:
                    continue
                selected = self._select_lexical_override(key, goauld, lang, context_words)
                primary = self._synthetic_map_entry(token, key, selected, lang)
                alternatives: list[dict] = []
                for alt in SECONDARY_GOAULD_MAPS.get(lang, {}).get(key, [])[:5]:
                    if _normalize_lookup(alt) == _normalize_lookup(selected):
                        continue
                    alternatives.append(self._synthetic_map_entry(token, key, alt, lang, confidence=0.72))
                return primary, alternatives
        return None, []

    def _exact_engine_matches(self, phrase: str, direction: str,
                              lang_pref: str) -> list[dict]:
        """Translation-mode phrase lookup: exact only, no prefix/fuzzy."""
        phrase_low = _normalize_lookup(phrase)
        field = "goauld" if direction == "goa2de" else "meaning"
        matches = [
            e for e in self.engine.entries
            if _normalize_lookup(str(e.get(field, ""))) == phrase_low
        ]
        lang_order = self._language_order(lang_pref)

        def sort_key(entry: dict) -> tuple[int, int, int, int, int]:
            entry_lang = str(entry.get("lang", ""))
            lang_score = len(lang_order) - lang_order.index(entry_lang) if entry_lang in lang_order else 0
            priority, source_priority, lang_bonus, exact_phrase = self._entry_rank(entry, lang_pref)
            return lang_score, priority, source_priority, lang_bonus, exact_phrase

        matches.sort(key=sort_key, reverse=True)
        return matches

    def _append_skip(self, result: list[dict], token: str, lang_pref: str) -> None:
        lang = "en" if lang_pref == "en" else "de"
        result.append({
            "token": token,
            "primary": None,
            "alternatives": [],
            "found": False,
            "skipped": True,
            "skip_reason": self._stop_reason(token, lang),
            "confidence": 1.0,
        })

    def analyze(self, text: str, direction: str, lang_pref: str = "de") -> list[dict]:
        """
        Returns list of token dicts:
            token        – original word (may be a phrase if matched as unit)
            primary      – best-match entry or None
            alternatives – up to 3 further entries
            found        – True/False
            skipped      – True when a transfer-only function word was dropped

        Translation mode is deliberately stricter than SearchEngine UI mode:
        multi-word spans are consumed only by exact primary-map hits or exact
        dictionary phrases. Prefix/fuzzy matches are suggestions only, never
        automatic translation units.
        """
        raw_tokens = re.split(r"(\s+)", text.strip())
        words: list[str] = []
        for tok in raw_tokens:
            clean = tok.strip(".,!?;:()[]{}\"“”„")
            if clean and self._WORD_RE.match(clean):
                words.append(clean)

        if not words:
            return []

        max_phrase = 6
        result: list[dict] = []
        i = 0

        while i < len(words):
            matched = False
            window = min(max_phrase, len(words) - i)

            if direction == "de2goa":
                if self._is_stop_word(words[i], lang_pref):
                    self._append_skip(result, words[i], lang_pref)
                    i += 1
                    continue

                for n in range(window, 1, -1):
                    phrase = " ".join(words[i:i + n])
                    primary, alternatives = self._lookup_primary_map(
                        phrase, lang_pref, words, allow_lemma=False,
                    )
                    if primary:
                        result.append({
                            "token": phrase,
                            "primary": primary,
                            "alternatives": alternatives[:3],
                            "found": True,
                            "skipped": False,
                            "confidence": primary.get("confidence", 0.94),
                        })
                        i += n
                        matched = True
                        break

                if matched:
                    continue

                for n in range(window, 1, -1):
                    phrase = " ".join(words[i:i + n])
                    matches = self._exact_engine_matches(phrase, direction, lang_pref)
                    if matches:
                        primary = dict(matches[0])
                        primary.setdefault("match_type", "exact_phrase")
                        primary.setdefault("confidence", 0.9)
                        result.append({
                            "token": phrase,
                            "primary": primary,
                            "alternatives": matches[1:3],
                            "found": True,
                            "skipped": False,
                            "confidence": primary.get("confidence", 0.9),
                        })
                        i += n
                        matched = True
                        break

                if matched:
                    continue

                token = words[i]
                primary, alternatives = self._lookup_primary_map(
                    token, lang_pref, words, allow_lemma=True,
                )
                if not primary:
                    matches = self._exact_engine_matches(token, direction, lang_pref)
                    if matches:
                        primary = dict(matches[0])
                        primary.setdefault("match_type", "exact_token")
                        primary.setdefault("confidence", 0.86)
                        alternatives = matches[1:4]

                result.append({
                    "token": token,
                    "primary": primary,
                    "alternatives": alternatives[:3] if alternatives else [],
                    "found": primary is not None,
                    "skipped": False,
                    "confidence": primary.get("confidence", 0.0) if primary else 0.0,
                })
                i += 1
                continue

            for n in range(window, 0, -1):
                phrase = " ".join(words[i:i + n])
                matches = self._exact_engine_matches(phrase, direction, lang_pref)
                if matches:
                    primary = dict(matches[0])
                    primary.setdefault("match_type", "exact_phrase" if n > 1 else "exact_token")
                    primary.setdefault("confidence", 0.9 if n > 1 else 0.86)
                    result.append({
                        "token": phrase,
                        "primary": primary,
                        "alternatives": matches[1:4],
                        "found": True,
                        "skipped": False,
                        "confidence": primary.get("confidence", 0.9),
                    })
                    i += n
                    matched = True
                    break

            if not matched:
                result.append({
                    "token": words[i],
                    "primary": None,
                    "alternatives": [],
                    "found": False,
                    "skipped": False,
                    "confidence": 0.0,
                })
                i += 1

        return result

    @staticmethod
    def _extract_core_meaning(meaning: str) -> str:
        """
        Extrahiert die kürzeste sinnvolle Kernbedeutung aus einem Wörterbuch-Eintrag.

        Strategie:
          1. Entfernt Klammern, Markdown-Dekoratoren
          2. Splittet an mehreren Trennzeichen (;  —  /  ,)
          3. Wählt das kürzeste nicht-leere Segment ≥ 1 Wort
          4. Bereinigt Anführungszeichen und führende Sonderzeichen
        """
        m = meaning.strip()
        # Strip leading decorators/bullets
        m = re.sub(r"^[\-–▸→✦◆◉☓\s]+", "", m)
        # Remove bracketed annotations like (Pronomen), (Substantiv) etc.
        m = re.sub(r"\s*\([^)]*\)\s*", " ", m)
        # Split on major meaning separators
        segments = re.split(r"\s*[;—/,]\s*", m)
        segments = [s.strip().strip('"\'„"').strip() for s in segments if s.strip()]
        if not segments:
            return ""
        # Prefer the shortest segment (most likely the core word/phrase)
        shortest = min(segments, key=lambda s: len(s.split()))
        # If shortest is still very long (>5 words), take just the first 3 words as fallback
        words_in_shortest = shortest.split()
        if len(words_in_shortest) > 5:
            shortest = " ".join(words_in_shortest[:3]) + "…"
        return re.sub(r"\s+", " ", shortest).strip()

    @staticmethod
    def _is_canonical_entry(entry: dict) -> bool:
        tier = str(entry.get("tier", "")).lower()
        source = str(entry.get("source", "")).lower()
        return tier.startswith("canon") or source in {
            "sg1-kanon", "kanon", "kanon-ext", "rpg-lexikon",
        }

    @staticmethod
    def _apply_goauld_style(text: str) -> str:
        """Lightweight martial/register polish without changing core tokens."""
        if not text or text == "—":
            return text
        if "Tal shak!" in text and not text.endswith("Kree!"):
            return f"{text} Kree!"
        return text

    def build_translation(self, analysis: list[dict],
                          direction: str = "goa2de",
                          mode: str = "extended") -> str:
        """
        Erzeugt die kompakte Übersetzung.
        goa2de → gibt die deutsche/englische Kernbedeutung aus
        de2goa → gibt das Goa'uld-Wort aus

        Modes:
          extended     Canon + Fanon (default)
          canonical    Prefer/require canonical entries; unresolved Fanon is marked
          literal      Strict token-by-token output
          goauld_style Extended output plus light martial/register polish
        """
        parts: list[str] = []
        for item in analysis:
            # Stop words & unmatched tokens
            if item.get("skipped"):
                continue        # Artikel etc. still schweigend überspringen
            if not item["found"]:
                parts.append(f"[{item['token']}?]")
                continue

            prim = item["primary"]

            if direction == "de2goa":
                chosen = prim
                if mode == "canonical" and not self._is_canonical_entry(prim):
                    canonical_alt = next(
                        (alt for alt in item["alternatives"] if self._is_canonical_entry(alt)),
                        None,
                    )
                    if canonical_alt is None:
                        parts.append(f"[{item['token']}?]")
                        continue
                    chosen = canonical_alt
                word = chosen["goauld"].strip()
                if word:
                    parts.append(word)
            else:
                # Prefer DE-lang entries for meaning output
                best = prim
                for alt in item["alternatives"]:
                    if alt.get("lang") == "de" and prim.get("lang") != "de":
                        best = alt
                        break
                # Multi-word token = phrase match → full meaning; single token → extract core
                if " " in item["token"]:
                    # Phrase match: clean up but don't shorten
                    m = best["meaning"].strip().strip('"\'„"').strip()
                    m = re.sub(r"\s*\([^)]*\)\s*", " ", m).strip()
                    m = re.sub(r"\s+", " ", m).strip()
                else:
                    m = self._extract_core_meaning(best["meaning"])
                if m:
                    parts.append(m)
        output = " ".join(parts) if parts else "—"
        if direction == "de2goa" and mode == "goauld_style":
            return self._apply_goauld_style(output)
        return output


# ─────────────────────────────────────────────────────────────────────────────
# DEUTSCH → GOA'ULD  WÖRTERBUCH
# Wird zur Laufzeit aus dem DE-Markdown-Wörterbuch befüllt.
# Priorität vor dem Fuzzy-Engine — direkte 1:1 Übersetzungen.
# ─────────────────────────────────────────────────────────────────────────────

# Mutable module-level dicts – werden vom YAML-Loader befüllt.
# DE_GOAULD_MAP bleibt als Legacy-Alias für bestehende UI-Codepfade erhalten.
DE_GOAULD_MAP: dict[str, str] = {}
EN_GOAULD_MAP: dict[str, str] = {}
PRIMARY_GOAULD_MAPS: dict[str, dict[str, str]] = {"de": DE_GOAULD_MAP, "en": EN_GOAULD_MAP}
SECONDARY_GOAULD_MAPS: dict[str, dict[str, list[str]]] = {"de": {}, "en": {}}


# ─────────────────────────────────────────────────────────────────────────────
# TRANSLATION ENGINE  (wortweises Ersetzen für Sätze)
# ─────────────────────────────────────────────────────────────────────────────

def preserve_case(original: str, translated: str) -> str:
    if not translated:
        return translated
    if original.isupper():
        return translated.upper()
    if original[0].isupper():
        return translated[0].upper() + translated[1:]
    return translated


def build_mapping(entries: list[dict], direction: str) -> dict[str, str]:
    """Baut ein flaches {lowercase_source: target} Mapping für Wort-Übersetzung."""
    mapping: dict[str, str] = {}
    if direction == "goa2de":
        for e in entries:
            mapping[e["goauld"].lower()] = e["meaning"]
    else:
        for e in entries:
            mapping[e["meaning"].lower()] = e["goauld"]
    return mapping


def translate_text(text: str, mapping: dict[str, str],
                   direction: str = "goa2de") -> str:
    """Übersetzt einen Freitext-Satz Wort für Wort."""
    text_stripped = text.strip()
    text_lower = text_stripped.lower()

    # DE/EN→Goa'uld: kompletten Satz zuerst in den expliziten YAML-Maps prüfen
    if direction == "de2goa":
        direct = DE_GOAULD_MAP.get(text_lower) or EN_GOAULD_MAP.get(text_lower)
        if direct:
            return direct

    if text_lower in mapping:
        return preserve_case(text_stripped, mapping[text_lower])

    tokens = re.split(r"([A-Za-zÄÖÜäöüßÀ-ÿ']+)", text)
    result = []
    for tok in tokens:
        if not tok:
            continue
        if re.match(r"^[A-Za-zÄÖÜäöüßÀ-ÿ']+$", tok):
            low = tok.lower()
            if direction == "de2goa" and (low in DE_GOAULD_MAP or low in EN_GOAULD_MAP):
                result.append(DE_GOAULD_MAP.get(low) or EN_GOAULD_MAP[low])
            elif low in mapping:
                result.append(preserve_case(tok, mapping[low]))
            else:
                result.append(tok)
        else:
            result.append(tok)
    return "".join(result)


# ─────────────────────────────────────────────────────────────────────────────
# GUI  — CustomTkinter / Tkinter
# ─────────────────────────────────────────────────────────────────────────────

def _get_app_dir() -> Path:
    """
    Liefert das Verzeichnis, neben dem die .md-Wörterbücher gesucht werden.

    - Frozen (.exe, PyInstaller):  Verzeichnis der .exe-Datei.
      Mit --add-data eingebettete Ressourcen liegen zusätzlich in sys._MEIPASS.
    - Entwicklung (.py):           Verzeichnis der Quelldatei.
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def _find_one(candidates: list[str], hint: Optional[str] = None) -> Optional[str]:
    """Sucht die erste vorhandene Datei aus einer Kandidatenliste (Rückwärtskompatibilität)."""
    result = _find_all(candidates, hint)
    return result[0] if result else None


def _find_all(candidates: list[str], hint: Optional[str] = None) -> list[str]:
    """
    Sucht ALLE vorhandenen Dateien aus einer Kandidatenliste.
    Gibt eine nach Kandidaten-Reihenfolge sortierte Liste zurück; keine Duplikate.
    """
    app_dir = _get_app_dir()
    meipass = getattr(sys, '_MEIPASS', None)
    found: list[str] = []
    seen: set[str] = set()

    # Optionaler Hint zuerst
    if hint and Path(hint).is_file():
        resolved = str(Path(hint).resolve())
        if resolved not in seen:
            seen.add(resolved)
            found.append(str(hint))

    for name in candidates:
        search_paths = [
            app_dir / name,
            Path.cwd() / name,
            Path.home() / name,
        ]
        if meipass:
            search_paths.append(Path(meipass) / name)
        for p in search_paths:
            if p.is_file():
                resolved = str(p.resolve())
                if resolved not in seen:
                    seen.add(resolved)
                    found.append(str(p))
                break  # nächster Kandidat — selber Name aus verschiedenen Dirs ist derselbe

    return found


def find_md_file(hint: Optional[str] = None) -> Optional[str]:
    """Rückwärtskompatibel: sucht irgendeine MD-Datei (EN bevorzugt)."""
    return _find_one(MD_CANDIDATES, hint)


def find_md_files(hint_en: Optional[str] = None,
                  hint_de: Optional[str] = None) -> tuple[list[str], list[str]]:
    """
    Sucht ALLE EN- und DE-Wörterbuchdateien.
    Gibt ([en_paths], [de_paths]) zurück — beide können leer sein.
    Lädt also Dictionary + Fictionary und Wörterbuch + Neologikum parallel.
    """
    en = _find_all(MD_CANDIDATES_EN, hint_en)
    de = _find_all(MD_CANDIDATES_DE, hint_de)
    return en, de

def _load_lexicon() -> tuple[list[dict], list[str], dict, dict, dict, dict]:
    """
    Bevorzugter Loader: versucht zuerst goauld_lexicon.yaml, fällt bei
    Fehlen auf die vier MD-Dateien zurück. Gibt zurück:
        (entries, found_paths, de_map, en_map, secondary_de, secondary_en)
    Die letzten vier Maps sind bei MD-Fallback nur teilweise gefüllt
    (de_map kommt aus DE_GOAULD_MAP, en_map/secondary_* sind leer).
    """
    global DE_GOAULD_MAP, EN_GOAULD_MAP, PRIMARY_GOAULD_MAPS, SECONDARY_GOAULD_MAPS

    # Bevorzugt: YAML-Loader
    if YAML_LOADER_AVAILABLE:
        # Suchreihenfolge beachtet frozen-Kontext:
        #   1. EXE-Verzeichnis (neben der ausgelieferten .exe)
        #   2. _MEIPASS (PyInstaller --onefile Extrakt-Verzeichnis, enthält
        #      --add-data Ressourcen)
        # Beides explizit mitgeben — `yaml_loader` prüft darüber hinaus auch
        # CWD und sein eigenes Verzeichnis.
        search_dirs: list = [_get_app_dir()]
        _meipass = getattr(sys, '_MEIPASS', None)
        if _meipass:
            search_dirs.append(Path(_meipass))
        yaml_path = find_lexicon_yaml(search_dirs=search_dirs)
        if yaml_path:
            entries, de_map, en_map, sec_de, sec_en = load_lexicon_yaml(yaml_path)
            # Primary-Maps werden aus YAML + optionalem YAML-Overlay befüllt.
            DE_GOAULD_MAP = dict(de_map)
            EN_GOAULD_MAP = dict(en_map)
            PRIMARY_GOAULD_MAPS = {"de": DE_GOAULD_MAP, "en": EN_GOAULD_MAP}
            SECONDARY_GOAULD_MAPS = {"de": sec_de, "en": sec_en}
            log.info("Lexikon aus YAML geladen: %s (%d Einträge)",
                     yaml_path, len(entries))
            return entries, [yaml_path], de_map, en_map, sec_de, sec_en

    # Fallback: alte MD-Loader-Logik
    entries, paths = _load_mds()
    EN_GOAULD_MAP = _build_reverse_map_for_lang(entries, "en")
    PRIMARY_GOAULD_MAPS = {"de": DE_GOAULD_MAP, "en": EN_GOAULD_MAP}
    SECONDARY_GOAULD_MAPS = {"de": {}, "en": {}}
    return entries, paths, dict(DE_GOAULD_MAP), dict(EN_GOAULD_MAP), {}, {}

def _load_mds(hint_en: Optional[str] = None,
              hint_de: Optional[str] = None) -> tuple[list[dict], list[str]]:
    """
    Lädt EN- und DE-Wörterbuchdateien, gibt (alle_eintraege, gefundene_pfade) zurück.
    Befüllt außerdem das globale DE_GOAULD_MAP aus der DE-Datei.
    """
    global DE_GOAULD_MAP, EN_GOAULD_MAP, PRIMARY_GOAULD_MAPS, SECONDARY_GOAULD_MAPS
    DE_GOAULD_MAP = {}   # FIX P4a: Map vor jedem Rebuild leeren — verhindert kumulative
    EN_GOAULD_MAP = {}
    PRIMARY_GOAULD_MAPS = {"de": DE_GOAULD_MAP, "en": EN_GOAULD_MAP}
    SECONDARY_GOAULD_MAPS = {"de": {}, "en": {}}
                         # Einträge bei mehrfachem _browse_md()-Aufruf in derselben Sitzung.
    all_entries: list[dict] = []
    found_paths: list[str] = []

    en_paths, de_paths = find_md_files(hint_en, hint_de)

    # EN-Dateien (Dictionary + Fictionary + ...)
    if en_paths:
        for en_path in en_paths:
            entries = parse_markdown_dictionary(en_path)
            if entries:
                all_entries += [{**e, "lang": "en"} for e in entries]
                found_paths.append(en_path)
                log.info("EN-Wörterbuch geladen: %s  (%d Einträge)",
                         Path(en_path).name, len(entries))
            else:
                log.warning("Keine Einträge in EN-Datei: %s", en_path)
    else:
        log.info("Kein EN-Wörterbuch gefunden.")

    # DE-Dateien (Wörterbuch + Neologikum + ...)
    if de_paths:
        for de_path in de_paths:
            entries = parse_markdown_dictionary(de_path)
            if entries:
                all_entries += [{**e, "lang": "de"} for e in entries]
                found_paths.append(de_path)
                new_map = parse_de_map_from_entries([{**e, "lang": "de"} for e in entries])
                for k, v in new_map.items():
                    if k not in DE_GOAULD_MAP:
                        DE_GOAULD_MAP[k] = v
                regular = sum(1 for e in entries if not e.get("de_map"))
                map_cnt = len(new_map)
                log.info("DE-Wörterbuch geladen: %s  (%d Einträge, %d DE→Goa'uld-Mappings)",
                         Path(de_path).name, regular, map_cnt)
            else:
                log.warning("Keine Einträge in DE-Datei: %s", de_path)
    else:
        log.info("Kein DE-Wörterbuch gefunden.")

    # ── Embedded gap-filling vocabulary ──────────────────────────────────────
    # Häufige deutsche Wörter, die im Kanon-Wörterbuch fehlen.
    # Quelle: linguistische Konstruktion / Fanon-Konsens / Stargate RPG.
    # Diese werden durch MD-Einträge überschrieben (niedrigere Priorität).
    #
    # FIX P4b: Nur kanonische Großschreibung (Substantive groß, Verben klein).
    # Duplikate wie "liebe"/"Liebe" werden hier entfernt — der SearchEngine-
    # Deduplicator normalisiert per .lower(), sodass ein Eintrag reicht.
    _GAP_FILL: list[dict] = [
        # FIX 2 (translation-bugs-findings.md): "mensch" → "tau'ri" (kanonisch SG1)
        # Diese Einträge haben höchste Priorität (SG1-Kanon) und überschreiben
        # sekundäre Quellen wie Fictionary/Neologikum (tap'tar).
        {"goauld": "tau'ri",   "meaning": "mensch",           "section": "Gap-Fill", "source": "SG1-Kanon", "lang": "de", "de_map": True},
        {"goauld": "tau'ri",   "meaning": "menschen",         "section": "Gap-Fill", "source": "SG1-Kanon", "lang": "de", "de_map": True},
        {"goauld": "tau'ri",   "meaning": "human",            "section": "Gap-Fill", "source": "SG1-Kanon", "lang": "en", "de_map": False},
        {"goauld": "tau'ri",   "meaning": "humans",           "section": "Gap-Fill", "source": "SG1-Kanon", "lang": "en", "de_map": False},
        # Verwandtschaft / Family
        {"goauld": "shel'c",   "meaning": "Bruder",          "section": "Gap-Fill", "source": "Fanon/RPG", "lang": "de", "de_map": True},
        {"goauld": "shel'ca",  "meaning": "Schwester",        "section": "Gap-Fill", "source": "Fanon/RPG", "lang": "de", "de_map": True},
        {"goauld": "tel'mak",  "meaning": "Vater",            "section": "Gap-Fill", "source": "Fanon/RPG", "lang": "de", "de_map": True},
        {"goauld": "tel'ma",   "meaning": "Mutter",           "section": "Gap-Fill", "source": "Fanon/RPG", "lang": "de", "de_map": True},
        {"goauld": "shol'va",  "meaning": "Sohn",             "section": "Gap-Fill", "source": "Fanon",     "lang": "de", "de_map": True},
        {"goauld": "kresh'ta", "meaning": "Tochter",          "section": "Gap-Fill", "source": "Fanon",     "lang": "de", "de_map": True},
        # Gefühle / Emotions
        {"goauld": "pal",      "meaning": "Liebe",            "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
        {"goauld": "pal",      "meaning": "Herz",             "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
        {"goauld": "shal tek", "meaning": "Stolz",            "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
        {"goauld": "nel nem ron","meaning": "Frieden",        "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
        {"goauld": "mak shel", "meaning": "Treue",            "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
        # Handlungen / Verben
        {"goauld": "kree",     "meaning": "gehen",            "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
        {"goauld": "kel",      "meaning": "kommen",           "section": "Gap-Fill", "source": "Fanon",     "lang": "de", "de_map": True},
        {"goauld": "hol",      "meaning": "halten",           "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
        {"goauld": "tel",      "meaning": "sehen",            "section": "Gap-Fill", "source": "Fanon",     "lang": "de", "de_map": True},
        {"goauld": "nok",      "meaning": "wissen",           "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
        {"goauld": "shree",    "meaning": "eindringen",       "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
        {"goauld": "tak",      "meaning": "täuschen",         "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
        # FIX Problem 2 (translation-bugs-findings.md): "stirb" → "mel", "vernichten" → "mol kek"
        {"goauld": "mel",      "meaning": "sterbe",           "section": "Gap-Fill", "source": "SG1-Kanon", "lang": "de", "de_map": True},
        {"goauld": "mel",      "meaning": "stirb",            "section": "Gap-Fill", "source": "SG1-Kanon", "lang": "de", "de_map": True},
        {"goauld": "mel",      "meaning": "sterben",          "section": "Gap-Fill", "source": "SG1-Kanon", "lang": "de", "de_map": True},
        {"goauld": "mol kek",  "meaning": "vernichten",       "section": "Gap-Fill", "source": "SG1-Kanon", "lang": "de", "de_map": True},
        {"goauld": "mol kek",  "meaning": "vernichtet",       "section": "Gap-Fill", "source": "SG1-Kanon", "lang": "de", "de_map": True},
        {"goauld": "kek",      "meaning": "sterben",          "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
        {"goauld": "tac",      "meaning": "kämpfen",          "section": "Gap-Fill", "source": "Fanon",     "lang": "de", "de_map": True},
        {"goauld": "kalach",   "meaning": "schützen",         "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
        {"goauld": "mol kek",  "meaning": "zerstören",        "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
        # Adjektive / Eigenschaften
        {"goauld": "tal",      "meaning": "groß",             "section": "Gap-Fill", "source": "Fanon",     "lang": "de", "de_map": True},
        {"goauld": "teal'c",   "meaning": "stark",            "section": "Gap-Fill", "source": "Kanon",     "lang": "de", "de_map": True},
        {"goauld": "teal'c",   "meaning": "Stärke",           "section": "Gap-Fill", "source": "Kanon",     "lang": "de", "de_map": True},
        {"goauld": "nokia",    "meaning": "neu",              "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
        {"goauld": "shel",     "meaning": "frei",             "section": "Gap-Fill", "source": "Fanon",     "lang": "de", "de_map": True},
        {"goauld": "kek",      "meaning": "schwach",          "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
        {"goauld": "onak",     "meaning": "alle",             "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
        # Technologie / Schiffe
        {"goauld": "ha'tak",   "meaning": "Raumschiff",       "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
        {"goauld": "ha'tak",   "meaning": "Schiff",           "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
        {"goauld": "ha'tak",   "meaning": "Kriegsschiff",     "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
        {"goauld": "tel'tak",  "meaning": "Frachtschiff",     "section": "Gap-Fill", "source": "Kanon",     "lang": "de", "de_map": True},
        {"goauld": "udajeet",  "meaning": "Jäger",            "section": "Gap-Fill", "source": "Kanon",     "lang": "de", "de_map": True},
        # Orte / Substantive
        {"goauld": "a'roush",  "meaning": "Heimat",           "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
        {"goauld": "nel",      "meaning": "Weg",              "section": "Gap-Fill", "source": "Fanon",     "lang": "de", "de_map": True},
        {"goauld": "ring",     "meaning": "Tor",              "section": "Gap-Fill", "source": "Fanon",     "lang": "de", "de_map": True},
        {"goauld": "kel'sha",  "meaning": "Welt",             "section": "Gap-Fill", "source": "Fanon",     "lang": "de", "de_map": True},
        {"goauld": "onak",     "meaning": "Macht",            "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
        {"goauld": "shal tek", "meaning": "Ehre",             "section": "Gap-Fill", "source": "Kanon",     "lang": "de", "de_map": True},
        {"goauld": "kel mar",  "meaning": "Rache",            "section": "Gap-Fill", "source": "Kanon",     "lang": "de", "de_map": True},
        {"goauld": "kalach",   "meaning": "heilig",           "section": "Gap-Fill", "source": "Kanon-ext", "lang": "de", "de_map": True},
    ]

    # Merge: existing DE_MAP takes priority — only add gap entries if key not yet known
    gap_map = parse_de_map_from_entries(_GAP_FILL)
    for k, v in gap_map.items():
        if k not in DE_GOAULD_MAP:
            DE_GOAULD_MAP[k] = v

    # Add gap entries to the main pool so they appear in search results too
    all_entries = _GAP_FILL + all_entries  # low priority (prepended, MD wins via dedup)
    EN_GOAULD_MAP = _build_reverse_map_for_lang(all_entries, "en")
    PRIMARY_GOAULD_MAPS = {"de": DE_GOAULD_MAP, "en": EN_GOAULD_MAP}
    SECONDARY_GOAULD_MAPS = {"de": {}, "en": {}}

    if not all_entries:
        log.error("Kein Vokabular geladen — bitte Wörterbuch-Dateien prüfen.")

    return all_entries, found_paths


class GoauldApp:
    """
    Haupt-GUI-Anwendung.  Läuft mit CustomTkinter (bevorzugt) oder
    Standard-Tkinter als Fallback.
    """

    # ─── Initialisierung ─────────────────────────────────────────────────────

    def __init__(self, md_path: Optional[str] = None) -> None:
        self._all_entries: list[dict] = []
        self._md_paths: list[str] = []
        # Secondary-Maps für "auch:"-UI — werden von _load_mds_app befüllt,
        # hier vorinitialisiert, damit die UI-Routinen (_run_live_translation,
        # _show_sentence_detail) sie sicher ansprechen können.
        self._secondary_de: dict[str, list[str]] = {}
        self._secondary_en: dict[str, list[str]] = {}
        self._load_mds_app(md_path)
        self._engine = SearchEngine(self._all_entries)
        self._analyzer = SentenceAnalyzer(self._engine)
        self._direction = "goa2de"
        self._lang_pref: str = "de"          # DE = Deutsch bevorzugt
        self._translation_mode: str = "extended"
        self._search_after_id: Optional[str] = None
        self._selected_entry: Optional[dict] = None
        self._sentence_mode: bool = False
        self._build_gui()

    # ─── Datenladen ──────────────────────────────────────────────────────────

    def _load_mds_app(self, hint: Optional[str] = None) -> None:
        """Lädt Lexikon. Mit explizitem `hint` → MD-Modus (User zeigt auf
        eine bestimmte Datei). Ohne hint → YAML bevorzugt, MD als Fallback.
        Füllt _all_entries, _md_paths sowie die Secondary-Maps für die UI."""
        if hint:
            # Expliziter MD-Pfad → klassischer MD-Loader (kein YAML-Lookup)
            entries, paths = _load_mds(hint_en=hint)
            secondary_de: dict[str, list[str]] = {}
            secondary_en: dict[str, list[str]] = {}
        else:
            entries, paths, _de_map, _en_map, secondary_de, secondary_en = _load_lexicon()
        self._all_entries  = entries
        self._md_paths     = paths
        self._secondary_de = secondary_de
        self._secondary_en = secondary_en

    def _get_secondary_alts(self, token: str, primary_goauld: str = "") -> list[str]:
        """Alternative Goa'uld-Übersetzungen für einen Quell-Token (nur bei
        DE/EN → Goa'uld sinnvoll).

        Respektiert `lang_pref`: EN-Nutzer bekommen zuerst die EN-Secondary-
        Map, DE-Nutzer die DE-Map; die jeweils andere dient als Fallback
        (z. B. englische Lehnwörter in deutschen Sätzen oder umgekehrt).

        Der Primärtreffer wird — falls übergeben — aus der Liste entfernt,
        damit die UI ihn nicht redundant als „auch:"-Alternative zeigt.
        """
        key = token.lower().strip()
        if self._lang_pref == "en":
            alts = self._secondary_en.get(key) or self._secondary_de.get(key, [])
        else:
            alts = self._secondary_de.get(key) or self._secondary_en.get(key, [])
        if primary_goauld:
            pg = primary_goauld.lower().strip()
            alts = [a for a in alts if a.lower() != pg]
        return alts

    # Legacy-Alias für den Datei-Browser (wird weiter unten aufgerufen)
    @property
    def _md_path(self) -> Optional[str]:
        """Erster gefundener Pfad – für Statusanzeige."""
        return self._md_paths[0] if self._md_paths else None

    # ─── GUI-Aufbau ──────────────────────────────────────────────────────────

    def _build_gui(self) -> None:
        if CTK_AVAILABLE:
            self._build_ctk()
        else:
            self._build_tk()

    # ── CustomTkinter variant ─────────────────────────────────────────────────

    def _build_ctk(self) -> None:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.root = ctk.CTk()
        self.root.title("GOA'ULD LINGUISTIC INTERFACE — SGC")
        self.root.geometry("1100x760")
        self.root.minsize(900, 600)
        self.root.configure(fg_color=C["bg_root"])

        self._build_classification_bar_ctk()
        self._build_header_ctk()
        self._build_controls_ctk()
        self._build_main_ctk()
        self._build_statusbar_ctk()
        self._update_status()

    def _build_classification_bar_ctk(self) -> None:
        """TOP SECRET // SCI Klassifizierungsleiste — dauerhaft rot (SGC-Konvention)."""
        bar = ctk.CTkFrame(self.root, fg_color=C["class_bg"],
                           corner_radius=0, height=20,
                           border_width=0)
        bar.pack(fill="x", padx=0, pady=0)
        bar.pack_propagate(False)

        # Untere Trennlinie
        ctk.CTkFrame(self.root, fg_color=C["class_border"],
                     corner_radius=0, height=1).pack(fill="x", padx=0, pady=0)

        # Links: Blocks + Text
        left = ctk.CTkFrame(bar, fg_color="transparent")
        left.pack(side="left", padx=10)
        ctk.CTkLabel(
            left,
            text="■ ■ ■   TOP SECRET // SCI // STARGATE COMMAND   ■ ■ ■",
            font=("Courier", 10, "bold"),
            text_color=C["class_text"],
        ).pack(side="left")

        # Rechts: Clearance
        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right", padx=10)
        ctk.CTkLabel(
            right,
            text="CLEARANCE LEVEL 28 REQUIRED",
            font=("Courier", 10, "bold"),
            text_color=C["class_text"],
        ).pack(side="right")

    def _build_header_ctk(self) -> None:
        """SGC-Kommandoterminal Header mit animierten Chevron, Event-Horizon und Status-Badges."""
        hdr = ctk.CTkFrame(self.root, fg_color=C["bg_panel"],
                           corner_radius=0, height=110)
        hdr.pack(fill="x", padx=0, pady=0)
        hdr.pack_propagate(False)

        # ── Linke Chevron-Spalte (animiert) ──────────────────────────────
        self._chev_buttons = []
        chev_frame = ctk.CTkFrame(hdr, fg_color="transparent", width=50)
        chev_frame.pack(side="left", padx=(10, 0))
        chev_frame.pack_propagate(False)
        for i in range(7):
            btn = ctk.CTkButton(
                chev_frame, text="◆", font=("Courier", 8),
                fg_color="transparent", text_color=C["chevron"],
                hover_color=C["bg_panel"], width=16, height=10,
                corner_radius=0, border_width=0
            )
            btn.pack(pady=1)
            self._chev_buttons.append(btn)

        # ── Zentrale Titel-Sektion mit Event-Horizon ─────────────────────
        title_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        title_frame.pack(side="left", padx=(10, 0), expand=True)

        # Pulsierender Event-Horizon-Glow (simuliert)
        self._eh_glow = ctk.CTkLabel(
            title_frame, text="⊕", font=("Courier", 28, "bold"),
            text_color=C["blue_gate"]
        )
        self._eh_glow.pack(anchor="n", pady=(6, 0))
        self._eh_phase = 0

        ctk.CTkLabel(
            title_frame,
            text="GOA'ULD LINGUISTIC INTERFACE",
            font=("Courier", 18, "bold"),
            text_color=C["gold_bright"],
        ).pack(anchor="w", pady=(2, 0))

        ctk.CTkLabel(
            title_frame,
            text="SGC XENOLINGUISTICS DIV  ·  SG-1 OPS  ·  FACILITY: CHEYENNE MOUNTAIN",
            font=("Courier", 9),
            text_color=C["text_blue"],
        ).pack(anchor="w")

        # ── Rechte Status-Sektion ────────────────────────────────────────
        status_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        status_frame.pack(side="right", padx=(10, 10))

        # Wormhole Status Badge — top
        self._wormhole_var = ctk.StringVar(value="◎  WORMHOLE ESTABLISHED")
        self._wormhole_lbl = ctk.CTkLabel(
            status_frame,
            textvariable=self._wormhole_var,
            font=("Courier", 10, "bold"),
            text_color=C["phosphor_grn"],
        )
        self._wormhole_lbl.pack(anchor="e")

        # Operator-ID
        self._operator_var = ctk.StringVar(value="◈ OPERATOR: CIV-01 / JACKSON-D")
        ctk.CTkLabel(
            status_frame,
            textvariable=self._operator_var,
            font=("Courier", 9),
            text_color=C["mil_amber"],
        ).pack(anchor="e")

        # Stardate / Zulu-Zeit (einmal beim Start gesetzt — keine Animation)
        from datetime import datetime, timezone
        _now = datetime.now(timezone.utc)
        _doy = _now.timetuple().tm_yday
        _stardate = f"⧗ STARDATE {_now.year}.{_doy:03d}  ·  {_now.strftime('%H%M')} ZULU"
        ctk.CTkLabel(
            status_frame,
            text=_stardate,
            font=("Courier", 9),
            text_color=C["text_blue"],
        ).pack(anchor="e")

        # Lexikon-Counter  (wird per _entry_count_var aktualisiert)
        self._entry_count_var = ctk.StringVar(value="▸ LEXICON: — ENTRIES")
        ctk.CTkLabel(
            status_frame,
            textvariable=self._entry_count_var,
            font=("Courier", 9),
            text_color=C["mil_text_dim"],
        ).pack(anchor="e")

        # MD-Datei Badge
        src_text = ("◈ MD: " + Path(self._md_paths[0]).name[:28]
                    if self._md_paths else "◈ MD: KEIN WÖRTERBUCH")
        self._md_lbl = ctk.CTkLabel(
            status_frame,
            text=src_text,
            font=("Courier", 8),
            text_color=C["text_lo"],
        )
        self._md_lbl.pack(anchor="e")

        # Rechte Gate-Dekoration
        ctk.CTkLabel(hdr, text="⊕", font=("Courier", 34, "bold"),
                     text_color=C["blue_dim"]).pack(side="right", padx=(4, 6))

        # Animation starten
        self._animate_header_ctk()

    def _animate_header_ctk(self) -> None:
        """Pulsierender Event-Horizon und Chevron-Pulsation."""
        if not hasattr(self, '_chev_buttons'):
            return
        # Chevron pulsierend
        _base = C["chevron"]
        for i, btn in enumerate(self._chev_buttons):
            phase = (self._eh_phase + i) % 5
            if phase < 2:
                btn.configure(text_color=C["gold"])
            else:
                btn.configure(text_color=C["chevron"])
        # Event-Horizon Glow
        glow_color = C["blue_bright"] if self._eh_phase % 3 == 0 else C["blue_gate"]
        self._eh_glow.configure(text_color=glow_color)
        self._eh_phase = (self._eh_phase + 1) % 15
        self.root.after(500, self._animate_header_ctk)

    def _build_controls_ctk(self) -> None:
        """SGC-Eingabespalte mit EINGABE-Label und Direction-Toggle darunter."""
        # Haupt-Control-Leiste (höher für zwei Zeilen)
        ctrl = ctk.CTkFrame(self.root, fg_color=C["bg_panel"],
                            corner_radius=0, height=80)
        ctrl.pack(fill="x", padx=0, pady=(1, 0))
        ctrl.pack_propagate(False)

        # ── Zeile 1: EINGABE-Feld ────────────────────────────────────────
        inp_frame = ctk.CTkFrame(ctrl, fg_color="transparent")
        inp_frame.pack(fill="x", padx=14, pady=(8, 2))

        # "▸ INPUT" Label
        ctk.CTkLabel(
            inp_frame, text="▸ INPUT",
            font=("Courier", 10, "bold"),
            text_color=C["orange"]
        ).pack(side="left", padx=(0, 8))

        # Search icon
        ctk.CTkLabel(inp_frame, text="◎", text_color=C["orange"],
                     font=("Courier", 14)).pack(side="left", padx=(0, 4))

        # Search entry
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search_change)
        self._entry = ctk.CTkEntry(
            inp_frame,
            textvariable=self._search_var,
            placeholder_text="Jaffa, kree!  —  Deutsch, Englisch oder Goa'uld …",
            font=("Courier", 13),
            fg_color=C["bg_input"],
            border_color=C["gold_dim"],
            text_color=C["text_hi"],
            placeholder_text_color=C["text_lo"],
            border_width=1,
            corner_radius=2,
            height=30,
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=(4, 4))
        self._entry.bind("<Escape>", lambda e: self._search_var.set(""))
        self._entry.bind("<Return>", lambda e: self._do_search())

        # Load MD Button (rechts)
        ctk.CTkButton(
            inp_frame,
            text="📂",
            width=36,
            height=30,
            fg_color=C["bg_card"],
            hover_color=C["bg_hover"],
            text_color=C["text_mid"],
            font=("Courier", 10),
            corner_radius=4,
            command=self._browse_md,
        ).pack(side="left", padx=(4, 0))

        # ── Zeile 2: Direction-Toggle + Language-Pref ────────────────────
        btn_frame = ctk.CTkFrame(ctrl, fg_color="transparent")
        btn_frame.pack(fill="x", padx=14, pady=(2, 6))

        # Direction toggle
        self._dir_var = ctk.StringVar(value="de2goa")
        seg = ctk.CTkSegmentedButton(
            btn_frame,
            values=["  DE/EN → Goa'uld  ",
                    "  Goa'uld → DE/EN  "],
            variable=self._dir_var,
            command=self._on_direction_change,
            fg_color=C["bg_card"],
            selected_color=C["gold_dim"],
            selected_hover_color=C["gold"],
            unselected_color=C["bg_card"],
            unselected_hover_color=C["bg_hover"],
            text_color=C["text_hi"],
            text_color_disabled=C["text_mid"],
            font=("Courier", 10, "bold"),
        )
        seg.pack(side="left", padx=(0, 8))
        seg.set("  DE/EN → Goa'uld  ")
        self._direction = "de2goa"

        # Language preference toggle (DE / EN)
        self._lang_btn_var = ctk.StringVar(value="🇩🇪 DE")
        self._lang_btn = ctk.CTkButton(
            btn_frame,
            textvariable=self._lang_btn_var,
            width=58,
            height=28,
            fg_color=C["locked_dim"],
            hover_color=C["locked"],
            text_color=C["locked_bright"],
            font=("Courier", 10, "bold"),
            corner_radius=4,
            command=self._toggle_lang_pref,
        )
        self._lang_btn.pack(side="left", padx=(0, 8))

        # Output mode selector (Canon / Extended / Literal / Goa'uld style)
        self._mode_label_to_value = {
            "Kanonisch": "canonical",
            "Erweitert": "extended",
            "Literal": "literal",
            "Goa'uld-Stil": "goauld_style",
        }
        self._mode_var = ctk.StringVar(value="Erweitert")
        self._mode_menu = ctk.CTkOptionMenu(
            btn_frame,
            values=list(self._mode_label_to_value.keys()),
            variable=self._mode_var,
            command=self._on_mode_change,
            width=122,
            height=28,
            fg_color=C["bg_card"],
            button_color=C["gold_dim"],
            button_hover_color=C["gold"],
            text_color=C["text_hi"],
            font=("Courier", 10, "bold"),
        )
        self._mode_menu.pack(side="left", padx=(0, 8))

        # Clear button
        ctk.CTkButton(
            btn_frame,
            text="✕",
            width=30,
            height=28,
            fg_color=C["bg_card"],
            hover_color=C["bg_hover"],
            text_color=C["gold_dim"],
            font=("Courier", 12),
            corner_radius=4,
            command=lambda: self._search_var.set(""),
        ).pack(side="left")

    def _build_main_ctk(self) -> None:
        """SGC-Hauptbereich: Links Ergebnisliste (450px), rechts Tabs + Live-Übersetzung."""
        # ── Resizable PanedWindow (horizontal sash) ───────────────────────
        self._paned = tk.PanedWindow(
            self.root,
            orient="horizontal",
            bg=C["blue_gate"],
            sashrelief="flat",
            sashwidth=6,
            sashpad=2,
            showhandle=False,
            bd=0,
        )
        self._paned.pack(fill="both", expand=True)

        # ── LEFT: Results panel (450px min, breiter) ──────────────────────
        left_outer = tk.Frame(self._paned, bg=C["bg_panel"])
        self._paned.add(left_outer, minsize=400, width=450, stretch="never")

        left = ctk.CTkFrame(left_outer, fg_color=C["bg_panel"], corner_radius=0)
        left.pack(fill="both", expand=True)
        left.rowconfigure(3, weight=1)
        left.columnconfigure(0, weight=1)

        ctk.CTkFrame(left, fg_color=C["blue_gate"],
                     corner_radius=0, height=2).grid(row=0, column=0, sticky="ew")

        # ── Left panel header (Intel Feed) ──────────────────────────────
        hdr_frame = ctk.CTkFrame(left, fg_color=C["bg_panel"], corner_radius=0)
        hdr_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=0)
        hdr_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr_frame,
            text=f"  {GLYPH_GATE}  INTERCEPT FEED",
            font=("Courier", 10, "bold"),
            text_color=C["blue_bright"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(4, 2))

        # Treffer-Counter rechts
        self._intel_count_var = ctk.StringVar(value="0 HITS")
        ctk.CTkLabel(
            hdr_frame,
            textvariable=self._intel_count_var,
            font=("Courier", 9, "bold"),
            text_color=C["mil_text_dim"],
            anchor="e",
        ).grid(row=0, column=1, sticky="e", padx=8, pady=(4, 2))

        # Blaue Trennlinie unter Intel-Feed-Header
        ctk.CTkFrame(left, fg_color=C["blue_gate"],
                     corner_radius=0, height=1).grid(row=2, column=0, sticky="ew")

        self._result_scroll = ctk.CTkScrollableFrame(
            left, fg_color=C["bg_panel"], corner_radius=0)
        self._result_scroll.grid(row=3, column=0, sticky="nsew")
        self._result_scroll.columnconfigure(0, weight=1)
        self._result_rows: list[ctk.CTkFrame | ctk.CTkLabel] = []

        # ── RIGHT: Tabs oben + Live-Übersetzung unten ─────────────────────
        right_outer = tk.Frame(self._paned, bg=C["bg_card"])
        self._paned.add(right_outer, minsize=400, stretch="always")

        right = ctk.CTkFrame(right_outer, fg_color=C["bg_card"], corner_radius=0)
        right.pack(fill="both", expand=True)
        right.rowconfigure(0, weight=0)   # Tabs
        right.rowconfigure(1, weight=1)   # Live-Übersetzung

        ctk.CTkFrame(right, fg_color=C["gold_dim"],
                     corner_radius=0, height=2).pack(fill="x")

        # Tabs (nur Detail + Satzanalyse, Übersetzer wird unten angezeigt)
        self._tabs = ctk.CTkTabview(
            right,
            fg_color=C["bg_card"],
            segmented_button_fg_color=C["bg_panel"],
            segmented_button_selected_color=C["gold_dim"],
            segmented_button_selected_hover_color=C["gold"],
            segmented_button_unselected_color=C["bg_panel"],
            segmented_button_unselected_hover_color=C["bg_hover"],
            text_color=C["text_hi"],
            text_color_disabled=C["text_mid"],
        )
        self._tabs.pack(fill="x", padx=6, pady=(4, 0))
        self._tabs.add("  ◈ BRIEFING  ")
        self._tabs.add("  ⊕ DEBRIEF  ")

        # Tab-Separator
        ctk.CTkFrame(right, fg_color=C["gold_dim"],
                     corner_radius=0, height=1).pack(fill="x", padx=6, pady=(0, 0))

        # Detail tab
        detail_tab = self._tabs.tab("  ◈ BRIEFING  ")
        self._detail_text = ctk.CTkTextbox(
            detail_tab,
            fg_color=C["bg_card"],
            text_color=C["text_hi"],
            font=("Courier", 11),
            border_width=0, corner_radius=0,
            state="disabled", wrap="word",
        )
        self._detail_text.pack(fill="both", expand=True, padx=2, pady=2)

        # Satzanalyse tab
        sentence_tab = self._tabs.tab("  ⊕ DEBRIEF  ")
        self._sentence_text = ctk.CTkTextbox(
            sentence_tab,
            fg_color=C["bg_card"],
            text_color=C["text_hi"],
            font=("Courier", 11),
            border_width=0, corner_radius=0,
            state="disabled", wrap="word",
        )
        self._sentence_text.pack(fill="both", expand=True, padx=2, pady=2)

        # ── LIVE-ÜBERSETZUNG (immer sichtbar, unten) ──────────────────────
        live_frame = ctk.CTkFrame(right, fg_color=C["bg_card"], corner_radius=0)
        live_frame.pack(fill="both", expand=True, padx=6, pady=(4, 6))
        live_frame.rowconfigure(0, weight=0)
        live_frame.rowconfigure(1, weight=0)
        live_frame.rowconfigure(2, weight=1)
        live_frame.columnconfigure(0, weight=1)

        # Header: ⚡ LIVE-ÜBERSETZUNG + Status
        live_hdr = ctk.CTkFrame(live_frame, fg_color=C["blue_dim"], corner_radius=4)
        live_hdr.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 4))
        live_hdr.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            live_hdr,
            text="  ⚡ LIVE-TRANSMISSION  ·  OUTGOING",
            font=("Courier", 10, "bold"),
            text_color=C["gold_bright"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=8, pady=4)

        self._trans_status_lbl = ctk.CTkLabel(
            live_hdr, text="◉ SIGNAL LOCKED",
            font=("Courier", 9, "bold"),
            text_color=C["phosphor_grn"], anchor="e",
        )
        self._trans_status_lbl.grid(row=0, column=1, sticky="e", padx=8, pady=4)

        # Output-Bereich (groß, Gold-Highlight)
        self._trans_output = ctk.CTkTextbox(
            live_frame,
            fg_color=C["bg_input"],
            text_color=C["gold_bright"],
            font=("Courier", 14, "bold"),
            border_width=1,
            corner_radius=4,
            state="disabled",
            wrap="word",
        )
        self._trans_output.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 4))

        # Token-Breakdown (kleinere Schrift)
        self._trans_token_lbl = ctk.CTkLabel(
            live_frame,
            text="── ⊞ TOKEN BREAKDOWN ──",
            font=("Courier", 8, "bold"),
            text_color=C["gold_dim"],
        )
        self._trans_token_lbl.grid(row=2, column=0, sticky="ew", pady=(0, 2))

        self._trans_token_text = ctk.CTkTextbox(
            live_frame,
            fg_color=C["bg_card"],
            text_color=C["text_hi"],
            font=("Courier", 10),
            border_width=0,
            corner_radius=0,
            state="disabled",
            wrap="word",
        )
        self._trans_token_text.grid(row=3, column=0, sticky="nsew", pady=(0, 0))
        live_frame.rowconfigure(3, weight=1)

        self._trans_after_id: Optional[str] = None

        self._show_welcome_detail()

    def _build_statusbar_ctk(self) -> None:
        # Gold-Trennlinie ÜBER der Statusbar
        ctk.CTkFrame(self.root, fg_color=C["gold_dim"],
                     corner_radius=0, height=1).pack(fill="x", side="bottom")

        bar = ctk.CTkFrame(self.root, fg_color=C["bg_root"],
                           corner_radius=0, height=24)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        # DEFCON / Status-Prefix (links, fest)
        ctk.CTkLabel(
            bar,
            text="▽ DEFCON 3",
            font=("Courier", 9, "bold"),
            text_color=C["mil_amber"],
        ).pack(side="left", padx=(12, 14))

        # Haupt-Status (dynamisch)
        self._status_var = ctk.StringVar(value="")
        ctk.CTkLabel(
            bar,
            textvariable=self._status_var,
            font=("Courier", 9),
            text_color=C["text_mid"],
            anchor="w",
        ).pack(side="left", padx=0)

        # Rechts: Version
        ctk.CTkLabel(
            bar,
            text="▸ v0.2.6",
            font=("Courier", 9, "bold"),
            text_color=C["gold"],
        ).pack(side="right", padx=(6, 12))

        # MD-Datei
        md_name = (Path(self._md_paths[0]).name if self._md_paths else "NO LEXICON")
        ctk.CTkLabel(
            bar,
            text=f"◈ MD: {md_name}",
            font=("Courier", 9),
            text_color=C["text_lo"],
        ).pack(side="right", padx=6)

        # Scanline-Overlay (nur bei CustomTkinter)
        self._create_scanline_overlay()

    def _create_scanline_overlay(self) -> None:
        """Erzeugt ein Scanline-Overlay über die gesamte GUI (CRT-Monitor-Look)."""
        if not CTK_AVAILABLE:
            return

        # Canvas wird nach dem ersten Pack aktualisiert
        self.root.after(500, self._draw_scanlines)

    def _draw_scanlines(self) -> None:
        """Zeichnet horizontale Scanline-Linien über die gesamte GUI."""
        try:
            width = self.root.winfo_width()
            height = self.root.winfo_height()
        except Exception:
            width, height = 1100, 720

        self._scanline_canvas = tk.Canvas(
            self.root,
            width=max(width, 800),
            height=max(height, 550),
            bg=C["bg_root"],
            highlightthickness=0,
            bd=0,
        )
        self._scanline_canvas.place(x=0, y=0,
                                    width=max(width, 800),
                                    height=max(height, 550))

        # Zeichne horizontale Linien (alle 3px) — Tkinter-freundlich
        scanline_color = "#101820"  # Dunkles Panel-Farbe für subtile Scanlines
        for y in range(0, max(height, 550), 3):
            self._scanline_canvas.create_line(
                0, y, max(width, 800), y,
                fill=scanline_color, width=1
            )

    # ─── Standard Tkinter variant ─────────────────────────────────────────────

    def _build_tk(self) -> None:
        self.root = tk.Tk()
        self.root.title("GOA'ULD LINGUISTIC INTERFACE — SGC")
        self.root.geometry("1100x720")
        self.root.minsize(800, 550)
        self.root.configure(bg=C["bg_root"])

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TScrollbar", background=C["bg_card"],
                        troughcolor=C["bg_panel"], arrowcolor=C["gold_dim"])

        self._build_header_tk()
        self._build_controls_tk()
        self._build_main_tk()
        self._build_statusbar_tk()
        self._update_status()

    def _build_header_tk(self) -> None:
        """SGC-Kommandoterminal Header (Tkinter-Fallback)."""
        hdr = tk.Frame(self.root, bg=C["bg_panel"], height=90)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # Linke Chevron-Spalte
        chev_frame = tk.Frame(hdr, bg=C["bg_panel"])
        chev_frame.pack(side="left", padx=(10, 0))
        for i in range(7):
            tk.Label(chev_frame, text="◆", bg=C["bg_panel"], fg=C["chevron"],
                     font=("Courier", 8)).pack(pady=1)

        # Gate-Symbol
        tk.Label(hdr, text="⊕", bg=C["bg_panel"], fg=C["blue_gate"],
                 font=("Courier", 28)).pack(side="left", padx=(10, 0))

        # Zentrale Titel-Sektion
        tf = tk.Frame(hdr, bg=C["bg_panel"])
        tf.pack(side="left", padx=(10, 0), expand=True)

        tk.Label(tf, text="⊕", bg=C["bg_panel"], fg=C["blue_gate"],
                 font=("Courier", 28, "bold")).pack(anchor="n")
        tk.Label(tf, text="GOA'ULD LINGUISTIC INTERFACE",
                 bg=C["bg_panel"], fg=C["gold_bright"],
                 font=("Courier", 18, "bold")).pack(anchor="w")
        tk.Label(tf, text="SGC Xenolinguistics  ·  LEVEL 28",
                 bg=C["bg_panel"], fg=C["text_blue"],
                 font=("Courier", 9)).pack(anchor="w")

        # Rechte Status-Sektion
        rf = tk.Frame(hdr, bg=C["bg_panel"])
        rf.pack(side="right", padx=(10, 0))

        self._entry_count_var = tk.StringVar()
        tk.Label(rf, textvariable=self._entry_count_var,
                 bg=C["bg_panel"], fg=C["locked_bright"],
                 font=("Courier", 9, "bold")).pack(anchor="e")

        self._wormhole_var = tk.StringVar(value="◎  WORMHOLE ESTABLISHED")
        tk.Label(rf, textvariable=self._wormhole_var,
                 bg=C["bg_panel"], fg=C["sgc_green"],
                 font=("Courier", 10, "bold")).pack(anchor="e")

        src_text = ("◈ MD: " + Path(self._md_paths[0]).name[:25]
                    if self._md_paths else "◈ MD: KEIN WÖRTERBUCH")
        tk.Label(rf, text=src_text, bg=C["bg_panel"], fg=C["text_lo"],
                 font=("Courier", 8)).pack(anchor="e")

        tk.Label(hdr, text="⊕", bg=C["bg_panel"], fg=C["blue_dim"],
                 font=("Courier", 34, "bold")).pack(side="right", padx=(0, 10))

    def _build_controls_tk(self) -> None:
        """SGC-Eingabespalte (Tkinter-Fallback)."""
        ctrl = tk.Frame(self.root, bg=C["bg_panel"], height=80)
        ctrl.pack(fill="x", pady=(1, 0))
        ctrl.pack_propagate(False)

        # Zeile 1: EINGABE-Feld
        inp_frame = tk.Frame(ctrl, bg=C["bg_panel"])
        inp_frame.pack(fill="x", padx=14, pady=(8, 2))

        tk.Label(inp_frame, text="EINGABE:", bg=C["bg_panel"], fg=C["gold_dim"],
                 font=("Courier", 10, "bold")).pack(side="left", padx=(0, 8))
        tk.Label(inp_frame, text="◎", bg=C["bg_panel"], fg=C["orange"],
                 font=("Courier", 14)).pack(side="left", padx=(0, 4))

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search_change)
        self._entry = tk.Entry(
            inp_frame,
            textvariable=self._search_var,
            bg=C["bg_input"],
            fg=C["text_hi"],
            insertbackground=C["gold"],
            font=("Courier", 13),
            relief="flat",
            bd=0,
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=(4, 4))
        self._entry.bind("<Escape>", lambda e: self._search_var.set(""))

        tk.Button(
            inp_frame,
            text="📂",
            bg=C["bg_card"],
            fg=C["text_mid"],
            activebackground=C["bg_hover"],
            activeforeground=C["text_hi"],
            font=("Courier", 10),
            relief="flat",
            bd=0,
            padx=8, pady=4,
            command=self._browse_md,
        ).pack(side="left", padx=(4, 0))

        # Zeile 2: Direction-Toggle + Buttons
        btn_frame = tk.Frame(ctrl, bg=C["bg_panel"])
        btn_frame.pack(fill="x", padx=14, pady=(2, 6))

        self._dir_var = tk.StringVar(value="de2goa")

        tk.Radiobutton(
            btn_frame,
            text="  DE/EN → Goa'uld  ",
            variable=self._dir_var,
            value="de2goa",
            command=self._on_direction_change,
            bg=C["bg_card"],
            fg=C["text_hi"],
            selectcolor=C["gold_dim"],
            activebackground=C["bg_hover"],
            activeforeground=C["gold_bright"],
            font=("Courier", 10),
            indicatoron=False,
            relief="flat",
            bd=0,
            padx=10, pady=6,
        ).pack(side="left", padx=(0, 2))

        tk.Radiobutton(
            btn_frame,
            text="  Goa'uld → DE/EN  ",
            variable=self._dir_var,
            value="goa2de",
            command=self._on_direction_change,
            bg=C["bg_card"],
            fg=C["text_hi"],
            selectcolor=C["gold_dim"],
            activebackground=C["bg_hover"],
            activeforeground=C["gold_bright"],
            font=("Courier", 10),
            indicatoron=False,
            relief="flat",
            bd=0,
            padx=10, pady=6,
        ).pack(side="left", padx=2)

        tk.Button(
            btn_frame,
            text="✕",
            bg=C["bg_card"],
            fg=C["gold_dim"],
            activebackground=C["bg_hover"],
            activeforeground=C["gold"],
            font=("Courier", 11),
            relief="flat",
            bd=0,
            padx=8, pady=4,
            command=lambda: self._search_var.set(""),
        ).pack(side="left", padx=(10, 0))

    def _build_main_tk(self) -> None:
        """SGC-Hauptbereich (Tkinter-Fallback)."""
        main = tk.Frame(self.root, bg=C["bg_root"])
        main.pack(fill="both", expand=True, pady=(1, 0))

        # Results panel (450px breit)
        left = tk.Frame(main, bg=C["bg_panel"], width=450)
        left.pack(side="left", fill="both")
        left.pack_propagate(False)

        tk.Label(left, text=f"  {GLYPH_SECTION} ERGEBNISSE",
                 bg=C["bg_panel"], fg=C["gold"],
                 font=("Courier", 10, "bold"), anchor="w").pack(
            fill="x", padx=6, pady=(6, 2))

        list_frame = tk.Frame(left, bg=C["bg_panel"])
        list_frame.pack(fill="both", expand=True)

        self._listbox = tk.Listbox(
            list_frame,
            bg=C["bg_panel"],
            fg=C["text_hi"],
            selectbackground=C["bg_select"],
            selectforeground=C["gold_bright"],
            activestyle="none",
            font=("Courier", 11),
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        sb = ttk.Scrollbar(list_frame, orient="vertical",
                           command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=sb.set)
        self._listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._listbox.bind("<<ListboxSelect>>", self._on_listbox_select)
        self._tk_results: list[dict] = []

        # Detail panel
        right = tk.Frame(main, bg=C["bg_card"])
        right.pack(side="right", fill="both", expand=True, padx=(1, 0))

        tk.Label(right, text=f"  {GLYPH_SECTION} DETAILANSICHT",
                 bg=C["bg_card"], fg=C["gold"],
                 font=("Courier", 10, "bold"), anchor="w").pack(
            fill="x", padx=6, pady=(6, 2))

        detail_frame = tk.Frame(right, bg=C["bg_card"])
        detail_frame.pack(fill="both", expand=True)

        self._detail_text = tk.Text(
            detail_frame,
            bg=C["bg_card"],
            fg=C["text_hi"],
            font=("Courier", 11),
            wrap="word",
            relief="flat",
            bd=0,
            highlightthickness=0,
            state="disabled",
            cursor="arrow",
        )
        dsb = ttk.Scrollbar(detail_frame, orient="vertical",
                            command=self._detail_text.yview)
        self._detail_text.configure(yscrollcommand=dsb.set)
        self._detail_text.pack(side="left", fill="both", expand=True, padx=4)
        dsb.pack(side="right", fill="y")

        # Configure text tags
        self._detail_text.tag_configure("gold",
            font=("Courier", 13, "bold"), foreground=C["gold_bright"])
        self._detail_text.tag_configure("orange",
            font=("Courier", 11, "bold"), foreground=C["orange_bright"])
        self._detail_text.tag_configure("label",
            font=("Courier", 10, "bold"), foreground=C["text_blue"])
        self._detail_text.tag_configure("value",
            font=("Courier", 11), foreground=C["text_hi"])
        self._detail_text.tag_configure("source",
            font=("Courier", 9, "italic"), foreground=C["text_mid"])
        self._detail_text.tag_configure("sep",
            font=("Courier", 9), foreground=C["gold_dim"])
        self._detail_text.tag_configure("sep_blue",
            font=("Courier", 9), foreground=C["blue_gate"])
        self._detail_text.tag_configure("dim",
            font=("Courier", 9), foreground=C["text_lo"])
        self._detail_text.tag_configure("arrow",
            font=("Courier", 11), foreground=C["text_hi"])
        self._detail_text.tag_configure("bullet",
            font=("Courier", 11), foreground=C["text_hi"])
        self._detail_text.tag_configure("chevron_tag",
            font=("Courier", 10, "italic"), foreground=C["text_mid"])
        self._detail_text.tag_configure("kek",
            font=("Courier", 11), foreground=C["text_kek"])
        self._detail_text.tag_configure("locked",
            font=("Courier", 11, "bold"), foreground=C["locked_bright"])
        self._show_welcome_detail()

    def _build_statusbar_tk(self) -> None:
        bar = tk.Frame(self.root, bg=C["bg_panel"], height=20)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self._status_var = tk.StringVar()
        tk.Label(bar, textvariable=self._status_var, bg=C["bg_panel"],
                 fg=C["text_mid"], font=("Courier", 9), anchor="w").pack(
            side="left", padx=10)

        tk.Label(bar, text="STARGATE  ·  Goa'uld Linguistic Interface  ·  v0.2",
                 bg=C["bg_panel"], fg=C["text_lo"], font=("Courier", 8)).pack(
            side="right", padx=10)

    # ─── Event Handlers ───────────────────────────────────────────────────────

    def _run_live_translation(self) -> None:
        """Execute live translation from the main search bar into the Übersetzer tab."""
        if not CTK_AVAILABLE or not hasattr(self, "_trans_output"):
            return

        text      = self._search_var.get().strip()
        direction = self._direction
        lang_pref = self._lang_pref

        if not text:
            for w in (self._trans_output, self._trans_token_text):
                w.configure(state="normal")
                w.delete("0.0", "end")
                w.configure(state="disabled")
            self._trans_status_lbl.configure(text="")
            return

        analysis  = self._analyzer.analyze(text, direction=direction,
                                           lang_pref=lang_pref)
        found_n   = sum(1 for t in analysis if t["found"])
        total_n   = sum(1 for t in analysis if not t.get("skipped"))  # exclude stop-words
        trans_str = self._analyzer.build_translation(
            analysis, direction=direction, mode=self._translation_mode,
        )

        # Translation output
        self._trans_output.configure(state="normal")
        self._trans_output.delete("0.0", "end")
        self._trans_output.insert("0.0", trans_str)
        self._trans_output.configure(state="disabled")

        # Status badge — farbcodierte Anzeige
        if found_n == total_n and total_n > 0:
            badge_icon = GLYPH_FOUND
            badge_color = C["sgc_green"]
            badge_text = f"{badge_icon}  {found_n}/{total_n} Token"
        elif found_n > 0:
            badge_icon = GLYPH_CHEVRON
            badge_color = C["orange"]
            badge_text = f"{badge_icon}  {found_n}/{total_n} Token"
        else:
            badge_icon = GLYPH_KEK
            badge_color = C["warning_red"]
            badge_text = f"{badge_icon}  0/{total_n} Token"

        self._trans_status_lbl.configure(
            text=badge_text,
            text_color=badge_color,
        )

        # Wormhole-Status im Header — farbcodierte Status-Anzeige
        if hasattr(self, "_wormhole_var"):
            if not text:
                self._wormhole_var.set("◎  STANDBY")
                self._wormhole_lbl.configure(text_color=C["text_mid"])
            elif found_n == total_n:
                self._wormhole_var.set(f"{GLYPH_FOUND}  WORMHOLE ESTABLISHED")
                self._wormhole_lbl.configure(text_color=C["sgc_green"])
            elif found_n > 0:
                self._wormhole_var.set(f"{GLYPH_CHEVRON}  DIALING  ({found_n}/{total_n})")
                self._wormhole_lbl.configure(text_color=C["orange"])
            else:
                self._wormhole_var.set(f"{GLYPH_KEK}  NO SIGNAL")
                self._wormhole_lbl.configure(text_color=C["warning_red"])

        # Token breakdown — verbesserte Tabelle mit Farbcodierung
        if direction == "goa2de":
            col_a_hdr, col_b_hdr = "GOA'ULD", "BEDEUTUNG (DE/EN)"
        else:
            col_a_hdr, col_b_hdr = f"EINGABE ({lang_pref.upper()})", "GOA'ULD"

        lines: list[str] = [
            f"\n  {col_a_hdr:<22}  {col_b_hdr}\n",
            f"  {'─' * 48}\n",
        ]

        for td in analysis:
            tok   = td["token"]
            found = td["found"]
            prim  = td["primary"]
            alts  = td["alternatives"]
            skipped = td.get("skipped", False)

            if skipped:
                reason = td.get("skip_reason", "Funktionswort")
                lines.append(f"  {GLYPH_CHEVRON}  {tok:<20}  ({reason}, Transferregel: ausgelassen)")
                lines.append("")
                continue

            t_icon = GLYPH_LOCKED if found else GLYPH_KEK

            if found and prim:
                if direction == "de2goa":
                    # col_a = Eingabe, col_b = Goa'uld
                    result_word = prim["goauld"].strip()
                    lines.append(f"  {t_icon}  {tok:<20}  {result_word}")
                    # Secondary-Alternativen aus YAML — respektiert lang_pref
                    # (EN-User: EN-Map zuerst; DE-User: DE-Map zuerst).
                    sec_alts = self._get_secondary_alts(tok, result_word)
                    if sec_alts:
                        alt_str = ", ".join(sec_alts[:3])
                        lines.append(f"       auch: {alt_str}")
                else:
                    # col_a = Goa'uld, col_b = Deutsche Bedeutung
                    best = prim
                    for a in alts:
                        if a.get("lang") == "de" and prim.get("lang") != "de":
                            best = a
                            break
                    mea = re.split(r"[;—]", best["meaning"])[0].strip()[:50]
                    lines.append(f"  {t_icon}  {tok:<20}  {mea}")

                # Source + confidence
                src = prim.get("source", "")
                confidence = prim.get("confidence") or td.get("confidence")
                meta_bits = []
                if src and src != "DE_MAP":
                    meta_bits.append(str(src))
                if confidence is not None:
                    try:
                        meta_bits.append(f"Confidence {float(confidence):.0%}")
                    except (TypeError, ValueError):
                        pass
                if meta_bits:
                    lines.append(f"       [{' · '.join(meta_bits)}]")

                # Alternativen
                if alts:
                    for a in alts[:2]:
                        if direction == "de2goa":
                            a_out = a["goauld"].split("/")[0].strip()
                        else:
                            a_out = re.split(r"[;—]", a["meaning"])[0].strip()[:36]
                        lines.append(f"       {GLYPH_ARROW}  Alt: {a_out}")
            else:
                lines.append(f"  {GLYPH_KEK}  {tok:<20}  — nicht gefunden")
                # DE/EN→Goa'uld: Fuzzy-Vorschläge aus der gewählten Primary-Map
                if direction == "de2goa":
                    suggestion_map = PRIMARY_GOAULD_MAPS.get(lang_pref, {}) or DE_GOAULD_MAP
                    close = difflib.get_close_matches(
                        _normalize_lookup(tok), suggestion_map.keys(), n=2, cutoff=0.6)
                    for c in close:
                        lines.append(f"       {GLYPH_CHEVRON}  Meinten Sie: {c} → {suggestion_map[c]}")
                else:
                    sug = self._engine.search(tok, direction=direction,
                                              max_results=2, lang_pref=lang_pref)
                    for s in sug:
                        s_out = re.split(r"[;—]", s["meaning"])[0].strip()[:36]
                        lines.append(f"       {GLYPH_CHEVRON}  Ähnlich: {s_out}")

            lines.append("")

        self._trans_token_text.configure(state="normal")
        self._trans_token_text.delete("0.0", "end")
        self._trans_token_text.insert("0.0", "\n".join(lines))
        self._trans_token_text.configure(state="disabled")

    def _toggle_lang_pref(self) -> None:
        """Wechselt zwischen Deutsch- und Englisch-Priorisierung."""
        self._lang_pref = "en" if self._lang_pref == "de" else "de"
        if CTK_AVAILABLE:
            if self._lang_pref == "de":
                self._lang_btn_var.set("🇩🇪 DE")
                self._lang_btn.configure(fg_color=C["locked_dim"],
                                          text_color=C["locked_bright"])
            else:
                self._lang_btn_var.set("🇬🇧 EN")
                self._lang_btn.configure(fg_color=C["blue_mid"],
                                          text_color=C["blue_bright"])
        self._do_search()
        if CTK_AVAILABLE and hasattr(self, "_trans_output"):
            self._run_live_translation()

    def _on_mode_change(self, label: str) -> None:
        """Wechselt den Ausgabe-Modus für Live-Übersetzung und Debrief."""
        label_to_value = getattr(self, "_mode_label_to_value", {})
        self._translation_mode = label_to_value.get(label, "extended")
        self._do_search()
        if CTK_AVAILABLE and hasattr(self, "_trans_output"):
            self._run_live_translation()

    def _on_direction_change(self, *_) -> None:
        if CTK_AVAILABLE:
            # CTK-SegmentedButton speichert das Label als Var-Wert, nicht
            # "de2goa"/"goa2de". Richtung aus Label-Struktur ableiten:
            # was VOR dem Pfeil steht ist die Quellsprache.
            val = self._dir_var.get()
            left, _, _right = val.partition("→")
            self._direction = "goa2de" if "Goa'uld" in left else "de2goa"
        else:
            # Tk-Radio speichert direkt "de2goa"/"goa2de" als value
            self._direction = self._dir_var.get()
        self._do_search()
        if CTK_AVAILABLE and hasattr(self, "_trans_output"):
            self._run_live_translation()

    def _on_search_change(self, *_) -> None:
        # Debounce: warte 160 ms nach letzter Änderung
        if self._search_after_id:
            self.root.after_cancel(self._search_after_id)
        self._search_after_id = self.root.after(160, self._on_search_debounced)

    def _on_search_debounced(self) -> None:
        """Fires after debounce — runs search AND live translation simultaneously."""
        self._do_search()
        if CTK_AVAILABLE:
            self._run_live_translation()

    def _do_search(self) -> None:
        query = self._search_var.get().strip()
        if not query:
            self._sentence_mode = False
            self._display_results([])
            return

        # DE/EN→Goa'uld: kompletten Satz direkt in der sprachspezifischen YAML-Map nachschlagen
        if self._direction == "de2goa":
            query_key = _normalize_lookup(query)
            lang_order = [self._lang_pref, "de" if self._lang_pref == "en" else "en"]
            for lang in lang_order:
                direct = PRIMARY_GOAULD_MAPS.get(lang, {}).get(query_key)
                if direct:
                    self._sentence_mode = False
                    self._display_results([{
                        "goauld":  direct,
                        "meaning": query,
                        "section": "Direktübersetzung",
                        "source":  f"{lang.upper()}_PRIMARY_MAP",
                        "lang":    lang,
                        "confidence": 0.94,
                    }])
                    return

        if self._analyzer.is_sentence(query):
            self._sentence_mode = True
            phrase_hit = self._analyzer._exact_engine_matches(
                query, direction=self._direction, lang_pref=self._lang_pref,
            )
            analysis = self._analyzer.analyze(query, direction=self._direction,
                                              lang_pref=self._lang_pref)
            self._display_sentence(analysis, query, phrase_hit[0] if phrase_hit else None)
        else:
            self._sentence_mode = False
            results = self._engine.search(query, direction=self._direction,
                                          lang_pref=self._lang_pref)
            self._display_results(results)

    def _display_results(self, results: list[dict]) -> None:
        if CTK_AVAILABLE:
            self._display_results_ctk(results)
        else:
            self._display_results_tk(results)

    def _display_sentence(self, analysis: list[dict], query: str,
                          phrase_hit: Optional[dict]) -> None:
        if CTK_AVAILABLE:
            self._display_sentence_ctk(analysis, query, phrase_hit)
        else:
            self._display_sentence_tk(analysis, query, phrase_hit)

    def _display_results_ctk(self, results: list[dict]) -> None:
        """SGC Intel-Feed — nummerierte Zeilen mit Goa'uld-Term, Bedeutung, Quelle.

        v0.2.5 Fix: Ersetzt das alte Card-Layout (wraplength-Hardcodes) durch
        eine saubere 4-Spalten-Grid-Zeile (Nr / Goa'uld / Meaning / Score) —
        dadurch verschwindet das Spalten-Abschneiden bei schmalem Paned-Panel.
        """
        # Clear old rows
        for row in self._result_rows:
            row.destroy()
        self._result_rows.clear()

        if not results:
            msg = ctk.CTkLabel(
                self._result_scroll,
                text=f"  {GLYPH_KEK}  KEIN EINTRAG GEFUNDEN\n     TEK'MA'TE…",
                font=("Courier", 11, "bold"),
                text_color=C["text_lo"],
                anchor="w",
                justify="left",
            )
            msg.grid(row=0, column=0, sticky="ew", padx=8, pady=20)
            self._result_rows.append(msg)
            self._update_status(len(results))
            return

        for idx, entry in enumerate(results):
            # Zeilen-Frame mit Border-Left-Accent (statt Full-Border-Card)
            row = ctk.CTkFrame(
                self._result_scroll,
                fg_color=C["bg_panel"],
                border_width=0,
                corner_radius=0,
                height=42,
            )
            row.grid(row=idx, column=0, sticky="ew", padx=0, pady=1)
            row.grid_propagate(False)
            # 4-Spalten-Grid:  [NR 30px] [GOA'ULD 120px] [MEANING flex] [SOURCE 28px-flex]
            row.columnconfigure(0, weight=0, minsize=30)
            row.columnconfigure(1, weight=0, minsize=120)
            row.columnconfigure(2, weight=1, minsize=80)
            row.columnconfigure(3, weight=0, minsize=44)

            # Border-Left-Accent (ersetzt Card-Border)
            score = entry.get("score", 0)
            if score >= 90:
                accent = C["phosphor_grn"]
            elif score >= 60:
                accent = C["gold"]
            else:
                accent = C["text_mid"]
            accent_strip = ctk.CTkFrame(row, fg_color=accent, corner_radius=0, width=3)
            accent_strip.grid(row=0, column=0, rowspan=2, sticky="nsw", padx=(0, 0))

            # [NR]
            nr_lbl = ctk.CTkLabel(
                row,
                text=f"{idx+1:02d}",
                font=("Courier", 10),
                text_color=C["mil_text_dim"],
                anchor="w",
                width=28,
            )
            nr_lbl.grid(row=0, column=0, sticky="w", padx=(8, 0), pady=(6, 0))

            # [GOA'ULD] — gold, bold, eigene Spalte
            goauld_text = entry["goauld"]
            if len(goauld_text) > 16:
                goauld_text = goauld_text[:14] + "…"
            goauld_lbl = ctk.CTkLabel(
                row,
                text=goauld_text,
                font=("Courier", 12, "bold"),
                text_color=C["gold_bright"],
                anchor="w",
            )
            goauld_lbl.grid(row=0, column=1, sticky="w", padx=(2, 6), pady=(6, 0))

            # [MEANING] — flex-spalte mit wraplength basierend auf Panel-Breite
            meaning = entry["meaning"]
            if len(meaning) > 48:
                meaning = meaning[:46] + "…"
            meaning_lbl = ctk.CTkLabel(
                row,
                text=meaning,
                font=("Courier", 10),
                text_color=C["text_hi"],
                anchor="w",
            )
            meaning_lbl.grid(row=0, column=2, sticky="w", padx=(2, 6), pady=(6, 0))

            # [SCORE]
            score_color = C["phosphor_grn"] if score >= 90 else (
                C["gold"] if score >= 60 else C["text_lo"]
            )
            score_lbl = ctk.CTkLabel(
                row,
                text=f"{score}%",
                font=("Courier", 9),
                text_color=score_color,
                anchor="e",
                width=40,
            )
            score_lbl.grid(row=0, column=3, sticky="e", padx=(0, 8), pady=(6, 0))

            # Zweite Zeile: Section-Tag (klein, gedämpft)
            sec = entry.get("section", "")
            src = entry.get("source", "")
            tag_bits = []
            if sec:
                tag_bits.append(sec[:20])
            if src and src not in ("DE_MAP",):
                src_short = src[:24] + "…" if len(src) > 24 else src
                tag_bits.append(src_short)
            tag_text = "  ·  ".join(tag_bits) if tag_bits else ""

            tag_lbl = ctk.CTkLabel(
                row,
                text=tag_text,
                font=("Courier", 8),
                text_color=C["text_lo"],
                anchor="w",
            )
            tag_lbl.grid(row=1, column=1, columnspan=3, sticky="w",
                         padx=(2, 6), pady=(0, 4))

            # Click binding: gesamte Zeile selektierbar
            def _select(e, entry=entry, row=row, accent_strip=accent_strip):
                for r in self._result_rows:
                    if isinstance(r, ctk.CTkFrame):
                        r.configure(fg_color=C["bg_panel"])
                row.configure(fg_color=C["bg_select"])
                self._show_detail(entry)

            for w in (row, nr_lbl, goauld_lbl, meaning_lbl, score_lbl, tag_lbl):
                w.bind("<Button-1>", _select)

            self._result_rows.append(row)

        self._update_status(len(results))

        # Auto-select first result
        if results:
            self._result_rows[0].configure(fg_color=C["bg_select"])
            self._show_detail(results[0])

    def _display_results_tk(self, results: list[dict]) -> None:
        """SGC Card-basierte Ergebnisliste (Tkinter-Fallback)."""
        self._listbox.delete(0, "end")
        self._tk_results = results
        if not results:
            self._listbox.insert("end", f"  {GLYPH_KEK}  Kein Eintrag gefunden.  Tek'ma'te…")
            self._update_status(0)
            return
        for e in results:
            score = e.get("score", 0)
            icon = GLYPH_FOUND if score >= 90 else GLYPH_BULLET
            goa = e["goauld"][:28]
            mea = e["meaning"][:36]
            sec = e.get("section", "")[:12]
            self._listbox.insert("end", f"  {icon}  {goa:<30}  {mea}  [{sec}]")
        self._update_status(len(results))
        self._listbox.selection_set(0)
        self._show_detail(results[0])

    def _display_sentence_ctk(self, analysis: list[dict], query: str,
                               phrase_hit: Optional[dict]) -> None:
        """CTK results panel in sentence mode."""
        for row in self._result_rows:
            row.destroy()
        self._result_rows.clear()

        translation = self._analyzer.build_translation(
            analysis, direction=self._direction, mode=self._translation_mode,
        )
        found_count = sum(1 for t in analysis if t["found"] and not t.get("skipped"))
        total_count = sum(1 for t in analysis if not t.get("skipped"))

        # Header card: full translation
        hdr_card = ctk.CTkFrame(self._result_scroll, fg_color=C["bg_sentence"],
                                corner_radius=6)
        hdr_card.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 6))
        hdr_card.columnconfigure(0, weight=1)

        ctk.CTkLabel(hdr_card,
                     text=f"  {GLYPH_GATE}  SATZANALYSE",
                     font=("Courier", 10, "bold"),
                     text_color=C["blue_bright"], anchor="w",
                     ).grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 2))

        ctk.CTkLabel(hdr_card,
                     text=f"  {query}",
                     font=("Courier", 12, "bold"),
                     text_color=C["gold_bright"], anchor="w",
                     ).grid(row=1, column=0, sticky="ew", padx=8, pady=1)

        ctk.CTkLabel(hdr_card,
                     text=f"  {GLYPH_ARROW}  {translation}",
                     font=("Courier", 11),
                     text_color=C["text_hi"], anchor="w", wraplength=310,
                     ).grid(row=2, column=0, sticky="ew", padx=8, pady=1)

        ctk.CTkLabel(hdr_card,
                     text=f"  {found_count}/{total_count} Token erkannt",
                     font=("Courier", 8),
                     text_color=C["locked_bright"] if found_count == total_count
                     else C["orange"], anchor="w",
                     ).grid(row=3, column=0, sticky="ew", padx=8, pady=(1, 6))

        def _click_hdr(e):
            for r in self._result_rows:
                if isinstance(r, ctk.CTkFrame):
                    r.configure(fg_color=C["bg_sentence"] if r is hdr_card else C["bg_card"])
            hdr_card.configure(fg_color=C["bg_select"])
            self._show_sentence_detail(analysis, query, phrase_hit)

        hdr_card.bind("<Button-1>", _click_hdr)
        self._result_rows.append(hdr_card)

        # Per-token cards
        for idx, token_data in enumerate(analysis):
            tok = token_data["token"]
            found = token_data["found"]
            primary = token_data["primary"]

            tok_color = C["bg_card"]
            row = ctk.CTkFrame(self._result_scroll, fg_color=tok_color, corner_radius=4)
            row.grid(row=idx + 1, column=0, sticky="ew", padx=4, pady=2)
            row.columnconfigure(0, weight=1)

            icon = GLYPH_LOCKED if found else GLYPH_KEK
            _icon_color = C["locked_bright"] if found else C["text_kek"]
            tok_label_color = C["gold_bright"] if found else C["text_mid"]

            ctk.CTkLabel(row,
                         text=f"  {icon}  {tok}",
                         font=("Courier", 12, "bold"),
                         text_color=tok_label_color, anchor="w",
                         ).grid(row=0, column=0, sticky="ew", padx=6, pady=(5, 1))

            if found and primary:
                short_meaning = re.split(r"[;—]", primary["meaning"])[0].strip()
                if len(short_meaning) > 60:
                    short_meaning = short_meaning[:57] + "…"
                ctk.CTkLabel(row,
                             text=f"    {GLYPH_ARROW}  {short_meaning}",
                             font=("Courier", 10),
                             text_color=C["text_hi"], anchor="w",
                             ).grid(row=1, column=0, sticky="ew", padx=6, pady=1)

                n_alt = len(token_data["alternatives"])
                ctk.CTkLabel(row,
                             text=f"    [{primary['section']}]  +{n_alt} Alternativen",
                             font=("Courier", 8),
                             text_color=C["gold_dim"], anchor="w",
                             ).grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 5))
            else:
                ctk.CTkLabel(row,
                             text=f"    {GLYPH_KEK}  nicht im Vokabular",
                             font=("Courier", 10),
                             text_color=C["text_kek"], anchor="w",
                             ).grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 5))

            def _select_token(e, td=token_data, r=row):
                for rr in self._result_rows:
                    if isinstance(rr, ctk.CTkFrame):
                        rr.configure(fg_color=C["bg_sentence"] if rr is self._result_rows[0]
                                     else C["bg_card"])
                r.configure(fg_color=C["bg_select"])
                if td["found"] and td["primary"]:
                    self._show_detail(td["primary"])
                else:
                    self._show_sentence_detail(analysis, query, phrase_hit)

            row.bind("<Button-1>", _select_token)
            self._result_rows.append(row)

        self._update_status(found_count, mode="sentence", total_tokens=total_count)
        # Auto-show sentence detail
        self._show_sentence_detail(analysis, query, phrase_hit)

    def _display_sentence_tk(self, analysis: list[dict], query: str,
                              phrase_hit: Optional[dict]) -> None:
        """Tkinter results panel in sentence mode."""
        self._listbox.delete(0, "end")
        self._tk_results = []
        translation = self._analyzer.build_translation(
            analysis, direction=self._direction, mode=self._translation_mode,
        )
        found_count = sum(1 for t in analysis if t["found"] and not t.get("skipped"))

        self._listbox.insert("end", f"  {GLYPH_GATE} SATZ: {query[:35]}")
        self._listbox.insert("end", f"  {GLYPH_ARROW} {translation[:50]}")
        self._listbox.insert("end", f"  {'─' * 40}")

        for td in analysis:
            icon = GLYPH_LOCKED if td["found"] else GLYPH_KEK
            mea = ""
            if td["found"] and td["primary"]:
                mea = re.split(r"[;—]", td["primary"]["meaning"])[0].strip()[:30]
            self._listbox.insert("end", f"  {icon} {td['token']:<16} {mea}")
            self._tk_results.append(td)

        self._update_status(found_count, mode="sentence", total_tokens=len(analysis))
        self._show_sentence_detail(analysis, query, phrase_hit)

    def _on_listbox_select(self, _) -> None:
        sel = self._listbox.curselection()
        if sel and self._tk_results:
            idx = sel[0]
            if idx < len(self._tk_results):
                self._show_detail(self._tk_results[idx])

    # ─── Detail View ──────────────────────────────────────────────────────────

    def _show_welcome_detail(self) -> None:
        total = len(self._engine.entries)
        de_map_count = len(DE_GOAULD_MAP)
        if self._md_paths:
            src = "  +  ".join(Path(p).name for p in self._md_paths)
        else:
            src = "Kein Wörterbuch geladen"
        welcome = (
            "\n"
            "╔══════════════════════════════════════════════╗\n"
            "║   GOA'ULD LINGUISTIC INTERFACE  v0.2        ║\n"
            "║   SGC Xenolinguistics Division               ║\n"
            "║   Stargate Command  ·  LEVEL 28             ║\n"
            "╚══════════════════════════════════════════════╝\n\n"
            f"  Wörterbuch-Einträge:  {total}\n"
            f"  DE→Goa'uld direkt:   {de_map_count} Ausdrücke\n"
            f"  Quelle:  {src}\n\n"
            "  ═══════════════════════════════════════════\n\n"
            "  HAUPTFUNKTION: DEUTSCH → GOA'ULD\n\n"
            "  Tippe einen deutschen Begriff oder Satz in\n"
            "  die Suchleiste. Der Übersetzer findet das\n"
            "  passende Goa'uld-Wort.\n\n"
            "  BEISPIELE:\n"
            '    "Ich sterbe frei"  →  Dal shakka mel\n'
            '    "Verräter"         →  Shol\'va\n'
            '    "Halt"             →  Hol\n'
            '    "Ich bin kein Jaffa"  →  Kel nok shree Jaffa\n'
            '    "Oh mein Gott"     →  Mak lo onak\n'
            '    "Angriff"          →  Tal shak\n\n'
            "  ─────────────────────────────────────────\n\n"
            "  GOA'ULD → DEUTSCH  (zweite Richtung)\n\n"
            '    "Jaffa, kree!"    →  Achtung, Krieger!\n'
            '    "Shol\'va"         →  Verräter\n'
            '    "Tek\'ma\'te"       →  Meister, gut getroffen\n'
            '    "Dal shakka mel"  →  Ich sterbe frei!\n'
            '    "Chappa\'ai"       →  Sternentor\n\n'
            "  ─────────────────────────────────────────\n\n"
            "  TABS:\n"
            "    ◈ Detail      — Wort-Detailansicht\n"
            "    ⊕ Satzanalyse — Token-für-Token Analyse\n"
            "    ⚡ Übersetzer  — Live-Übersetzung\n\n"
            "  ─────────────────────────────────────────\n\n"
            '  "Shel kek nem ron."  —  Widerstandsparole\n'
            "  der Freien Jaffa. Bedeutung: Ich sterbe frei.\n\n"
            "  ✦  Tek'ma'te. Jaffa, kree!  ✦\n"
        )
        self._write_detail(welcome)

    def _show_detail(self, entry: dict) -> None:
        """SGC Detail-Panel mit klaren Sektionen: ENTRY, BEDEUTUNG, QUELLE, GRAMMATIK, ALTERNATIVEN."""
        self._selected_entry = entry
        sep   = "─" * 52
        sep_s = "┄" * 52

        # --- Alternatives: other entries with the same or similar Goa'uld term ---
        goa_root = re.split(r"[/(!'\s]", entry["goauld"])[0].strip()
        all_matches = self._engine.search(goa_root, direction="goa2de", max_results=10)
        alternatives = [r for r in all_matches
                        if r is not entry
                        and r["goauld"].lower() != entry["goauld"].lower()][:4]

        # Semantic variants: other entries with similar meaning
        mean_root = re.split(r"[;—,(]", entry["meaning"])[0].strip()[:20]
        mean_matches = self._engine.search(mean_root, direction="de2goa", max_results=6)
        semantic = [r for r in mean_matches
                    if r is not entry
                    and r["goauld"].lower() != entry["goauld"].lower()
                    and r not in alternatives][:3]

        # --- Grammar analysis ---
        gl = entry["goauld"].lower()
        tips: list[str] = []
        if "'" in entry["goauld"]:
            tips.append(
                f"  {GLYPH_GATE}  GLOTTALSTOPP: Das Apostroph kennzeichnet einen harten\n"
                f"     Stimmeinsatz — charakteristisch für Goa'uld.")
        if gl.endswith("ia"):
            tips.append(f"  {GLYPH_GATE}  SUFFIX -ia = Verneinung (»nicht«)")
        if gl.endswith("k") and len(gl) > 2:
            tips.append(f"  {GLYPH_GATE}  SUFFIX -k kann »sein / ist« bedeuten")
        if gl.endswith("p") and len(gl) > 2:
            tips.append(f"  {GLYPH_GATE}  SUFFIX -p = Plural-Markierung")
        if gl.startswith("kree"):
            tips.append(f"  {GLYPH_GATE}  KREE-KOMPOSITA: Bedeutung stark kontextabhängig")
        if "tok" in gl:
            tips.append(f"  {GLYPH_GATE}  Wurzel TOK = »gegen, widerstehen«")
        if "kek" in gl:
            tips.append(f"  {GLYPH_GATE}  Wurzel KEK = »Tod / Schwäche«")

        # --- Build text mit Sektionen ---
        lines = [
            "",
            f"  {GLYPH_GATE}  ENTRY DETAIL",
            f"  {sep}",
            "",
            f"  {GLYPH_LOCKED}  {entry['goauld']}",
            "",
        ]

        # BEDEUTUNG Sektion
        lines += [f"  {sep}", ""]
        lines.append("  BEDEUTUNG")
        lines.append("")

        full_meaning = entry["meaning"]
        meaning_parts = re.split(r"\s*([;—])\s*", full_meaning)
        if len(meaning_parts) == 1:
            lines.append(f"    {full_meaning}")
        else:
            first = True
            i = 0
            while i < len(meaning_parts):
                part = meaning_parts[i]
                _sep_char = ""
                if i + 1 < len(meaning_parts) and meaning_parts[i + 1] in (";", "—"):
                    _sep_char = meaning_parts[i + 1]
                    i += 2
                else:
                    i += 1
                if part.strip():
                    prefix = f"    {GLYPH_BULLET}  " if not first else "    "
                    lines.append(f"{prefix}{part.strip()}")
                    first = False
        lines += ["", f"  {sep}", ""]

        # QUELLE / EPISODE Sektion
        lines.append("  QUELLE")
        lines.append("")
        if entry.get("section"):
            sec = entry["section"]
            sec_icon = "◆" if "Kanon" in sec else "◈" if "Fanon" in sec else "▸"
            lines.append(f"    {sec_icon}  SEKTION     {sec}")
        if entry.get("source"):
            lines.append(f"    ◈  EPISODE     {entry['source']}")
        if not entry.get("section") and not entry.get("source"):
            lines.append("    —  Keine Quelle verfügbar")
        lines += ["", f"  {sep}", ""]

        # GRAMMATIK & LINGUISTIK Sektion
        if tips:
            lines.append("  GRAMMATIK & LINGUISTIK")
            lines.append("")
            for t in tips:
                lines.append(t)
            lines += ["", f"  {sep}", ""]

        # ALTERNATIVEN Sektion
        if alternatives:
            lines.append("  ALTERNATIVEN")
            lines.append("")
            for r in alternatives:
                goa = r["goauld"][:26]
                mea = re.split(r"[;—]", r["meaning"])[0].strip()[:40]
                sec = f"[{r['section'][:14]}]" if r.get("section") else ""
                lines.append(f"    ▸  {goa:<28}  {mea}")
                if sec:
                    lines.append(f"       {sec}")
            lines += ["", f"  {sep_s}", ""]

        # SEMANTISCH VERWANDT Sektion
        if semantic:
            lines.append("  SEMANTISCH VERWANDT")
            lines.append("")
            for r in semantic:
                goa = r["goauld"][:26]
                mea = re.split(r"[;—]", r["meaning"])[0].strip()[:38]
                lines.append(f"    {GLYPH_GATE}  {goa:<28}  {mea}")
            lines += ["", f"  {sep}", ""]

        lines.append(f"  {GLYPH_STAR}  Tek'ma'te.  {GLYPH_STAR}")
        lines.append("")

        self._write_detail("\n".join(lines))

    def _show_sentence_detail(self, analysis: list[dict], query: str,
                               phrase_hit: Optional[dict]) -> None:
        """Vollständige Satzanalyse in der Detailansicht."""
        sep   = "═" * 52
        sep_s = "─" * 52
        translation = self._analyzer.build_translation(
            analysis, direction=self._direction, mode=self._translation_mode,
        )
        found_count = sum(1 for t in analysis if t["found"] and not t.get("skipped"))
        total_count = sum(1 for t in analysis if not t.get("skipped"))

        lines = [
            "",
            f"  {GLYPH_GATE}  SATZANALYSE",
            "",
            f"  {sep}",
            "",
            "  EINGABE",
            f"    {query}",
            "",
            "  WÖRTLICHE ÜBERSETZUNG",
            f"    {translation}",
            "",
        ]

        # If there's a direct phrase match in the dictionary, highlight it
        if phrase_hit:
            lines += [
                f"  {sep_s}",
                "",
                f"  {GLYPH_LOCKED}  DIREKTTREFFER IM WÖRTERBUCH",
                "",
                f"    {GLYPH_ARROW}  {phrase_hit['meaning']}",
                f"    Sektion: {phrase_hit.get('section', '—')}  ·  "
                f"Quelle: {phrase_hit.get('source', '—')}",
                "",
            ]

        lines += [
            f"  {sep}",
            "",
            f"  TOKEN-AUFSCHLÜSSELUNG  "
            f"({found_count}/{total_count} erkannt)",
            "",
        ]

        for i, td in enumerate(analysis):
            tok   = td["token"]
            found = td["found"]
            prim  = td["primary"]
            alts  = td["alternatives"]

            token_icon = GLYPH_LOCKED if found else GLYPH_KEK
            lines += [
                f"  {sep_s}",
                "",
                f"  {token_icon}  TOKEN {i + 1}:  {tok.upper()}",
                "",
            ]

            if td.get("skipped"):
                reason = td.get("skip_reason", "Funktionswort")
                lines.append(f"    {GLYPH_CHEVRON}  Transferregel: {reason} ausgelassen.")
                lines.append("")
                continue

            if found and prim:
                # Primary meaning — structured display
                full = prim["meaning"]
                parts_m = re.split(r"\s*[;—]\s*", full)
                lines.append("  PRIMÄRE BEDEUTUNG")
                lines.append("")
                for j, part in enumerate(parts_m):
                    part = part.strip()
                    if not part:
                        continue
                    prefix = f"    {GLYPH_BULLET}  " if j > 0 else "    "
                    lines.append(f"{prefix}{part}")
                lines.append("")

                meta = []
                if prim.get("section"):
                    meta.append(f"Sektion: {prim['section']}")
                if prim.get("source"):
                    meta.append(f"Quelle: {prim['source']}")
                if prim.get("tier"):
                    meta.append(f"Tier: {prim['tier']}")
                confidence = prim.get("confidence") or td.get("confidence")
                if confidence is not None:
                    try:
                        meta.append(f"Confidence: {float(confidence):.0%}")
                    except (TypeError, ValueError):
                        pass
                if meta:
                    lines.append(f"    {'  ·  '.join(meta)}")
                    lines.append("")

                # Secondary-Alternativen aus YAML (nur bei DE/EN → Goa'uld):
                # polysemische Quellbegriffe mit mehreren Goa'uld-Übersetzungen.
                # Der Helper prüft beide Sprachmaps gemäß lang_pref.
                if self._direction == "de2goa":
                    sec_alts = self._get_secondary_alts(
                        tok, prim.get("goauld", "")
                    )
                    if sec_alts:
                        lines.append("  AUCH")
                        lines.append("")
                        for sa in sec_alts[:5]:
                            lines.append(f"    {GLYPH_ARROW}  {sa}")
                        lines.append("")

                # Alternatives
                if alts:
                    lines.append("  ALTERNATIVEN")
                    lines.append("")
                    for alt in alts:
                        alt_goa  = alt["goauld"][:24]
                        alt_mea  = re.split(r"[;—]", alt["meaning"])[0].strip()[:42]
                        alt_src  = alt.get("source", "")[:16]
                        lines.append(f"    {GLYPH_ARROW}  {alt_goa:<26}  {alt_mea}")
                        if alt_src:
                            lines.append(f"                              [{alt_src}]")
                    lines.append("")
            else:
                lines.append(f"    {GLYPH_KEK}  Kein Eintrag gefunden.")
                lines.append("")
                # Fuzzy suggestions
                suggestions = self._engine.search(tok, direction=self._direction,
                                                  max_results=3, fuzzy_threshold=0.3)
                if suggestions:
                    lines.append("  ÄHNLICHE BEGRIFFE")
                    lines.append("")
                    for s in suggestions:
                        lines.append(f"    {GLYPH_CHEVRON}  {s['goauld']:<22}  "
                                     f"{re.split(chr(59), s['meaning'])[0].strip()[:36]}")
                    lines.append("")

        lines += [
            f"  {sep}",
            "",
            f"  {GLYPH_STAR}  Kree!  {GLYPH_STAR}",
            "",
        ]
        self._write_detail("\n".join(lines), target="sentence")

    def _write_detail(self, text: str, target: str = "detail") -> None:
        """Render text into a detail panel textbox.
        target: 'detail' → self._detail_text, 'sentence' → self._sentence_text
        """
        if CTK_AVAILABLE:
            widget = (self._sentence_text if target == "sentence"
                      else self._detail_text)
            widget.configure(state="normal")
            widget.delete("0.0", "end")
            widget.insert("0.0", text)
            widget.configure(state="disabled")
            # Switch tab
            if target == "sentence":
                self._tabs.set("  ⊕ Satzanalyse  ")
            else:
                self._tabs.set("  ◈ Detail  ")
        else:
            self._detail_text.configure(state="normal")
            self._detail_text.delete("1.0", "end")
            for line in text.split("\n"):
                stripped = line.strip()
                if stripped.startswith((GLYPH_LOCKED, GLYPH_GATE, GLYPH_FOUND, GLYPH_SECTION)):
                    self._detail_text.insert("end", line + "\n", "gold")
                elif stripped.startswith(GLYPH_KEK):
                    self._detail_text.insert("end", line + "\n", "kek")
                elif stripped.startswith(("BEDEUTUNG", "PRIMÄRE", "WÖRTLICHE", "EINGABE")):
                    self._detail_text.insert("end", line + "\n", "orange")
                elif stripped.startswith(("SEKTION", "EPISODE", "GRAMMATIK", "VERWANDTE",
                                          "SEMANTISCH", "ÄHNLICHE", "ALTERNATIVEN",
                                          "TOKEN ", "SATZANALYSE", "DIREKTTREFFER",
                                          "TOKEN-AUFSCHLÜSSELUNG")):
                    self._detail_text.insert("end", line + "\n", "label")
                elif "═" * 4 in stripped:
                    self._detail_text.insert("end", line + "\n", "sep_blue")
                elif "─" * 4 in stripped or "┄" * 4 in stripped:
                    self._detail_text.insert("end", line + "\n", "sep")
                elif stripped.startswith(GLYPH_ARROW):
                    self._detail_text.insert("end", line + "\n", "arrow")
                elif stripped.startswith(GLYPH_BULLET):
                    self._detail_text.insert("end", line + "\n", "bullet")
                elif stripped.startswith(GLYPH_CHEVRON):
                    self._detail_text.insert("end", line + "\n", "chevron_tag")
                elif stripped.startswith(("✦", "╔", "║", "╚")):
                    self._detail_text.insert("end", line + "\n", "dim")
                elif stripped.startswith("["):
                    self._detail_text.insert("end", line + "\n", "source")
                else:
                    self._detail_text.insert("end", line + "\n", "value")
            self._detail_text.configure(state="disabled")

    # ─── Datei-Browser ────────────────────────────────────────────────────────

    def _browse_md(self) -> None:
        path = filedialog.askopenfilename(
            title="Markdown-Wörterbuch auswählen",
            filetypes=[("Markdown-Dateien", "*.md"), ("Alle Dateien", "*.*")],
        )
        if not path:
            return
        new_entries = parse_markdown_dictionary(path)
        if not new_entries:
            if TK_AVAILABLE:
                messagebox.showwarning(
                    "Keine Einträge",
                    f"In der Datei wurden keine Goa'uld-Einträge gefunden:\n{path}",
                )
            return

        # Determine language by filename heuristic
        # DE: Wörterbuch, Neologikum, deutsch, de_, _de., vollständige
        # EN: Dictionary, Fictionary, and anything else
        name_low = Path(path).name.lower()
        is_de = any(k in name_low for k in (
            "wörterbuch", "woerterbuch", "neologikum",
            "deutsch", "de_", "_de.", "vollständige", "vollstandige",
        ))
        lang = "de" if is_de else "en"
        tagged = [{**e, "lang": lang} for e in new_entries]

        # Reload everything fresh from both MDs, then replace matching lang
        entries, paths, de_map, en_map, secondary_de, secondary_en = _load_lexicon()
        self._secondary_de = secondary_de      # für "auch:"-UI
        self._secondary_en = secondary_en
        # Remove any old entries of the same lang and add new ones
        entries = [e for e in entries if e.get("lang") != lang] + tagged
        if path not in paths:
            paths = [p for p in paths if Path(p).name.lower() != name_low] + [path]

        self._all_entries = entries
        self._md_paths    = paths
        self._engine      = SearchEngine(self._all_entries)
        self._analyzer    = SentenceAnalyzer(self._engine)
        self._update_status()
        self._show_welcome_detail()
        self._do_search()
        log.info("MD-Datei geladen (%s): %s  (%d Einträge)", lang.upper(), path, len(new_entries))

    # ─── Hilfsfunktionen ─────────────────────────────────────────────────────

    def _update_status(self, result_count: Optional[int] = None,
                       mode: str = "search", total_tokens: int = 0) -> None:
        total = len(self._engine.entries)
        # Header: Lexikon-Counter
        self._entry_count_var.set(f"▸ LEXICON: {total:,} ENTRIES".replace(",", "."))
        # Intel-Feed-Counter (links oben)
        if hasattr(self, "_intel_count_var"):
            if result_count is None:
                self._intel_count_var.set("")
            else:
                self._intel_count_var.set(f"{result_count} HITS")

        dir_label = ("GOA'ULD → DE/EN" if self._direction == "goa2de"
                     else "DE/EN → GOA'ULD")

        if mode == "sentence":
            if result_count == total_tokens:
                msg = (f"  {GLYPH_LOCKED}  ALL {total_tokens} TOKENS DECRYPTED  ·  "
                       f"{total} ENTRIES  ·  {dir_label}")
            else:
                msg = (f"  {GLYPH_CHEVRON}  {result_count}/{total_tokens} TOKENS DECRYPTED  ·  "
                       f"{total} ENTRIES  ·  {dir_label}")
        elif result_count is None:
            msg = (f"  {GLYPH_GATE}  STANDBY  ·  {total} ENTRIES LOADED  ·  "
                   f"DIR: {dir_label}")
        elif result_count == 0:
            msg = (f"  {GLYPH_KEK}  KEK!  —  NO INTERCEPTS  ·  "
                   f"DIR: {dir_label}")
        else:
            msg = (f"  {GLYPH_FOUND}  {result_count} INTERCEPTS  ·  "
                   f"TOTAL: {total} ENTRIES  ·  {dir_label}")
        self._status_var.set(msg)

    # ─── App starten ──────────────────────────────────────────────────────────

    def run(self) -> None:
        self.root.mainloop()


# ─────────────────────────────────────────────────────────────────────────────
# CLI MODUS  (Kompatibel mit dem Original-Script)
# ─────────────────────────────────────────────────────────────────────────────

def run_cli(args: argparse.Namespace) -> None:
    # Guard: bei --noconsole-EXE ist sys.stdout None → print würde crashen.
    # In diesem Fall ist der interaktive CLI-Modus ohnehin nicht bedienbar.
    if sys.stdout is None:
        log.error("CLI-Modus ist in der --noconsole-EXE nicht verfügbar.")
        return
    print("\n" + "=" * 62)
    print("   JAFFA, KREE!  —  Goa'uld Linguistic Interface  v0.2")
    print("=" * 62)

    # Lade bevorzugt YAML (+ Overlay); explizites --md erzwingt den Legacy-MD-Modus.
    hint = getattr(args, "md", None)
    if hint:
        all_entries, _found_paths = _load_mds(hint_en=hint)
    else:
        all_entries, _found_paths, _de_map, _en_map, _sec_de, _sec_en = _load_lexicon()
    if not all_entries:
        log.error("Kein Vokabular geladen. Abbruch.")
        return

    engine = SearchEngine(all_entries)
    analyzer = SentenceAnalyzer(engine)
    lang_pref = getattr(args, "lang", "de")
    mode = getattr(args, "mode", "extended")
    dir_name = "Goa'uld -> Deutsch/Englisch" if args.dir == "goa2de" else "Deutsch/Englisch -> Goa'uld"

    if args.text:
        analysis = analyzer.analyze(args.text, args.dir, lang_pref=lang_pref)
        result = analyzer.build_translation(analysis, direction=args.dir, mode=mode)
        print(f"[{dir_name}]  {args.text}  ->  {result}")
        return

    print(f"\nRichtung: {dir_name}")
    print("Eingabe: Text oder 'exit'\n")

    while True:
        try:
            user_input = input("> ").strip()
            if user_input.lower() in ("exit", "quit", "q"):
                print("Tek'ma'te!")
                break
            if not user_input:
                continue
            analysis = analyzer.analyze(user_input, args.dir, lang_pref=lang_pref)
            result = analyzer.build_translation(analysis, direction=args.dir, mode=mode)
            print(f"  ->  {result}\n")
        except (KeyboardInterrupt, EOFError):
            print("\nTek'ma'te!")
            break


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stargate: Goa'uld Linguistic Interface v0.2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele (GUI):
  python goauld_translator_gui.py
  python goauld_translator_gui.py --md /pfad/zum/dictionary.md

Beispiele (CLI):
  python goauld_translator_gui.py --cli --dir goa2de
  python goauld_translator_gui.py --cli --dir goa2de --text "Jaffa kree"
  python goauld_translator_gui.py --cli --dir de2goa --text "Ich sterbe frei"

  Jaffa, kree!
        """,
    )
    parser.add_argument(
        "--md",
        type=str,
        default=None,
        help="Pfad zur Markdown-Wörterbuchdatei (optional, wird sonst automatisch gesucht)",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="CLI-Modus statt GUI starten",
    )
    parser.add_argument(
        "--dir",
        choices=["goa2de", "de2goa"],
        default="goa2de",
        help="Übersetzungsrichtung (nur im CLI-Modus)",
    )
    parser.add_argument(
        "--text",
        type=str,
        default=None,
        help="Text direkt übersetzen (nur im CLI-Modus)",
    )
    parser.add_argument(
        "--lang",
        choices=["de", "en"],
        default="de",
        help="Quellsprache für DE/EN→Goa'uld im CLI-Modus",
    )
    parser.add_argument(
        "--mode",
        choices=["canonical", "extended", "literal", "goauld_style"],
        default="extended",
        help="Ausgabemodus für Übersetzungen (CLI)",
    )
    args = parser.parse_args()

    if args.cli:
        run_cli(args)
    else:
        if not TK_AVAILABLE:
            log.error("Tkinter ist nicht verfügbar. Bitte Python mit Tkinter-Unterstützung installieren.")
            log.error("Im CLI-Modus läuft das Script ohne Tkinter:  --cli")
            sys.exit(1)
        if not CTK_AVAILABLE:
            log.warning("CustomTkinter nicht gefunden — nutze Standard-Tkinter.")
            log.warning("Für das beste Erlebnis:  pip install customtkinter")
        else:
            log.info("CustomTkinter verfügbar — nutze CTK-GUI.")
        try:
            log.info("Initialisiere GoauldApp...")
            app = GoauldApp(md_path=args.md)
            log.info("Starte app.run()...")
            app.run()
            log.info("app.run() zurückgegeben.")
        except SystemExit:
            log.error("SystemExit während GUI-Start.")
            import traceback
            traceback.print_exc()
            input("FEHLER: SystemExit\nDrücke Enter zum Beenden...")
            sys.exit(1)
        except Exception as _gui_err:
            log.error("GUI-Fehler: %s", _gui_err, exc_info=True)
            import traceback
            _tb = traceback.format_exc()
            log.error(_tb)
            # Versuche, Fehler in einer MessageBox anzuzeigen
            try:
                import tkinter as tk
                from tkinter import messagebox as _mb
                _root = tk.Tk()
                _root.withdraw()
                _mb.showerror("GUI-Fehler", f"FEHLER: {_gui_err}\n\n{_tb}")
                _root.destroy()
            except Exception:
                pass
            input(f"\nFEHLER: {_gui_err}\n\n{_tb}\nDrücke Enter zum Beenden...")
            sys.exit(1)


if __name__ == "__main__":
    main()
