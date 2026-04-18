# Stargate — Goa'uld Linguistic Interface ⬡
### Version 0.2.5

A bidirectional translator for the Goa'uld language from the Stargate franchise. This tool offers both an immersive graphical user interface (GUI) styled as an SGC command terminal and a Command-Line Interface (CLI).

The interface uses a combination of an embedded core vocabulary and up to four extensible Markdown dictionary files to analyze individual words and entire sentences.

---

## 🆕 What's new in v0.2.5

- **Parser fix for reversed sections** — Sections titled `Deutsch → Goa'uld: Direktzuordnung (Neologikum)` and `English → Goa'uld: Direct lookup` are now correctly recognized as reversed-column tables. Previously, over 1,200 entries from the Neologikum and Fictionary were loaded with swapped fields, which corrupted lookups (e.g. `tap'tar → menschheit` instead of `menschheit → tap'tar`). A robust regex replaces the previous rigid exact-match.

- **Complete UI redesign: Level 28 / SGC command terminal** — The interface has been militarized:
  - Persistent **`TOP SECRET // SCI // STARGATE COMMAND`** classification bar at the very top
  - Expanded header with **Operator ID**, **Stardate/Zulu timestamp**, and **lexicon counter**
  - Expanded subtitle: *SGC Xenolinguistics Div · SG-1 Ops · Facility: Cheyenne Mountain*
  - Tabs renamed: **`◈ BRIEFING`** (formerly Detail) and **`⊕ DEBRIEF`** (formerly Satzanalyse)
  - Results panel is now **`⊕ INTERCEPT FEED`** with hit counter
  - Live translation is now **`⚡ LIVE-TRANSMISSION · OUTGOING`** with Signal-Locked indicator
  - **DEFCON 3** status bar at the bottom with version badge

- **Bugfix: truncated columns in the results list** — The old card-based layout with hardcoded `wraplength` values cut off words whenever the left panel fell below 400px. Replaced with a clean 4-column grid (Nr / Goa'uld / Meaning / Score) with a colored left accent strip (phosphor green for ≥90 % score, gold for ≥60 %, gray below).

- **Fallback for "Mensch"** — The gap-fill vocabulary now includes `mensch → tau'ri` (SG1 canonical) as a low-priority fallback when the main dictionary has no entry.

---

## ✨ Features

- **Bidirectional Translation** — Translates fluently from Goa'uld to English/German and vice versa. Direction and language can be toggled at any time.

- **Intelligent Sentence Analysis** — Analyzes entire sentences token by token, showing primary meanings, alternatives, and linguistic tips in the `⊕ DEBRIEF` tab.

- **Live Transmission** — A real-time translation view (`⚡ LIVE-TRANSMISSION`) reads from the main search bar with debounced updates — no dialog popups required.

- **Briefing View** — The `◈ BRIEFING` tab displays structured meaning parts, grammar tips, semantic relatives, and source-cited alternatives for any selected entry.

- **Fuzzy-Search Engine** — Finds entries through exact matching, prefix matching, and fuzzy matching — even typos lead to the right term. Includes language-preference scoring, source prioritization, and dynamic fuzzy thresholds for short words.

- **SGC Command Terminal GUI** — Immersive interface based on `customtkinter` with a *Dark / Gold / Blue / Orange* palette, classification bar, pulsing chevron indicators, event-horizon glyphs, and resizable panels via a gate-blue sash divider. A fallback to standard `tkinter` is integrated.

- **Terminal / CLI Mode** — For quick translations directly in your console using the `--cli` flag.

- **Markdown Auto-Parsing** — Automatically reads vocabulary from tables within Markdown files. Supports both direct `Goa'uld → English/German` tables and reversed `Deutsch → Goa'uld: Direktzuordnung` sections, including variants with suffixes (`(Neologikum)`, `(Fictionary)`, etc.).

- **Auto-Installer** — Automatically attempts to install `customtkinter` in the background if it is missing, with `ensurepip` fallback guidance.

- **DE_MAP Priority** — For German→Goa'uld translation (`de2goa`), the direct German dictionary (DE_MAP) always takes priority over the fuzzy engine, ensuring accurate phrase-based translations.

- **Multi-Word Phrase Engine Search** — The engine now also searches for multi-word phrases, not just DE_MAP, improving coverage for complex German expressions.

- **Source Prioritization** — The engine deduplicates entries by source: main dictionaries (priority 3) outrank Fictionary/Neologikum (priority 2) outrank gap-fill (priority 0). Secondary sources also receive a −15 score penalty.

- **Optimized Scoring** — Direction-aware bonuses: German→Goa'uld searches receive priority for exact/prefix matches. Short words (≤6 chars) get a higher fuzzy threshold to prevent random matches.

- **Enhanced Stemming** — German lemma detection with verb conjugation (1st/2nd/3rd person singular → infinitive), noun plurals, genitive → nominative, superlative/comparative → positive, contractions (`im → in dem`, `zum → zu dem`, `ans → an das`, `beim → bei dem`), umlaut variants (ä↔a, ö↔o, ü↔u, ß↔ss), and compound bridges (`-heit`, `-keit`, `-ung`, `-lich`, `-isch`).

---

## 🚀 Installation

Make sure you have **Python 3** installed on your system.

Clone the repository and install the required library for the modern GUI:

```bash
git clone https://github.com/DaWasteh/goauld-translator.git
cd goauld-translator
pip install customtkinter
```

> **Note:** The script will attempt an automatic background installation if it detects that `customtkinter` is missing.

---

## 💻 Usage

### GUI Mode (Graphical Interface)

Simply start the application without any parameters to open the GUI:

```bash
python goauld_translator.py
```

To load a specific Markdown dictionary file directly:

```bash
python goauld_translator.py --md path/to/file.md
```

### CLI Mode (Command Line)

Use the `--cli` flag for efficient terminal use. Translate a string directly or enter interactive mode:

```bash
# Interactive Mode (Goa'uld to English/German)
python goauld_translator.py --cli --dir goa2de

# Direct translation of a specific sentence
python goauld_translator.py --cli --dir goa2de --text "Jaffa kree"
```

---

## 📦 Pack as .EXE (Windows)

Distribute the script as a standalone Windows application using `pyinstaller`:

```powershell
pip install pyinstaller
pyinstaller --noconsole --onefile `
  --add-data "Goa'uld-Dictionary.md;." `
  --add-data "Goa'uld-Wörterbuch.md;." `
  --add-data "Goa'uld-Fictionary.md;." `
  --add-data "Goa'uld-Neologikum.md;." `
  goauld_translator.py
```

The finished `.exe` will be located inside the newly created `dist` folder.

> **PowerShell note:** Line continuation uses backtick (`` ` ``), not caret (`^`). Adjust accordingly for Bash/CMD.

