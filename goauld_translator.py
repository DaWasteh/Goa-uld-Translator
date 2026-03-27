#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   STARGATE — GOA'ULD LINGUISTIC INTERFACE  v2.0                 ║
║   SGC Xenolinguistics Division  ·  Classification: LEVEL 28    ║
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

import re
import os
import sys
import argparse
import difflib
import threading
from pathlib import Path
from typing import Optional


# ── Dependency Check ──────────────────────────────────────────────────────────

try:
    import customtkinter as ctk
    from customtkinter import ThemeManager
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    # Auto-install attempt
    try:
        import subprocess
        print("[INFO] CustomTkinter nicht gefunden — versuche automatische Installation…")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "customtkinter", "--quiet"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            import customtkinter as ctk
            from customtkinter import ThemeManager
            CTK_AVAILABLE = True
            print("[OK] CustomTkinter erfolgreich installiert!")
        else:
            print("[HINWEIS] CustomTkinter konnte nicht automatisch installiert werden.")
            print("          Manuelle Installation: python -m pip install customtkinter")
            print("          Falls pip defekt ist: python -m ensurepip --upgrade")
    except Exception as _install_err:
        print(f"[HINWEIS] Auto-Install fehlgeschlagen: {_install_err}")
        print("          Manuelle Installation: python -m pip install customtkinter")

try:
    import tkinter as tk
    import tkinter.ttk as ttk
    import tkinter.messagebox as messagebox
    import tkinter.filedialog as filedialog
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
MD_CANDIDATES = [
    "opus4.6-en-language-analysis.md",
    "goauld_dictionary.md",
    "dictionary.md",
]


# ─────────────────────────────────────────────────────────────────────────────
# MARKDOWN PARSER
# ─────────────────────────────────────────────────────────────────────────────

