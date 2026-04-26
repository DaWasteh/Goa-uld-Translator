# Stargate — Goa'uld Linguistic Interface ⬡
### Version 0.2.8

A bidirectional translator for the Goa'uld language from the Stargate franchise. This tool offers both an immersive graphical user interface (GUI) styled as an SGC command terminal and a Command-Line Interface (CLI).

The interface combines a structured YAML lexicon, four extensible Markdown dictionary files, and an embedded core vocabulary to analyze individual words and entire sentences.

---

## 🆕 What's new in v0.2.6

- **YAML lexicon as the primary data format** — The new `goauld_lexicon.yaml` consolidates all four dictionaries into a single structured source with **~5,850 entries**, priority tiers (`canon_series` → `fanon_derived`), per-sense `glosses.de/en` fields, and explicit source attribution. The four Markdown files remain as a full **fallback** — if the YAML is missing, the legacy MD loader kicks in automatically and the tool runs without any loss of functionality.

- **"Also:" alternatives for polysemous terms** — When a German or English word maps to multiple Goa'uld translations (e.g. `warrior → Jaffa` with the alternative `mel'shak'tar`), the canonical choice is shown as the primary hit and any additional variants appear in a compact **`auch:`** line directly below it. The sentence analysis tab (`⊕ DEBRIEF`) now shows a dedicated **`AUCH`** block per token with up to five alternatives.

- **Bilingual UI** — The direction buttons now consistently read **`DE/EN → Goa'uld`** and **`Goa'uld → DE/EN`** (previously just `DE`). The status bar and input placeholder have been aligned accordingly. The language toggle (🇩🇪 DE / 🇬🇧 EN) now decides which secondary map is consulted first for polysemous terms — with automatic fallback to the other language for loan words.

- **Robustness in `.exe` bundles** — YAML and `yaml_loader.py` are now reliably loaded from `sys._MEIPASS` (PyInstaller `--onefile` extraction directory) **and** the directory next to the `.exe`. This supports both embedded deployment and an externally swappable YAML file without needing to rebuild.

- **Bugfixes** —
  - **Direction toggle** was never correctly matching its second label due to fragile whitespace-sensitive substring checks (masked by the hardcoded initial state); now handled via a robust arrow-split.
  - **Indentation bug in `_browse_md`** broke the `GoauldApp` class as seen by the parser (cascading into 38+ Pylance errors) — fixed.
  - **`log.warning()` before logger initialization** raised `NameError` if the YAML loader failed to import — now deferred until after `_setup_logging()`.
  - **`tk.messagebox`** crashed in the GUI error fallback due to a missing explicit submodule import — fixed via `from tkinter import messagebox`.
  - **`--cli` mode inside a `--noconsole` EXE** crashed on `print` because `sys.stdout is None` — guarded at the start of `run_cli()`.
  - **Type annotations** tightened for Optional variables (now mypy-clean).

---

## ✨ Features

- **Bidirectional Translation** — Translates fluently from Goa'uld to English/German and vice versa. Direction and language can be toggled at any time.

- **Intelligent Sentence Analysis** — Analyzes entire sentences token by token, showing primary meanings, alternatives, polysemous `auch:` variants, and linguistic tips in the `⊕ DEBRIEF` tab.

- **Live Transmission** — A real-time translation view (`⚡ LIVE-TRANSMISSION`) reads from the main search bar with debounced updates — no dialog popups required.

- **Briefing View** — The `◈ BRIEFING` tab displays structured meaning parts, grammar tips, semantic relatives, and source-cited alternatives for any selected entry.

- **Fuzzy-Search Engine** — Finds entries through exact matching, prefix matching, and fuzzy matching — even typos lead to the right term. Includes language-preference scoring, source prioritization, and dynamic fuzzy thresholds for short words.

- **SGC Command Terminal GUI** — Immersive interface based on `customtkinter` with a *Dark / Gold / Blue / Orange* palette, classification bar, pulsing chevron indicators, event-horizon glyphs, and resizable panels via a gate-blue sash divider. A fallback to standard `tkinter` is integrated.

- **Terminal / CLI Mode** — For quick translations directly in your console using the `--cli` flag.

- **YAML Lexicon with Tier System** — Canonical sources (`canon_series`, `canon_film`) outrank fanon extensions, so polysemous terms get a canonically grounded primary choice while every additional variant is surfaced as `secondary`.

- **Markdown Auto-Parsing as fallback** — Automatically reads vocabulary from tables within Markdown files. Supports both direct `Goa'uld → English/German` tables and reversed `Deutsch → Goa'uld: Direktzuordnung` sections, including variants with suffixes (`(Neologikum)`, `(Fictionary)`, etc.).

- **Auto-Installer** — Automatically attempts to install `customtkinter` in the background if it is missing, with `ensurepip` fallback guidance.

- **DE_MAP Priority** — For German→Goa'uld translation (`de2goa`), the direct German dictionary (DE_MAP) always takes priority over the fuzzy engine, ensuring accurate phrase-based translations.

- **Multi-Word Phrase Engine Search** — The engine now also searches for multi-word phrases, not just DE_MAP, improving coverage for complex German expressions.

- **Source Prioritization** — The engine deduplicates entries by source: main dictionaries (priority 3) outrank Fictionary/Neologikum (priority 2) outrank gap-fill (priority 0). Secondary sources also receive a −15 score penalty.

- **Optimized Scoring** — Direction-aware bonuses: German→Goa'uld searches receive priority for exact/prefix matches. Short words (≤6 chars) get a higher fuzzy threshold to prevent random matches.

