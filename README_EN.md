# Stargate — Goa'uld Linguistic Interface ⬡
### Version 0.2

A bidirectional translator for the Goa'uld language from the Stargate franchise. This tool offers both a modern graphical user interface (GUI) in an SGC terminal design and a Command-Line Interface (CLI).

The interface uses a combination of an embedded core vocabulary and up to four extensible Markdown dictionary files to analyze individual words and entire sentences.

---

## ✨ Features

- **Bidirectional Translation** — Translates fluently from Goa'uld to English/German and vice versa. Direction and language can be toggled at any time.

- **Intelligent Sentence Analysis** — Analyzes entire sentences token by token, showing primary meanings, alternatives, and linguistic tips in the dedicated *⊕ Satzanalyse* tab.

- **Live Translator Tab** — A real-time translation view (*⚡ Übersetzer*) reads from the main search bar with debounced updates — no dialog popups required.

- **Detail View** — The *◈ Detail* tab displays structured meaning parts, grammar tips, semantic relatives, and source-cited alternatives for any selected entry.

- **Fuzzy-Search Engine** — Finds entries through exact matching, prefix matching, and fuzzy matching — even typos lead to the right term. Includes language-preference scoring for German/English entries.

- **SGC-Design GUI** — An immersive interface based on `customtkinter` featuring the *Dark / Gold / Orange* look of Stargate Command, with resizable panels via a gate-blue sash divider. A fallback to standard `tkinter` is integrated.

- **Terminal / CLI Mode** — For quick translations directly in your console using the `--cli` flag.

- **Markdown Auto-Parsing** — Automatically reads vocabulary from tables within Markdown files. The four included dictionaries cover the full canonical and extended vocabulary.

- **Auto-Installer** — Automatically attempts to install `customtkinter` in the background if it is missing, with `ensurepip` fallback guidance.

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

```bash
pip install pyinstaller
pyinstaller --onefile goauld_translator.py
```

The finished `.exe` will be located inside the newly created `dist` folder.

---

## 📚 Vocabulary & Data

This project ships with four Markdown dictionary files and an embedded fallback vocabulary covering the most essential terms. The dictionaries are automatically parsed at startup.

### Official Dictionaries

These two dictionaries document the canonical vocabulary attested across the Stargate film, ten seasons of SG-1, *The Ultimate Visual Guide*, the SG-1 Roleplaying Game, the *Unleashed* mobile game, and fan community analyses. Each contains approximately **250 documented entries**.

| File | Language | Description |
|------|----------|-------------|
| `Goa_uld-Dictionary.md` | English | Complete canonical Goa'uld vocabulary with etymologies, grammar notes, and episode sources |
| `Goa_uld-Wörterbuch.md` | German | German-language counterpart of the canonical dictionary |

> **Created by:** Claude Opus 4.6 Extended Research

---

### Fictional Dictionaries (Constructed Extensions)

These two dictionaries systematically extend the canonical vocabulary into areas the show left undocumented — body parts, numbers, emotions, colors, technology, and abstract reasoning — using only attested canonical roots and documented morphological rules (Swadesh framework, compound logic, vowel shifting, Unas inheritance).

| File | Language | Description |
|------|----------|-------------|
| `Goa_uld-Fictionary.md` | English | Swadesh foundation, semantic extensions, and modern concepts |
| `Goa_uld-Neologikum.md` | German | German-language neologisms for modern and abstract vocabulary |

> **Created by:** Collaborative effort between **Google Gemini 2.0 Pro Deep Research** and **Claude Opus 4.6 Extended Research**

---

## 🤝 Contributing

**Kree!** Want to expand the dictionary or improve the code? Pull requests are always welcome.

- Add new vocabulary as a new table row in any Markdown file — the parser handles the rest.
- Entries can carry language tags (`lang: "de"` / `lang: "en"`) for improved search scoring.
- The fictional dictionaries follow strict canonical morphological rules — please maintain consistency with attested roots.