# Header cells we skip (those are the table-header rows, not data)
_SKIP_FIRST = {"goa'uld", "phrase", "abydonian", "goauld"}
_SKIP_SECOND = {"meaning", "english", "translation", "compound analysis",
                "context", "notes", "episode", "speaker", "source / episode"}


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
        meaning  – English / German meaning
        section  – which section of the dictionary (e.g. "Battle cries")
        source   – episode / source reference (optional)
    """
    entries: list[dict] = []
    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError as exc:
        print(f"[WARNUNG] Markdown-Datei nicht lesbar: {exc}")
        return entries

    current_section = "Allgemein"

    for raw in lines:
        line = raw.rstrip("\n")

        # Track section headings
        if line.startswith("## ") or line.startswith("# "):
            current_section = line.lstrip("#").strip()
            continue

        # Only process table rows
        if not line.startswith("|"):
            continue

        # Skip separator rows (| --- | --- |)
        if re.search(r"\|\s*[-:]+\s*\|", line):
            continue

        parts = [_clean(p) for p in line.split("|")]
        # Remove leading / trailing empty strings from split artefact
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

        entries.append({
            "goauld":  col0,
            "meaning": col1,
            "section": current_section,
            "source":  col2,
        })

    return entries


# ─────────────────────────────────────────────────────────────────────────────
# EMBEDDED FALLBACK VOCABULARY  (aus dem Original-Script, deutlich erweitert)
# ─────────────────────────────────────────────────────────────────────────────

EMBEDDED_VOCAB: list[dict] = [
    # ── Core ──────────────────────────────────────────────────────────────
    {"goauld": "Kree",          "meaning": "Achtung! Zuhören! Imperativ-Partikel", "section": "Kern", "source": "Throughout"},
    {"goauld": "Kek",           "meaning": "Tod; Schwäche (wer schwach ist, ist wie tot)", "section": "Kern", "source": "Orpheus"},
    {"goauld": "Kel",           "meaning": "Fragepartikel: wo, wann, was", "section": "Kern", "source": "Ultimate Visual Guide"},
    {"goauld": "Nok",           "meaning": "Jetzt", "section": "Kern", "source": "Ultimate Visual Guide"},
    {"goauld": "Mel",           "meaning": "Sterben; enden; danach", "section": "Kern", "source": "Ultimate Visual Guide"},
    {"goauld": "Hol",           "meaning": "Halten; Stopp", "section": "Kern", "source": "Ultimate Visual Guide"},
    {"goauld": "Shal",          "meaning": "Was, welche", "section": "Kern", "source": "Ultimate Visual Guide"},
    {"goauld": "Tal",           "meaning": "Warten; auch: sterben", "section": "Kern", "source": "Ultimate Visual Guide"},
    {"goauld": "Tak",           "meaning": "Trick; Unehrlichkeit", "section": "Kern", "source": "Ultimate Visual Guide"},
    {"goauld": "Tok",           "meaning": "Gegen; widerstehen", "section": "Kern", "source": "The Tok'ra"},
    {"goauld": "Tel",           "meaning": "Ich; Ich habe", "section": "Kern", "source": "Ultimate Visual Guide"},
    {"goauld": "Mak",           "meaning": "Meine Identität", "section": "Kern", "source": "Ultimate Visual Guide"},
    {"goauld": "Mok",           "meaning": "Deine Identität", "section": "Kern", "source": "Ultimate Visual Guide"},
    {"goauld": "Ta",            "meaning": "Ich (Pronomen)", "section": "Kern", "source": "SGCommand Wiki"},
    {"goauld": "Lo",            "meaning": "Du (Pronomen)", "section": "Kern", "source": "SGCommand Wiki"},
    {"goauld": "Tap",           "meaning": "Wir (Plural von Ta)", "section": "Kern", "source": "SGCommand Wiki"},
    {"goauld": "Lop",           "meaning": "Ihr alle (Plural von Lo)", "section": "Kern", "source": "SGCommand Wiki"},
    {"goauld": "Ka",            "meaning": "Nein", "section": "Kern", "source": "SGCommand Wiki"},
    {"goauld": "Re",            "meaning": "Komm", "section": "Kern", "source": "StargateWiki"},
    {"goauld": "Onak",          "meaning": "Gott; Goa'uld (aus Unas: onac)", "section": "Titel", "source": "Summit"},
    {"goauld": "Tar",           "meaning": "Umgangssprachlich für 'Mensch' (von Tau'ri)", "section": "Titel", "source": "RPG Lexicon"},
    {"goauld": "Shree",         "meaning": "Eindringling; Schänder", "section": "Beleidigungen", "source": "StargateWiki"},
    {"goauld": "Bet",           "meaning": "Kapitulation; möglicherweise: Waffe", "section": "Kampf", "source": "SGCommand Wiki"},
    {"goauld": "Leaa",          "meaning": "Zuhören", "section": "Kern", "source": "RPG Lexicon"},
    # ── Greetings ─────────────────────────────────────────────────────────
    {"goauld": "Tek'ma'te",     "meaning": "Meister, gut getroffen — formelle Begrüßung an Vorgesetzte", "section": "Begrüßungen", "source": "Children of the Gods"},
    {"goauld": "Tek'ma'tek",    "meaning": "Freunde, gut getroffen; wir kommen in Frieden — Begrüßung unter Gleichen", "section": "Begrüßungen", "source": "Throughout"},
    {"goauld": "Tak mal tiak",  "meaning": "Du wirst erinnert — formelle, ehrerbietige Begrüßung", "section": "Begrüßungen", "source": "SGCommand"},
    {"goauld": "Tal'ma'te",     "meaning": "Liebevolle Begrüßung oder Abschied — zwischen Vertrauten", "section": "Begrüßungen", "source": "Throughout"},
    {"goauld": "Chel hol",      "meaning": "Standardbegrüßung", "section": "Begrüßungen", "source": "Ultimate Visual Guide"},
    {"goauld": "Kel'sha",       "meaning": "Es wird so sein / wie du es wünschst / freundliche Begrüßung", "section": "Begrüßungen", "source": "Within the Serpent's Grasp"},
    {"goauld": "Lek tol",       "meaning": "Auf Wiedersehen; Abschalten", "section": "Begrüßungen", "source": "SGCommand"},
    {"goauld": "Shal met",      "meaning": "Toast; Prost — Jaffa-Trinkbrauch", "section": "Begrüßungen", "source": "SGCommand"},
    {"goauld": "Ral tora ke",   "meaning": "Viel Glück", "section": "Begrüßungen", "source": "A Hundred Days"},
    {"goauld": "Chel nok",      "meaning": "Viel Glück; sehr gute Wünsche", "section": "Begrüßungen", "source": "Ultimate Visual Guide"},
    {"goauld": "Quell shak",    "meaning": "Bitte", "section": "Begrüßungen", "source": "Ultimate Visual Guide"},
    {"goauld": "Ba'ja'kakma'te","meaning": "Ich grüße dich auch — Antwort auf Begrüßung", "section": "Begrüßungen", "source": "SGCommand"},
    # ── Battle cries ──────────────────────────────────────────────────────
    {"goauld": "Dal shakka mel", "meaning": "Ich sterbe frei! — Jaffa-Schlachtruf", "section": "Kampfrufe", "source": "The Nox"},
    {"goauld": "Shel kek nem ron","meaning": "Ich sterbe frei — Freie Jaffa Passwort", "section": "Kampfrufe", "source": "Birthright"},
    {"goauld": "Kalach shal tek","meaning": "Sieg oder Tod! (wörtl.: Seele kehrt heim)", "section": "Kampfrufe", "source": "Ultimate Visual Guide"},
    {"goauld": "Arik tree'ac te kek","meaning": "Wir ergeben uns nicht, auch nicht im Tod", "section": "Kampfrufe", "source": "Allegiance"},
    {"goauld": "Tal shak",      "meaning": "Angriff! / Auf der Hut sein", "section": "Kampfrufe", "source": "Ultimate Visual Guide"},
    {"goauld": "Tal bet",       "meaning": "Ergebt euch / Waffen niederlegen", "section": "Kampfrufe", "source": "StargateWiki"},
    {"goauld": "Shel norak",    "meaning": "Ergebt euch oder sterbt", "section": "Kampfrufe", "source": "StargateWiki"},
    {"goauld": "Mol kek",       "meaning": "Tötet sie alle!", "section": "Kampfrufe", "source": "Ultimate Visual Guide"},
    {"goauld": "Hol mel",       "meaning": "Feuer einstellen; Warteposition", "section": "Kampfrufe", "source": "Ultimate Visual Guide"},
    {"goauld": "Mel nok tee",   "meaning": "Jetzt evakuieren!", "section": "Kampfrufe", "source": "Ultimate Visual Guide"},
    {"goauld": "Kel'tesh",      "meaning": "Flankierender Angriff von zwei Seiten — Jaffa-Taktik", "section": "Kampfrufe", "source": "Icon"},
    {"goauld": "Shal kek",      "meaning": "Entlassen / Weggetreten", "section": "Kampfrufe", "source": "Ultimate Visual Guide"},
    {"goauld": "Hahl kree",     "meaning": "Freeze! Keine Bewegung!", "section": "Kampfrufe", "source": "Ultimate Visual Guide"},
    {"goauld": "Kree tal shal mak","meaning": "Identifiziere dich!", "section": "Kampfrufe", "source": "Throughout"},
    {"goauld": "Kree hol",      "meaning": "Los, wir gehen!", "section": "Kampfrufe", "source": "Throughout"},
    {"goauld": "Aray kree",     "meaning": "Bleib wo du bist", "section": "Kampfrufe", "source": "Ultimate Visual Guide"},
    {"goauld": "Shak'na kree",  "meaning": "Befehl zur Kapitulation oder zum Sterben", "section": "Kampfrufe", "source": "StargateWiki"},
    # ── Insults ───────────────────────────────────────────────────────────
    {"goauld": "Shol'va",       "meaning": "Verräter; Ketzer — berühmteste Beleidigung der Serie", "section": "Beleidigungen", "source": "Throughout"},
    {"goauld": "Hasshak",       "meaning": "Schwächling, Kanonenfutter, Narr — Bra'tacs Lieblingsbeleidigung", "section": "Beleidigungen", "source": "Bloodlines"},
    {"goauld": "Ha'taaka",      "meaning": "Kindermörder, Geistvergifter — extreme Beleidigung", "section": "Beleidigungen", "source": "Family"},
    {"goauld": "Kresh'taa",     "meaning": "Außenseiter; Verbannter; Unberührbarer", "section": "Beleidigungen", "source": "Bloodlines"},
    {"goauld": "Gonach",        "meaning": "Grobe Beleidigung (genaue Bedeutung unbekannt)", "section": "Beleidigungen", "source": "Fair Game"},
    {"goauld": "Goe'nahk",      "meaning": "Idiot!", "section": "Beleidigungen", "source": "Maj C's Dictionary"},
    {"goauld": "Mikta",         "meaning": "Hinterteil — anatomische Beleidigung", "section": "Beleidigungen", "source": "Seth"},
    {"goauld": "Mai'tac",       "meaning": "Verdammt!", "section": "Beleidigungen", "source": "Ultimate Visual Guide"},
    {"goauld": "Orak",          "meaning": "Unaussprechlich — für Kull-Krieger verwendet", "section": "Beleidigungen", "source": "New Order"},
    {"goauld": "Klavel ha",     "meaning": "Zu spät", "section": "Beleidigungen", "source": "Enemies"},
    # ── Titles & Ranks ────────────────────────────────────────────────────
    {"goauld": "Goa'uld",       "meaning": "Gott / Kinder der Götter — Eigenbezeichnung der Spezies", "section": "Titel", "source": "Children of the Gods"},
    {"goauld": "Jaffa",         "meaning": "Diener-Krieger; Symbionten-Brutträger", "section": "Titel", "source": "Children of the Gods"},
    {"goauld": "Tok'ra",        "meaning": "Gegen Ra — Rebellische Goa'uld-Fraktion", "section": "Titel", "source": "The Tok'ra"},
    {"goauld": "Tau'ri",        "meaning": "Die Erste Welt / Erdenbewohner", "section": "Titel", "source": "The Enemy Within"},
    {"goauld": "Lo'taur",       "meaning": "Höchstrangiger menschlicher Sklave (wörtl.: Du, Mensch!)", "section": "Titel", "source": "Summit"},
    {"goauld": "Ashrak",        "meaning": "Jäger — Elite-Goa'uld-Attentäter", "section": "Titel", "source": "In the Line of Duty"},
    {"goauld": "Hok'tar",       "meaning": "Fortgeschrittener Mensch — genetisch überlegen", "section": "Titel", "source": "Rite of Passage"},
    {"goauld": "Harcesis",      "meaning": "Kind zweier Goa'uld-Wirte (trägt genetisches Gedächtnis)", "section": "Titel", "source": "Maternal Instinct"},
    {"goauld": "Teal'c",        "meaning": "Stärke", "section": "Titel", "source": "Past and Present"},
    {"goauld": "Reenlokia",     "meaning": "Die Asgard", "section": "Titel", "source": "Ultimate Visual Guide"},
    {"goauld": "Kin'dra",       "meaning": "Stellvertreter; Zweiter im Kommando", "section": "Titel", "source": "GateWorld Omnipedia"},
    {"goauld": "Dis'tra",       "meaning": "Meister", "section": "Titel", "source": "The Nox"},
    {"goauld": "Cha'tii",       "meaning": "Krieger-Lehrling", "section": "Titel", "source": "RPG Lexicon"},
    # ── Technology ────────────────────────────────────────────────────────
    {"goauld": "Chappa'ai",     "meaning": "Sternentor / Stargate", "section": "Technologie", "source": "Throughout"},
    {"goauld": "Chappa'ko",     "meaning": "Supergate", "section": "Technologie", "source": "Stargate SG-1"},
    {"goauld": "Ha'tak",        "meaning": "Pyramiden-Mutterschiff / Angriffsraumschiff", "section": "Technologie", "source": "Throughout"},
    {"goauld": "Al'kesh",       "meaning": "Mittelschwerer Bomber", "section": "Technologie", "source": "Throughout"},
    {"goauld": "Tel'tak",       "meaning": "Frachtraumschiff", "section": "Technologie", "source": "Throughout"},
    {"goauld": "Pel'tak",       "meaning": "Brücke / Kommandoraum eines Ha'tak", "section": "Technologie", "source": "Throughout"},
    {"goauld": "Zat'nik'tel",   "meaning": "Energie-Seitenwaffe (1× betäubt, 2× tötet, 3× desintegriert)", "section": "Technologie", "source": "Throughout"},
    {"goauld": "Ma'tok",        "meaning": "Stabwaffe", "section": "Technologie", "source": "Throughout"},
    {"goauld": "Kara kesh",     "meaning": "Handgerät (Bandgerät)", "section": "Technologie", "source": "RPG Source"},
    {"goauld": "Udajeet",       "meaning": "Todesgleiter — Goa'uld-Kampfjet", "section": "Technologie", "source": "Throughout"},
    {"goauld": "Intar",         "meaning": "Trainings-Betäubungswaffe (roter Kristall)", "section": "Technologie", "source": "Rules of Engagement"},
    {"goauld": "Naquadah",      "meaning": "Quartzit-Mineral — Grundlage der Goa'uld-Technologie", "section": "Technologie", "source": "Throughout"},
    {"goauld": "Naquadria",     "meaning": "Instabile Variante von Naquadah", "section": "Technologie", "source": "Meridian"},
    {"goauld": "Nish'ta",       "meaning": "Biologische Gehirnwäsche-Verbindung", "section": "Technologie", "source": "Seth"},
    {"goauld": "Vo'cume",       "meaning": "Hologramm-Projektor / Kommunikationsgerät", "section": "Technologie", "source": "Rules of Engagement"},
    {"goauld": "Tretonin",      "meaning": "Medizin aus Symbionten synthetisiert", "section": "Technologie", "source": "The Changeling"},
    # ── Rituals & Culture ─────────────────────────────────────────────────
    {"goauld": "Kel'no'reem",   "meaning": "Tiefer Meditationstrance (ersetzt Schlaf für Jaffa)", "section": "Rituale", "source": "Holiday"},
    {"goauld": "Prim'ta",       "meaning": "Larven-Symbiont UND die Implantationszeremonie", "section": "Rituale", "source": "Bloodlines"},
    {"goauld": "Prata",         "meaning": "Pubertät — Alter der ersten Prim'ta-Zeremonie", "section": "Rituale", "source": "Ultimate Visual Guide"},
    {"goauld": "Bashaak",       "meaning": "Jaffa-Krieger-Training / Holz-Übungsstab", "section": "Rituale", "source": "The Warrior"},
    {"goauld": "Shim'roa",      "meaning": "Flitterwochen", "section": "Rituale", "source": "Ultimate Visual Guide"},
    {"goauld": "Cal mah",       "meaning": "Heiligtum — heilige Bezeichnung", "section": "Rituale", "source": "Serpent's Song"},
    {"goauld": "Korush'nai",    "meaning": "Umkehren — Warnung auf verseuchten Welten", "section": "Rituale", "source": "There But for the Grace of God"},
    {"goauld": "Dakara",        "meaning": "Heiliger Ort der ersten Prim'ta-Zeremonie", "section": "Orte", "source": "Reckoning"},
    {"goauld": "Kheb",          "meaning": "Jaffa-Jenseits / Ort der Erleuchtung", "section": "Orte", "source": "Maternal Instinct"},
    {"goauld": "Joma secu",     "meaning": "Führungsherausforderung — Kampf auf Leben und Tod", "section": "Rituale", "source": "The Warrior"},
    {"goauld": "Kel shak lo",   "meaning": "Ritueller Kampf auf Leben und Tod zur Sühne eines Unrechts (Sodan)", "section": "Rituale", "source": "Babylon"},
    {"goauld": "Sim'ka",        "meaning": "Verlobte — altertümlicher Begriff", "section": "Gesellschaft", "source": "Ultimate Visual Guide"},
    {"goauld": "Sodan",         "meaning": "Legendäre freie Jaffa-Gruppe (seit 5000+ Jahren unabhängig)", "section": "Titel", "source": "Babylon"},
    # ── Key phrases ───────────────────────────────────────────────────────
    {"goauld": "Mekta satak Oz","meaning": "Meine Identität ist der Große und Mächtige Oz! (O'Neill)", "section": "Phrasen", "source": "Tangent"},
    {"goauld": "Jaffa, kree",   "meaning": "Hört zu, Jaffa! / Jaffa, Achtung!", "section": "Phrasen", "source": "Throughout"},
    {"goauld": "Niss trah",     "meaning": "Ich bin hier!", "section": "Phrasen", "source": "Ultimate Visual Guide"},
    {"goauld": "Mak lo onak",   "meaning": "Oh mein Gott!", "section": "Phrasen", "source": "Ultimate Visual Guide"},
    {"goauld": "Mak tal shree! Lo tak.", "meaning": "Ich bin ein Herr.", "section": "Phrasen", "source": "Ultimate Visual Guide"},
    {"goauld": "Shin tel",      "meaning": "Was ist los?", "section": "Phrasen", "source": "Ultimate Visual Guide"},
    {"goauld": "Kel nok shree Jaffa","meaning": "Ich bin kein Jaffa", "section": "Phrasen", "source": "Into the Fire"},
    {"goauld": "Pal tiem shree tal ma","meaning": "Unsere Liebe endet nicht im Tod", "section": "Phrasen", "source": "Ultimate Visual Guide"},
    {"goauld": "Kal kek m'al shol'va","meaning": "Bereit zu sterben, Verräter?", "section": "Phrasen", "source": "RPG Lexicon"},
    {"goauld": "Lo tak meta satak Oz","meaning": "Du sprichst mit dem Großen Oz / Ich bin der Große Oz (Doppelsatz!)", "section": "Phrasen", "source": "Tangent"},
    {"goauld": "Benna! Ya wan ya duru!","meaning": "Kniet nieder vor euren Herren!", "section": "Phrasen", "source": "Ultimate Visual Guide"},
    {"goauld": "Shor'wai'e! Yas! Yas!","meaning": "Beeil dich! Jetzt, jetzt!", "section": "Phrasen", "source": "Unleashed Ep 1"},
    # ── Abydonian dialect ─────────────────────────────────────────────────
    {"goauld": "Na-nay",        "meaning": "Nein, tu das nicht — Abydonian", "section": "Abydonian", "source": "Kasuf/Klorel"},
    {"goauld": "Ti'u",          "meaning": "Ja — Abydonian", "section": "Abydonian", "source": "Film"},
    {"goauld": "Bi'bo",         "meaning": "Möchtest du? / Nimm! — Abydonian", "section": "Abydonian", "source": "Kasuf"},
    {"goauld": "Bonniewae",     "meaning": "Sehr gut, wohlschmeckend — Abydonian", "section": "Abydonian", "source": "Kasuf"},
    {"goauld": "Bradio",        "meaning": "Komm schon! Beeil dich! — Abydonian", "section": "Abydonian", "source": "Kasuf"},
    {"goauld": "Di'dak'dida",   "meaning": "Du wagst es?! — Abydonian", "section": "Abydonian", "source": "Film"},
    {"goauld": "Ke'i",          "meaning": "Knie nieder! — Abydonian", "section": "Abydonian", "source": "Film"},
    {"goauld": "Kegalo",        "meaning": "Stille! — Abydonian", "section": "Abydonian", "source": "Film"},
    {"goauld": "Noc'ri'ton",    "meaning": "Hilf mir hier raus — Abydonian", "section": "Abydonian", "source": "Serpent's Lair"},
    {"goauld": "A'roush",       "meaning": "Dorf — Abydonian", "section": "Abydonian", "source": "Film"},
    # ── Numbers & misc ────────────────────────────────────────────────────
    {"goauld": "Noc",           "meaning": "Nein", "section": "Grundvokabular", "source": "Within the Serpent's Grasp"},
    {"goauld": "Arik",          "meaning": "Ja", "section": "Grundvokabular", "source": "SGCommand"},
    {"goauld": "Chel'nak",      "meaning": "Sehr gut; ausgezeichnet", "section": "Grundvokabular", "source": "SGCommand"},
    {"goauld": "Maa",           "meaning": "Vielleicht", "section": "Grundvokabular", "source": "SGCommand"},
    {"goauld": "Haa",           "meaning": "Okay", "section": "Grundvokabular", "source": "SGCommand"},
    {"goauld": "Ma'ate",        "meaning": "Verstanden; Wahrheit; Gerechtigkeit", "section": "Grundvokabular", "source": "SGCommand"},
    {"goauld": "Kree nok",      "meaning": "Achtung, jetzt! (effektiv: Halt den Mund)", "section": "Grundvokabular", "source": "Ultimate Visual Guide"},
    {"goauld": "Naquadah",      "meaning": "Quartzit-Mineral — Basis der Goa'uld-Energie-Technologie", "section": "Technologie", "source": "Throughout"},
    {"goauld": "Ra",            "meaning": "Herrschaft; Herr; Sonnengott — System Lord", "section": "Titel", "source": "Film"},
    {"goauld": "Ma'at",         "meaning": "Wahrheit; Gerechtigkeit; Ordnung; Schönheit", "section": "Grundvokabular", "source": "Ägyptische Mythologie"},
    {"goauld": "Sutekh",        "meaning": "Chaos; das Böse; Feind", "section": "Grundvokabular", "source": "Ägyptische Mythologie"},
    {"goauld": "M'al Sharran",  "meaning": "Letzter Ritus — Krieger wird an den Rand des Todes gebracht um Gehirnwäsche zu brechen", "section": "Rituale", "source": "Threshold"},
    {"goauld": "Shesh'ta",      "meaning": "Goa'uld/Jaffa-Währungseinheit", "section": "Gesellschaft", "source": "Family"},
    {"goauld": "Nek'sed",       "meaning": "Blitzkanone", "section": "Technologie", "source": "RPG sourcebook"},
    {"goauld": "Ra'kek",        "meaning": "Sonnenstoß-Granate", "section": "Technologie", "source": "RPG sourcebook"},
    {"goauld": "Krantu",        "meaning": "Klingenschaft-Waffe (Sodan)", "section": "Technologie", "source": "Babylon"},
]


# ─────────────────────────────────────────────────────────────────────────────
# SEARCH ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class SearchEngine:
    """
    Bidirektionale Suche mit exaktem Matching, Präfix-Matching und Fuzzy-Matching.
    """

    def __init__(self, entries: list[dict]) -> None:
        self.entries = entries
        # Deduplicate by (goauld_lower, meaning_lower) – keep later (MD preferred)
        seen: set[tuple] = set()
        unique: list[dict] = []
        for e in reversed(entries):
            key = (e["goauld"].lower(), e["meaning"].lower())
            if key not in seen:
                seen.add(key)
                unique.append(e)
        self.entries = list(reversed(unique))

    # ─── public api ──────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        direction: str = "goa2de",
        max_results: int = 80,
        fuzzy_threshold: float = 0.45,
        lang_pref: str = "de",
    ) -> list[dict]:
        """
        direction:  'goa2de' → suche in goauld-Spalte
                    'de2goa' → suche in meaning-Spalte
        lang_pref:  'de' → deutsche Einträge zuerst
                    'en' → englische Einträge zuerst
        """
        q = query.strip()
        if not q:
            return []
        q_low = q.lower()

        field = "goauld" if direction == "goa2de" else "meaning"

        results: list[tuple[float, dict]] = []

        for e in self.entries:
            val = e[field].lower()
            base_score = self._score(q_low, val)
            if base_score > 0:
                # Sprach-Bonus: bevorzugte Sprache +8 Punkte
                lang_bonus = 8 if e.get("lang", "de") == lang_pref else 0
                results.append((base_score + lang_bonus, e))

        results.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in results[:max_results]]

    def search_all(self, query: str, max_results: int = 80) -> list[dict]:
        """Suche in beiden Feldern gleichzeitig."""
        q = query.strip()
        if not q:
            return []
        q_low = q.lower()
        best: dict[int, tuple[int, dict]] = {}  # id(entry) → (score, entry)

        for e in self.entries:
            score_g = self._score(q_low, e["goauld"].lower())
            score_m = self._score(q_low, e["meaning"].lower())
            score = max(score_g, score_m)
            if score > 0:
                eid = id(e)
                if eid not in best or best[eid][0] < score:
                    best[eid] = (score, e)

        results = sorted(best.values(), key=lambda x: x[0], reverse=True)
        return [e for _, e in results[:max_results]]

    # ─── private ─────────────────────────────────────────────────────────────

    @staticmethod
    def _score(query: str, value: str, fuzzy_threshold: float = 0.42) -> int:
        if value == query:
            return 100
        if value.startswith(query):
            return 85
        if query in value:
            return 70
        # word-level match
        value_words = re.split(r"[\s,;/!?()]+", value)
        if any(w.startswith(query) for w in value_words if w):
            return 60
        if any(query in w for w in value_words if w):
            return 50
        # fuzzy
        ratio = difflib.SequenceMatcher(None, query, value).ratio()
        if ratio >= fuzzy_threshold:
            return int(ratio * 45)
        return 0


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

    def analyze(self, text: str, direction: str, lang_pref: str = "de") -> list[dict]:
        """
        Returns list of token dicts:
            token        – original word
            primary      – best-match entry or None
            alternatives – up to 3 further entries
            found        – True/False
        """
        raw_tokens = re.split(r"(\s+)", text.strip())
        result: list[dict] = []
        for tok in raw_tokens:
            if not tok:
                continue
            clean = tok.strip(".,!?;:")
            if not clean or not self._WORD_RE.match(clean):
                continue
            matches = self.engine.search(clean, direction=direction,
                                         max_results=7, lang_pref=lang_pref)
            if matches:
                result.append({
                    "token":        clean,
                    "primary":      matches[0],
                    "alternatives": matches[1:4],
                    "found":        True,
                })
            else:
                result.append({
                    "token":        clean,
                    "primary":      None,
                    "alternatives": [],
                    "found":        False,
                })
        return result

    def build_translation(self, analysis: list[dict],
                          direction: str = "goa2de") -> str:
        """
        Erzeugt die kompakte Übersetzung.
        goa2de → gibt die deutsche/englische Bedeutung aus
        de2goa → gibt das Goa'uld-Wort aus
        """
        parts: list[str] = []
        for item in analysis:
            if not item["found"]:
                parts.append(f"[{item['token']}?]")
            else:
                prim = item["primary"]

                if direction == "de2goa":
                    # Output: the Goa'uld word itself
                    word = prim["goauld"].split("/")[0].strip()
                    if word:
                        parts.append(word)
                else:
                    # Output: the German meaning, prefer DE entries
                    best = prim
                    for alt in item["alternatives"]:
                        if alt.get("lang") == "de" and prim.get("lang") != "de":
                            best = alt
                            break
                    m = best["meaning"]
                    m = re.split(r"\s*[;—]\s*", m)[0]
                    m = re.sub(r"\s*\(.*?\)\s*", " ", m).strip()
                    m = re.sub(r"\s+", " ", m).strip()
                    m = re.sub(r"^[-–▸→✦◆◉☓]+\s*", "", m).strip()
                    m = m.strip('"\'').strip()
                    if m:
                        parts.append(m)
        return " ".join(parts) if parts else "—"


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


def translate_text(text: str, mapping: dict[str, str]) -> str:
    """Übersetzt einen Freitext-Satz Wort für Wort."""
    text_lower = text.strip().lower()
    if text_lower in mapping:
        return preserve_case(text.strip(), mapping[text_lower])

    tokens = re.split(r"([A-Za-zÄÖÜäöüßÀ-ÿ']+)", text)
    result = []
    for tok in tokens:
        if not tok:
            continue
        if re.match(r"^[A-Za-zÄÖÜäöüßÀ-ÿ']+$", tok):
            low = tok.lower()
            if low in mapping:
                result.append(preserve_case(tok, mapping[low]))
            else:
                result.append(tok)
        else:
            result.append(tok)
    return "".join(result)


# ─────────────────────────────────────────────────────────────────────────────
# GUI  — CustomTkinter / Tkinter
# ─────────────────────────────────────────────────────────────────────────────

def find_md_file(hint: Optional[str] = None) -> Optional[str]:
    """Sucht die Markdown-Datei an verschiedenen Standard-Speicherorten."""
    search_paths = [hint] if hint else []
    # Versuche Verzeichnis des Skripts
    script_dir = Path(sys.argv[0]).parent
    for name in MD_CANDIDATES:
        search_paths += [
            str(script_dir / name),
            str(Path.cwd() / name),
            str(Path.home() / name),
        ]
    for p in search_paths:
        if p and Path(p).is_file():
            return str(p)
    return None


class GoauldApp:
    """
    Haupt-GUI-Anwendung.  Läuft mit CustomTkinter (bevorzugt) oder
    Standard-Tkinter als Fallback.
    """

    # ─── Initialisierung ─────────────────────────────────────────────────────

    def __init__(self, md_path: Optional[str] = None) -> None:
        self._all_entries: list[dict] = list(EMBEDDED_VOCAB)
        self._md_path: Optional[str] = None
        self._load_md(md_path)
        self._engine = SearchEngine(self._all_entries)
        self._analyzer = SentenceAnalyzer(self._engine)
        self._direction = "goa2de"
        self._lang_pref: str = "de"          # DE = Deutsch bevorzugt
        self._search_after_id: Optional[str] = None
        self._selected_entry: Optional[dict] = None
        self._sentence_mode: bool = False
        self._build_gui()

    # ─── Datenladen ──────────────────────────────────────────────────────────

    def _load_md(self, path: Optional[str]) -> None:
        found = find_md_file(path)
        if found:
            md_entries = parse_markdown_dictionary(found)
            if md_entries:
                # MD-Datei hat englische Bedeutungen → lang="en"
                md_tagged  = [{**e, "lang": "en"} for e in md_entries]
                # Eingebettetes Vokabular hat deutsche Bedeutungen → lang="de"
                emb_tagged = [{**e, "lang": "de"} for e in EMBEDDED_VOCAB]
                self._all_entries = md_tagged + emb_tagged
                self._md_path = found
                print(f"[OK] Markdown geladen: {found}  ({len(md_entries)} Einträge)")
            else:
                print(f"[WARN] Keine Einträge aus MD-Datei extrahiert: {found}")
        else:
            self._all_entries = [{**e, "lang": "de"} for e in EMBEDDED_VOCAB]
            print("[INFO] Keine MD-Datei gefunden – nutze eingebettetes Vokabular.")

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
        self.root.geometry("1100x720")
        self.root.minsize(800, 550)
        self.root.configure(fg_color=C["bg_root"])

        self._configure_ctk_fonts()
        self._build_header_ctk()
        self._build_controls_ctk()
        self._build_main_ctk()
        self._build_statusbar_ctk()
        self._update_status()

    def _configure_ctk_fonts(self) -> None:
        import tkinter.font as tkfont
        # Pre-register fonts so they can be reused
        pass  # CTk accepts tuple fonts directly

    def _build_header_ctk(self) -> None:
        hdr = ctk.CTkFrame(self.root, fg_color=C["bg_panel"],
                           corner_radius=0, height=76)
        hdr.pack(fill="x", padx=0, pady=0)
        hdr.pack_propagate(False)

        # Left: gate ring decoration
        gate_frame = ctk.CTkFrame(hdr, fg_color="transparent", width=54)
        gate_frame.pack(side="left", padx=(14, 0))
        gate_frame.pack_propagate(False)
        ctk.CTkLabel(gate_frame, text="⊕", font=("Courier", 30, "bold"),
                     text_color=C["blue_gate"]).pack(pady=12)

        # Title block
        title_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        title_frame.pack(side="left", padx=10)

        ctk.CTkLabel(
            title_frame,
            text="GOA'ULD LINGUISTIC INTERFACE",
            font=("Courier", 18, "bold"),
            text_color=C["gold_bright"],
        ).pack(anchor="w")

        # Chevron row — 9 chevrons, 7 lit
        chevrons = "".join(
            [f" {GLYPH_LOCKED}" for _ in range(7)] +
            [f" {GLYPH_CHEVRON}" for _ in range(2)]
        )
        ctk.CTkLabel(
            title_frame,
            text=chevrons,
            font=("Courier", 10),
            text_color=C["chevron"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_frame,
            text="SGC Xenolinguistics Division  ·  Stargate Command  ·  LEVEL 28",
            font=("Courier", 8),
            text_color=C["text_blue"],
        ).pack(anchor="w")

        # Right side stats
        stats_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        stats_frame.pack(side="right", padx=18)

        self._entry_count_var = ctk.StringVar(value="")
        ctk.CTkLabel(
            stats_frame,
            textvariable=self._entry_count_var,
            font=("Courier", 9, "bold"),
            text_color=C["locked_bright"],
        ).pack(anchor="e")

        src_text = (f"MD: {Path(self._md_path).name[:38]}"
                    if self._md_path else "MD: — (Fallback-Vokabular)")
        ctk.CTkLabel(
            stats_frame,
            text=src_text,
            font=("Courier", 8),
            text_color=C["text_lo"],
        ).pack(anchor="e")

        # Right gate decoration
        ctk.CTkLabel(hdr, text="⊕", font=("Courier", 30, "bold"),
                     text_color=C["blue_dim"]).pack(side="right", padx=(0, 10))

    def _build_controls_ctk(self) -> None:
        ctrl = ctk.CTkFrame(self.root, fg_color=C["bg_panel"],
                            corner_radius=0, height=52)
        ctrl.pack(fill="x", padx=0, pady=(1, 0))
        ctrl.pack_propagate(False)

        # Direction toggle
        self._dir_var = ctk.StringVar(value="goa2de")
        seg = ctk.CTkSegmentedButton(
            ctrl,
            values=["  Goa'uld  →  DE/EN  ",
                    "  DE/EN  →  Goa'uld  "],
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
        seg.pack(side="left", padx=(14, 8), pady=10)
        seg.set("  Goa'uld  →  DE/EN  ")

        # Language preference toggle (DE / EN)
        self._lang_btn_var = ctk.StringVar(value="🇩🇪 DE")
        self._lang_btn = ctk.CTkButton(
            ctrl,
            textvariable=self._lang_btn_var,
            width=58,
            height=30,
            fg_color=C["locked_dim"],
            hover_color=C["locked"],
            text_color=C["locked_bright"],
            font=("Courier", 10, "bold"),
            corner_radius=4,
            command=self._toggle_lang_pref,
        )
        self._lang_btn.pack(side="left", padx=(0, 10))

        # Separator
        ctk.CTkLabel(ctrl, text="|", text_color=C["gold_dim"],
                     font=("Courier", 16)).pack(side="left", padx=4)

        # Search icon
        ctk.CTkLabel(ctrl, text="◎", text_color=C["orange"],
                     font=("Courier", 16)).pack(side="left", padx=(8, 0))

        # Search entry — wider, with horizontal scroll hint
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search_change)
        self._entry = ctk.CTkEntry(
            ctrl,
            textvariable=self._search_var,
            placeholder_text="Wort suchen oder Satz übersetzen  ·  Goa'uld oder Deutsch  …",
            font=("Courier", 13),
            fg_color=C["bg_input"],
            border_color=C["gold_dim"],
            text_color=C["text_hi"],
            placeholder_text_color=C["text_lo"],
            border_width=1,
            corner_radius=4,
            height=32,
        )
        self._entry.pack(side="left", padx=(6, 8), pady=10, fill="x", expand=True)
        self._entry.bind("<Escape>", lambda e: self._search_var.set(""))
        self._entry.bind("<Return>", lambda e: self._do_search())

        # Clear button
        ctk.CTkButton(
            ctrl,
            text="✕",
            width=30,
            height=30,
            fg_color=C["bg_card"],
            hover_color=C["bg_hover"],
            text_color=C["gold_dim"],
            font=("Courier", 12),
            corner_radius=4,
            command=lambda: self._search_var.set(""),
        ).pack(side="left", padx=(0, 8))

        # Load MD button
        ctk.CTkButton(
            ctrl,
            text="📂",
            width=36,
            height=30,
            fg_color=C["bg_card"],
            hover_color=C["bg_hover"],
            text_color=C["text_mid"],
            font=("Courier", 10),
            corner_radius=4,
            command=self._browse_md,
        ).pack(side="right", padx=(0, 14))

    def _build_main_ctk(self) -> None:
        # ── Resizable PanedWindow (horizontal sash) ───────────────────────
        self._paned = tk.PanedWindow(
            self.root,
            orient="horizontal",
            bg=C["blue_gate"],
            sashrelief="flat",
            sashwidth=5,
            sashpad=0,
            showhandle=False,
            bd=0,
        )
        self._paned.pack(fill="both", expand=True)

        # ── LEFT: Results panel ───────────────────────────────────────────
        left_outer = tk.Frame(self._paned, bg=C["bg_panel"])
        self._paned.add(left_outer, minsize=200, width=340, stretch="never")

        left = ctk.CTkFrame(left_outer, fg_color=C["bg_panel"], corner_radius=0)
        left.pack(fill="both", expand=True)
        left.rowconfigure(2, weight=1)
        left.columnconfigure(0, weight=1)

        ctk.CTkFrame(left, fg_color=C["blue_gate"],
                     corner_radius=0, height=2).grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(
            left,
            text=f"  {GLYPH_GATE}  ERGEBNISSE",
            font=("Courier", 10, "bold"),
            text_color=C["blue_bright"],
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 2))

        self._result_scroll = ctk.CTkScrollableFrame(
            left, fg_color=C["bg_panel"], corner_radius=0)
        self._result_scroll.grid(row=2, column=0, sticky="nsew")
        self._result_scroll.columnconfigure(0, weight=1)
        self._result_rows: list[ctk.CTkFrame] = []

        # ── RIGHT: Tabbed panel (Detail | Satzanalyse) ────────────────────
        right_outer = tk.Frame(self._paned, bg=C["bg_card"])
        self._paned.add(right_outer, minsize=300, stretch="always")

        right = ctk.CTkFrame(right_outer, fg_color=C["bg_card"], corner_radius=0)
        right.pack(fill="both", expand=True)

        ctk.CTkFrame(right, fg_color=C["gold_dim"],
                     corner_radius=0, height=2).pack(fill="x")

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
        self._tabs.pack(fill="both", expand=True)
        self._tabs.add("  ◈ Detail  ")
        self._tabs.add("  ⊕ Satzanalyse  ")
        self._tabs.add("  ⚡ Übersetzer  ")

        # Detail tab
        detail_tab = self._tabs.tab("  ◈ Detail  ")
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
        sentence_tab = self._tabs.tab("  ⊕ Satzanalyse  ")
        self._sentence_text = ctk.CTkTextbox(
            sentence_tab,
            fg_color=C["bg_card"],
            text_color=C["text_hi"],
            font=("Courier", 11),
            border_width=0, corner_radius=0,
            state="disabled", wrap="word",
        )
        self._sentence_text.pack(fill="both", expand=True, padx=2, pady=2)

        # ── Übersetzer tab (live, liest aus der Suchleiste) ──────────────
        trans_tab = self._tabs.tab("  ⚡ Übersetzer  ")
        trans_tab.rowconfigure(4, weight=1)
        trans_tab.columnconfigure(0, weight=1)

        # ── Direction bar ─────────────────────────────────────────────────
        trans_hdr = ctk.CTkFrame(trans_tab, fg_color=C["blue_dim"],
                                 corner_radius=4)
        trans_hdr.grid(row=0, column=0, sticky="ew", padx=6, pady=(8, 4))
        trans_hdr.columnconfigure(0, weight=1)

        self._trans_dir_lbl = ctk.CTkLabel(
            trans_hdr,
            text=f"  {GLYPH_GATE}  Goa'uld  →  Deutsch",
            font=("Courier", 11, "bold"),
            text_color=C["blue_bright"],
            anchor="w",
        )
        self._trans_dir_lbl.grid(row=0, column=0, sticky="w", padx=10, pady=6)

        self._trans_status_lbl = ctk.CTkLabel(
            trans_hdr, text="",
            font=("Courier", 9, "bold"),
            text_color=C["locked_bright"], anchor="e",
        )
        self._trans_status_lbl.grid(row=0, column=1, sticky="e", padx=10, pady=6)

        # ── INPUT display (read-only echo of the search bar) ─────────────
        inp_frame = ctk.CTkFrame(trans_tab, fg_color=C["bg_input"],
                                 corner_radius=4,
                                 border_color=C["gold_dim"], border_width=1)
        inp_frame.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 0))
        inp_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            inp_frame,
            text=f"  EINGABE  ",
            font=("Courier", 8, "bold"),
            text_color=C["gold_dim"],
            anchor="w",
        ).grid(row=0, column=0, padx=(8, 0), pady=6)

        self._trans_input_echo = ctk.CTkLabel(
            inp_frame,
            text="—  Suchleiste benutzen",
            font=("Courier", 12),
            text_color=C["text_mid"],
            anchor="w",
            wraplength=600,
        )
        self._trans_input_echo.grid(row=0, column=1, sticky="ew", padx=4, pady=6)

        # ── Big arrow divider ─────────────────────────────────────────────
        ctk.CTkLabel(
            trans_tab,
            text=f"  ▼  ÜBERSETZUNG",
            font=("Courier", 10, "bold"),
            text_color=C["locked_bright"],
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=10, pady=(6, 2))

        # ── OUTPUT — the main result ──────────────────────────────────────
        self._trans_output = ctk.CTkTextbox(
            trans_tab,
            fg_color=C["locked_dim"],
            text_color=C["gold_bright"],
            font=("Courier", 16, "bold"),
            border_color=C["locked"],
            border_width=2,
            corner_radius=6,
            height=90,
            state="disabled",
            wrap="word",
        )
        self._trans_output.grid(row=3, column=0, sticky="ew", padx=6, pady=(0, 8))

        # ── Token breakdown ───────────────────────────────────────────────
        bd_outer = ctk.CTkFrame(trans_tab, fg_color=C["bg_panel"], corner_radius=0)
        bd_outer.grid(row=4, column=0, sticky="nsew", padx=0)
        bd_outer.rowconfigure(1, weight=1)
        bd_outer.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            bd_outer,
            text=f"  {GLYPH_SECTION}  WORT-FÜR-WORT  AUFSCHLÜSSELUNG",
            font=("Courier", 9, "bold"),
            text_color=C["gold_dim"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 2))

        self._trans_breakdown = ctk.CTkTextbox(
            bd_outer,
            fg_color=C["bg_card"],
            text_color=C["text_hi"],
            font=("Courier", 10),
            border_width=0, corner_radius=0,
            state="disabled", wrap="word",
        )
        self._trans_breakdown.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 4))

        self._trans_after_id: Optional[str] = None

        self._show_welcome_detail()

    def _build_statusbar_ctk(self) -> None:
        bar = ctk.CTkFrame(self.root, fg_color=C["bg_panel"],
                           corner_radius=0, height=24)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        # Left accent strip (event-horizon blue)
        ctk.CTkFrame(bar, fg_color=C["blue_gate"],
                     corner_radius=0, width=4).pack(side="left", fill="y")

        self._status_var = ctk.StringVar(value="")
        ctk.CTkLabel(
            bar,
            textvariable=self._status_var,
            font=("Courier", 9),
            text_color=C["text_mid"],
            anchor="w",
        ).pack(side="left", padx=10)

        ctk.CTkLabel(
            bar,
            text="STARGATE SG-1  ·  Goa'uld Linguistic Interface  ·  v3.0",
            font=("Courier", 9),
            text_color=C["text_lo"],
        ).pack(side="right", padx=12)

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
        hdr = tk.Frame(self.root, bg=C["bg_panel"], height=68)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="⬡", bg=C["bg_panel"], fg=C["gold"],
                 font=("Courier", 28)).pack(side="left", padx=(14, 0))

        tf = tk.Frame(hdr, bg=C["bg_panel"])
        tf.pack(side="left", padx=10)

        tk.Label(tf, text="GOA'ULD LINGUISTIC INTERFACE",
                 bg=C["bg_panel"], fg=C["gold_bright"],
                 font=("Courier", 16, "bold")).pack(anchor="w")

        tk.Label(tf, text="SGC Xenolinguistics Division  ·  Classification: LEVEL 28",
                 bg=C["bg_panel"], fg=C["text_mid"],
                 font=("Courier", 9)).pack(anchor="w")

        rf = tk.Frame(hdr, bg=C["bg_panel"])
        rf.pack(side="right", padx=14)

        self._entry_count_var = tk.StringVar()
        tk.Label(rf, textvariable=self._entry_count_var,
                 bg=C["bg_panel"], fg=C["gold_dim"],
                 font=("Courier", 9)).pack(anchor="e")

        src_text = (f"MD: {Path(self._md_path).name[:40]}"
                    if self._md_path else "MD: — (Fallback-Vokabular)")
        tk.Label(rf, text=src_text, bg=C["bg_panel"], fg=C["text_lo"],
                 font=("Courier", 8)).pack(anchor="e")

        tk.Label(hdr, text="⬡", bg=C["bg_panel"], fg=C["gold"],
                 font=("Courier", 28)).pack(side="right", padx=(0, 4))

    def _build_controls_tk(self) -> None:
        ctrl = tk.Frame(self.root, bg=C["bg_panel"], height=48)
        ctrl.pack(fill="x", pady=(1, 0))
        ctrl.pack_propagate(False)

        self._dir_var = tk.StringVar(value="goa2de")

        tk.Radiobutton(
            ctrl,
            text="  Goa'uld → Dt/En  ",
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
        ).pack(side="left", padx=(14, 2), pady=8)

        tk.Radiobutton(
            ctrl,
            text="  Dt/En → Goa'uld  ",
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
        ).pack(side="left", padx=2, pady=8)

        tk.Label(ctrl, text=" ◎ ", bg=C["bg_panel"], fg=C["orange"],
                 font=("Courier", 14)).pack(side="left", padx=(14, 0))

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search_change)
        self._entry = tk.Entry(
            ctrl,
            textvariable=self._search_var,
            bg=C["bg_input"],
            fg=C["text_hi"],
            insertbackground=C["gold"],
            font=("Courier", 13),
            relief="flat",
            bd=0,
            width=38,
        )
        self._entry.pack(side="left", padx=(4, 8), pady=10, ipady=5)
        self._entry.bind("<Escape>", lambda e: self._search_var.set(""))

        tk.Button(
            ctrl,
            text="✕",
            bg=C["bg_card"],
            fg=C["gold_dim"],
            activebackground=C["bg_hover"],
            activeforeground=C["gold"],
            font=("Courier", 11),
            relief="flat",
            bd=0,
            padx=6, pady=3,
            command=lambda: self._search_var.set(""),
        ).pack(side="left", padx=(0, 12))

        tk.Button(
            ctrl,
            text="📂  MD laden",
            bg=C["bg_card"],
            fg=C["text_mid"],
            activebackground=C["bg_hover"],
            activeforeground=C["text_hi"],
            font=("Courier", 10),
            relief="flat",
            bd=0,
            padx=8, pady=4,
            command=self._browse_md,
        ).pack(side="right", padx=(0, 14))

    def _build_main_tk(self) -> None:
        main = tk.Frame(self.root, bg=C["bg_root"])
        main.pack(fill="both", expand=True, pady=(1, 0))

        # Results panel
        left = tk.Frame(main, bg=C["bg_panel"], width=340)
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

        tk.Label(bar, text="STARGATE  ·  Goa'uld Linguistic Interface  ·  v2.0",
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

        # Sync direction label
        if direction == "goa2de":
            dir_text  = "Goa'uld  →  Deutsch"
            in_label  = "Goa'uld"
            out_label = "Deutsch"
        else:
            dir_text  = "Deutsch  →  Goa'uld"
            in_label  = "Deutsch"
            out_label = "Goa'uld"

        self._trans_dir_lbl.configure(text=f"  {GLYPH_GATE}  {dir_text}")

        # Update input echo
        self._trans_input_echo.configure(
            text=text if text else f"—  Etwas in die Suchleiste eingeben ({in_label})",
            text_color=C["gold_bright"] if text else C["text_lo"],
        )

        if not text:
            for w in (self._trans_output, self._trans_breakdown):
                w.configure(state="normal")
                w.delete("0.0", "end")
                w.configure(state="disabled")
            self._trans_status_lbl.configure(text="")
            return

        analysis  = self._analyzer.analyze(text, direction=direction,
                                           lang_pref=lang_pref)
        found_n   = sum(1 for t in analysis if t["found"])
        total_n   = len(analysis)
        trans_str = self._analyzer.build_translation(analysis, direction=direction)

        # Translation output
        self._trans_output.configure(state="normal")
        self._trans_output.delete("0.0", "end")
        self._trans_output.insert("0.0", trans_str)
        self._trans_output.configure(state="disabled")

        # Status badge
        icon = GLYPH_LOCKED if found_n == total_n else GLYPH_CHEVRON
        self._trans_status_lbl.configure(
            text=f"{icon}  {found_n}/{total_n} Token",
            text_color=C["locked_bright"] if found_n == total_n else C["orange"],
        )

        # Token breakdown — label columns depend on direction
        if direction == "goa2de":
            col_a_hdr, col_b_hdr = "GOA'ULD", "BEDEUTUNG (DE)"
        else:
            col_a_hdr, col_b_hdr = "EINGABE", "GOA'ULD"

        lines: list[str] = [f"\n  {col_a_hdr:<22}  {col_b_hdr}\n"]
        sep = "─" * 48
        lines.append(f"  {sep}\n")

        for td in analysis:
            tok   = td["token"]
            found = td["found"]
            prim  = td["primary"]
            alts  = td["alternatives"]

            t_icon = GLYPH_LOCKED if found else GLYPH_KEK

            if found and prim:
                if direction == "de2goa":
                    # col_a = input word, col_b = Goa'uld result
                    result_word = prim["goauld"].split("/")[0].strip()
                    lines.append(f"  {t_icon}  {tok:<20}  {result_word}")
                    # Meaning context below
                    mea = re.split(r"[;—]", prim["meaning"])[0].strip()[:50]
                    lines.append(f"       {'':20}  ({mea})")
                else:
                    # col_a = Goa'uld input, col_b = German meaning
                    mea = re.split(r"[;—]", prim["meaning"])[0].strip()[:50]
                    # prefer DE
                    best = prim
                    for a in alts:
                        if a.get("lang") == "de" and prim.get("lang") != "de":
                            best = a
                            break
                    mea = re.split(r"[;—]", best["meaning"])[0].strip()[:50]
                    lines.append(f"  {t_icon}  {tok:<20}  {mea}")

                # Source
                src = prim.get("source", "")
                if src:
                    lines.append(f"       [{src}]")

                # Alternatives compact
                if alts:
                    for a in alts[:2]:
                        if direction == "de2goa":
                            a_out = a["goauld"].split("/")[0].strip()
                        else:
                            a_out = re.split(r"[;—]", a["meaning"])[0].strip()[:36]
                        lines.append(f"       {GLYPH_ARROW}  Alt: {a_out}")
            else:
                lines.append(f"  {GLYPH_KEK}  {tok:<20}  — nicht gefunden")
                sug = self._engine.search(tok, direction=direction,
                                          max_results=2, lang_pref=lang_pref)
                for s in sug:
                    if direction == "de2goa":
                        s_out = s["goauld"].split("/")[0].strip()
                    else:
                        s_out = re.split(r"[;—]", s["meaning"])[0].strip()[:36]
                    lines.append(f"       {GLYPH_CHEVRON}  Ähnlich: {s_out}")

            lines.append("")

        self._trans_breakdown.configure(state="normal")
        self._trans_breakdown.delete("0.0", "end")
        self._trans_breakdown.insert("0.0", "\n".join(lines))
        self._trans_breakdown.configure(state="disabled")

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

    def _on_direction_change(self, *_) -> None:
        if CTK_AVAILABLE:
            val = self._dir_var.get()
            self._direction = ("goa2de" if "Goa" in val else "de2goa")
        else:
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

        if self._analyzer.is_sentence(query):
            self._sentence_mode = True
            phrase_hit = self._engine.search(query, direction=self._direction,
                                             max_results=1, lang_pref=self._lang_pref)
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
        # Clear old rows
        for row in self._result_rows:
            row.destroy()
        self._result_rows.clear()

        if not results:
            msg = ctk.CTkLabel(
                self._result_scroll,
                text="  Kein Eintrag gefunden.\n  Tek'ma'te…",
                font=("Courier", 11),
                text_color=C["text_lo"],
                anchor="w",
                justify="left",
            )
            msg.grid(row=0, column=0, sticky="ew", padx=8, pady=20)
            self._result_rows.append(msg)
            self._update_status(len(results))
            return

        for idx, entry in enumerate(results):
            row = ctk.CTkFrame(
                self._result_scroll,
                fg_color=C["bg_card"],
                corner_radius=4,
            )
            row.grid(row=idx, column=0, sticky="ew", padx=4, pady=2)
            row.columnconfigure(0, weight=1)

            # Top line: Goa'uld term
            goauld_lbl = ctk.CTkLabel(
                row,
                text=f"  {GLYPH_BULLET}  {entry['goauld']}",
                font=("Courier", 12, "bold"),
                text_color=C["gold_bright"],
                anchor="w",
            )
            goauld_lbl.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 1))

            # Second line: meaning (truncated)
            meaning = entry["meaning"]
            if len(meaning) > 72:
                meaning = meaning[:69] + "…"
            meaning_lbl = ctk.CTkLabel(
                row,
                text=f"    {GLYPH_ARROW}  {meaning}",
                font=("Courier", 10),
                text_color=C["text_hi"],
                anchor="w",
                wraplength=320,
            )
            meaning_lbl.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 2))

            # Section tag
            tag_lbl = ctk.CTkLabel(
                row,
                text=f"    [{entry['section']}]",
                font=("Courier", 8),
                text_color=C["gold_dim"],
                anchor="w",
            )
            tag_lbl.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 5))

            # Click binding
            def _select(e, entry=entry, row=row):
                for r in self._result_rows:
                    if isinstance(r, ctk.CTkFrame):
                        r.configure(fg_color=C["bg_card"])
                row.configure(fg_color=C["bg_select"])
                self._show_detail(entry)

            for w in [row, goauld_lbl, meaning_lbl, tag_lbl]:
                w.bind("<Button-1>", _select)

            self._result_rows.append(row)

        self._update_status(len(results))

        # Auto-select first result
        if results:
            self._result_rows[0].configure(fg_color=C["bg_select"])
            self._show_detail(results[0])

    def _display_results_tk(self, results: list[dict]) -> None:
        self._listbox.delete(0, "end")
        self._tk_results = results
        if not results:
            self._listbox.insert("end", "  Kein Eintrag gefunden.  Tek'ma'te…")
            self._update_status(0)
            return
        for e in results:
            goa = e["goauld"][:30]
            mea = e["meaning"][:38]
            self._listbox.insert("end", f"  {goa:<32}  {mea}")
        self._update_status(len(results))
        self._listbox.selection_set(0)
        self._show_detail(results[0])

    def _display_sentence_ctk(self, analysis: list[dict], query: str,
                               phrase_hit: Optional[dict]) -> None:
        """CTK results panel in sentence mode."""
        for row in self._result_rows:
            row.destroy()
        self._result_rows.clear()

        translation = self._analyzer.build_translation(analysis, direction=self._direction)
        found_count = sum(1 for t in analysis if t["found"])
        total_count = len(analysis)

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
            icon_color = C["locked_bright"] if found else C["text_kek"]
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
        translation = self._analyzer.build_translation(analysis, direction=self._direction)
        found_count = sum(1 for t in analysis if t["found"])

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
        src = (f"MD-Datei: {Path(self._md_path).name}"
               if self._md_path else "Eingebettetes Fallback-Vokabular")
        welcome = (
            "\n"
            "╔══════════════════════════════════════════════╗\n"
            "║   GOA'ULD LINGUISTIC INTERFACE               ║\n"
            "║   SGC Xenolinguistics Division               ║\n"
            "╚══════════════════════════════════════════════╝\n\n"
            f"  Einträge geladen:  {total}\n"
            f"  Quelle:  {src}\n\n"
            "  ─────────────────────────────────────────────\n\n"
            "  Verwende das Suchfeld oben um Wörter oder\n"
            "  Phrasen zu suchen.\n\n"
            "  RICHTUNGEN:\n"
            "    Goa'uld → Deutsch/Englisch\n"
            "    Deutsch/Englisch → Goa'uld\n\n"
            "  TIPP: Fuzzy-Matching ist aktiviert — auch\n"
            "  Tippfehler führen zu Treffern.\n\n"
            "  ─────────────────────────────────────────────\n\n"
            '  "Jaffa, Kree!"  --  Achtung, Krieger!\n'
            '  "Shel kek nem ron."  --  Ich sterbe frei.\n'
            '  "Tek\'ma\'te."  --  Meister, gut getroffen.\n\n'
            "  ✦  Kree!  ✦\n"
        )
        self._write_detail(welcome)

    def _show_detail(self, entry: dict) -> None:
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

        # --- Build text ---
        lines = [
            "",
            f"  {GLYPH_LOCKED}  {entry['goauld']}",
            "",
            f"  {sep}",
            "",
            "  BEDEUTUNG",
            "",
        ]

        # Full meaning with line wrapping at 58 chars
        full_meaning = entry["meaning"]
        # Split on ; and — to show structured meaning
        meaning_parts = re.split(r"\s*([;—])\s*", full_meaning)
        if len(meaning_parts) == 1:
            lines.append(f"    {full_meaning}")
        else:
            first = True
            i = 0
            while i < len(meaning_parts):
                part = meaning_parts[i]
                sep_char = ""
                if i + 1 < len(meaning_parts) and meaning_parts[i + 1] in (";", "—"):
                    sep_char = meaning_parts[i + 1]
                    i += 2
                else:
                    i += 1
                if part.strip():
                    prefix = f"    {GLYPH_BULLET}  " if not first else "    "
                    lines.append(f"{prefix}{part.strip()}")
                    first = False

        lines.append("")

        # Section / Quelle
        lines += [f"  {sep}", ""]
        if entry.get("section"):
            lines.append(f"  SEKTION     {entry['section']}")
        if entry.get("source"):
            lines.append(f"  EPISODE     {entry['source']}")
        lines += ["", f"  {sep}", ""]

        # Grammar tips
        if tips:
            lines.append("  GRAMMATIK & LINGUISTIK")
            lines.append("")
            for t in tips:
                lines.append(t)
            lines += ["", f"  {sep}", ""]

        # Alternatives (other forms)
        if alternatives:
            lines.append("  VERWANDTE EINTRÄGE")
            lines.append("")
            for r in alternatives:
                goa = r["goauld"][:26]
                mea = re.split(r"[;—]", r["meaning"])[0].strip()[:40]
                sec = f"[{r['section'][:14]}]" if r.get("section") else ""
                lines.append(f"    {GLYPH_ARROW}  {goa:<28}  {mea}")
                if sec:
                    lines.append(f"       {sec}")
            lines += ["", f"  {sep_s}", ""]

        # Semantic relatives (same meaning domain)
        if semantic:
            lines.append("  SEMANTISCH VERWANDT")
            lines.append("")
            for r in semantic:
                goa = r["goauld"][:26]
                mea = re.split(r"[;—]", r["meaning"])[0].strip()[:38]
                lines.append(f"    {GLYPH_GATE}  {goa:<28}  {mea}")
            lines += ["", f"  {sep}", ""]

        lines.append(f"  {GLYPH_STAR}  Kree!  {GLYPH_STAR}")
        lines.append("")

        self._write_detail("\n".join(lines))

    def _show_sentence_detail(self, analysis: list[dict], query: str,
                               phrase_hit: Optional[dict]) -> None:
        """Vollständige Satzanalyse in der Detailansicht."""
        sep   = "═" * 52
        sep_s = "─" * 52
        translation = self._analyzer.build_translation(analysis, direction=self._direction)
        found_count = sum(1 for t in analysis if t["found"])
        total_count = len(analysis)

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
                    meta.append(f"Episode: {prim['source']}")
                if meta:
                    lines.append(f"    {'  ·  '.join(meta)}")
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
        if path:
            new_entries = parse_markdown_dictionary(path)
            if new_entries:
                self._md_path = path
                self._all_entries = new_entries + list(EMBEDDED_VOCAB)
                self._engine = SearchEngine(self._all_entries)
                self._analyzer = SentenceAnalyzer(self._engine)
                self._update_status()
                self._show_welcome_detail()
                self._do_search()
                print(f"[OK] Neue MD-Datei geladen: {path}  ({len(new_entries)} Einträge)")
            else:
                if TK_AVAILABLE:
                    messagebox.showwarning(
                        "Keine Einträge",
                        f"In der Datei wurden keine Goa'uld-Einträge gefunden:\n{path}",
                    )

    # ─── Hilfsfunktionen ─────────────────────────────────────────────────────

    def _update_status(self, result_count: Optional[int] = None,
                       mode: str = "search", total_tokens: int = 0) -> None:
        total = len(self._engine.entries)
        self._entry_count_var.set(f"Einträge:  {total}")
        dir_label = ("Goa'uld → Dt/En" if self._direction == "goa2de"
                     else "Dt/En → Goa'uld")

        if mode == "sentence":
            if result_count == total_tokens:
                msg = (f"  {GLYPH_LOCKED}  Alle {total_tokens} Token erkannt  ·  "
                       f"{total} Einträge  ·  {dir_label}")
            else:
                msg = (f"  {GLYPH_CHEVRON}  {result_count}/{total_tokens} Token erkannt  ·  "
                       f"{total} Einträge  ·  {dir_label}")
        elif result_count is None:
            msg = (f"  {GLYPH_GATE}  Bereit  ·  {total} Einträge geladen  ·  "
                   f"Richtung: {dir_label}")
        elif result_count == 0:
            msg = (f"  {GLYPH_KEK}  Kek!  —  Keine Treffer  ·  "
                   f"Richtung: {dir_label}")
        else:
            msg = (f"  {GLYPH_FOUND}  {result_count} Treffer  ·  "
                   f"Gesamt: {total} Einträge  ·  {dir_label}")
        self._status_var.set(msg)

    # ─── App starten ──────────────────────────────────────────────────────────

    def run(self) -> None:
        self.root.mainloop()


# ─────────────────────────────────────────────────────────────────────────────
# CLI MODUS  (Kompatibel mit dem Original-Script)
# ─────────────────────────────────────────────────────────────────────────────

def run_cli(args: argparse.Namespace) -> None:
    print("\n" + "=" * 62)
    print("   JAFFA, KREE!  —  Goa'uld Linguistic Interface  v2.0")
    print("=" * 62)

    # Lade Vokabular
    all_entries = list(EMBEDDED_VOCAB)
    md_path = find_md_file(getattr(args, "md", None))
    if md_path:
        md_entries = parse_markdown_dictionary(md_path)
        all_entries = md_entries + all_entries
        print(f"[OK] MD geladen: {md_path}  ({len(md_entries)} Einträge)")
    else:
        print("[INFO] Kein MD-Wörterbuch gefunden — nutze Fallback-Vokabular.")

    mapping = build_mapping(all_entries, args.dir)
    dir_name = "Goa'uld → Deutsch/Englisch" if args.dir == "goa2de" else "Deutsch/Englisch → Goa'uld"

    if args.text:
        result = translate_text(args.text, mapping)
        print(f"[{dir_name}]  {args.text}  →  {result}")
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
            result = translate_text(user_input, mapping)
            print(f"  →  {result}\n")
        except (KeyboardInterrupt, EOFError):
            print("\nTek'ma'te!")
            break


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stargate: Goa'uld Linguistic Interface v2.0",
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
    args = parser.parse_args()

    if args.cli:
        run_cli(args)
    else:
        if not TK_AVAILABLE:
            print("FEHLER: Tkinter ist nicht verfügbar. Bitte Python mit Tkinter-Unterstützung installieren.")
            print("       Im CLI-Modus läuft das Script ohne Tkinter:  --cli")
            sys.exit(1)
        if not CTK_AVAILABLE:
            print("[HINWEIS] CustomTkinter nicht gefunden — nutze Standard-Tkinter.")
            print("          Für das beste Erlebnis:  pip install customtkinter\n")
        app = GoauldApp(md_path=args.md)
        app.run()


if __name__ == "__main__":
    main()