- **Enhanced Stemming** — German lemma detection with verb conjugation (1st/2nd/3rd person singular → infinitive), noun plurals, genitive → nominative, superlative/comparative → positive, contractions (`im → in dem`, `zum → zu dem`, `ans → an das`, `beim → bei dem`), umlaut variants (ä↔a, ö↔o, ü↔u, ß↔ss), and compound bridges (`-heit`, `-keit`, `-ung`, `-lich`, `-isch`).

---

## 🚀 Installation

Make sure you have **Python 3** installed on your system.

Clone the repository and install the required libraries:

```bash
git clone https://github.com/DaWasteh/goauld-translator.git
cd goauld-translator
pip install customtkinter pyyaml
```

> **Note:** The script will attempt an automatic background installation if it detects that `customtkinter` is missing. If `pyyaml` is missing, the tool falls back to the Markdown loader automatically, with a corresponding warning in the log.

---

## 💻 Usage

### GUI Mode (Graphical Interface)

Simply start the application without any parameters to open the GUI:

```bash
python goauld_translator.py
```

To load a specific Markdown dictionary file directly (forces MD mode, skipping YAML):

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
pip install pyinstaller pyyaml
pyinstaller --noconsole --onefile `
  --add-data "Goauld-Dictionary.md;." `
  --add-data "Goauld-Woerterbuch.md;." `
  --add-data "Goauld-Fictionary.md;." `
  --add-data "Goauld-Neologikum.md;." `
  --add-data "goauld_lexicon.yaml;." `
  --add-data "yaml_loader.py;." `
  --hidden-import yaml `
  goauld_translator.py
```

The finished `.exe` will be located inside the newly created `dist` folder.

> **PowerShell note:** Line continuation uses backtick (`` ` ``), not caret (`^`). Adjust accordingly for Bash/CMD.

> **If you hit a `PermissionError` during the build:** Make sure no old `goauld_translator.exe` is still running in the Task Manager, and that no Explorer window has the `dist` folder open. Running `Remove-Item -Recurse -Force .\build, .\dist` first clears any leftovers from previous builds.

> **Swappable YAML:** The tool looks for `goauld_lexicon.yaml` both inside the `_MEIPASS` bundle **and** next to the `.exe`. This lets you ship an updated YAML without rebuilding the EXE — just drop the new file into the same directory.

---

## 📚 Vocabulary & Data

This project ships with a structured YAML lexicon alongside four Markdown dictionary files. On startup, `goauld_lexicon.yaml` is loaded preferentially (**~5,850 entries** with priority tiers and bilingual glosses); if the YAML is missing, the fallback loader parses all four Markdown files into a unified lexicon (**~3,463 entries, 3,244 after deduplication**).

### Official Dictionaries

These two dictionaries document the canonical vocabulary attested across the Stargate film, ten seasons of SG-1, *The Ultimate Visual Guide*, the SG-1 Roleplaying Game, the *Unleashed* mobile game, and fan community analyses. Each contains approximately **230 documented entries** plus around **272 German→Goa'uld direct mappings**.

| File | Language | Description |
|------|----------|-------------|
| `Goauld-Dictionary.md` | English | Complete canonical Goa'uld vocabulary with etymologies, grammar notes, and episode sources |
| `Goauld-Woerterbuch.md` | German | German-language counterpart of the canonical dictionary |

> **Created by:** Claude Opus 4.6 Extended Research

---

### Fictional Dictionaries (Constructed Extensions)

These two dictionaries systematically extend the canonical vocabulary into areas the show left undocumented — body parts, numbers, emotions, colors, technology, and abstract reasoning — using only attested canonical roots and documented morphological rules (Swadesh framework, compound logic, vowel shifting, Unas inheritance). Each contains approximately **1,000–1,500 entries** plus **800+ direct mappings**.

| File | Language | Description |
|------|----------|-------------|
| `Goauld-Fictionary.md` | English | Swadesh foundation, semantic extensions, and modern concepts |
| `Goauld-Neologikum.md` | German | German-language neologisms for modern and abstract vocabulary |

> **Created by:** Collaborative effort between **Google Gemini 3.1 Pro Deep Research** and **Claude Opus 4.6 Extended Research**

---

### Consolidated YAML Lexicon

`goauld_lexicon.yaml` is the merged distillation of all four Markdown dictionaries with additional per-sense metadata:

- **Tier system** (`canon_series`, `canon_film`, `canon_guide`, `canon_rpg`, `abydonian`, `fanon_strict`, `fanon_derived`, …) as an authority signal
- **Priorities** for tiebreakers among polysemous terms (canonical choice wins primary)
- **`glosses.de` / `glosses.en`** per sense for clean bilingual lookup
- **~163 DE and ~132 EN secondary entries** powering the new `auch:` display

---

## 🤝 Contributing

**Kree!** Want to expand the dictionary or improve the code? Pull requests are always welcome.

- Add new vocabulary as a new table row in any Markdown file — the parser handles the rest.
- For reverse mappings (German → Goa'uld), use a section with title `Deutsch → Goa'uld: Direktzuordnung` (or variants with suffixes).
- Entries can carry language tags (`lang: "de"` / `lang: "en"`) for improved search scoring.
- The fictional dictionaries follow strict canonical morphological rules — please maintain consistency with attested roots.
- For structured YAML contributions: add new entries to `goauld_lexicon.yaml` with appropriate `tier` and `priority`; `yaml_loader.py` handles expansion.

**Tek'ma'te.**