---

## 📚 Vocabulary & Data

This project ships with four Markdown dictionary files and an embedded gap-fill vocabulary covering commonly used terms. The dictionaries are automatically parsed at startup and merged into a unified lexicon of **~3,244 deduplicated entries** (3,463 raw).

### Official Dictionaries

These two dictionaries document the canonical vocabulary attested across the Stargate film, ten seasons of SG-1, *The Ultimate Visual Guide*, the SG-1 Roleplaying Game, the *Unleashed* mobile game, and fan community analyses. Each contains approximately **230 documented entries** plus around **272 German→Goa'uld direct mappings**.

| File | Language | Description |
|------|----------|-------------|
| `Goa_uld-Dictionary.md` | English | Complete canonical Goa'uld vocabulary with etymologies, grammar notes, and episode sources |
| `Goa_uld-Wörterbuch.md` | German | German-language counterpart of the canonical dictionary |

> **Created by:** Claude Opus 4.6 Extended Research

---

### Fictional Dictionaries (Constructed Extensions)

These two dictionaries systematically extend the canonical vocabulary into areas the show left undocumented — body parts, numbers, emotions, colors, technology, and abstract reasoning — using only attested canonical roots and documented morphological rules (Swadesh framework, compound logic, vowel shifting, Unas inheritance). Each contains approximately **1,000–1,500 entries** plus **800+ direct mappings**.

| File | Language | Description |
|------|----------|-------------|
| `Goa_uld-Fictionary.md` | English | Swadesh foundation, semantic extensions, and modern concepts |
| `Goa_uld-Neologikum.md` | German | German-language neologisms for modern and abstract vocabulary |

> **Created by:** Collaborative effort between **Google Gemini 3.1 Pro Deep Research** and **Claude Opus 4.6 Extended Research**

---

## 🤝 Contributing

**Kree!** Want to expand the dictionary or improve the code? Pull requests are always welcome.

- Add new vocabulary as a new table row in any Markdown file — the parser handles the rest.
- For reverse mappings (German → Goa'uld), use a section with title `Deutsch → Goa'uld: Direktzuordnung` (or variants with suffixes).
- Entries can carry language tags (`lang: "de"` / `lang: "en"`) for improved search scoring.
- The fictional dictionaries follow strict canonical morphological rules — please maintain consistency with attested roots.

**Tek'ma'te.**