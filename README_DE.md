# Stargate — Goa'uld Linguistic Interface ⬡
### Version 0.2

Ein bidirektionaler Übersetzer für die Goa'uld-Sprache aus dem Stargate-Franchise. Dieses Tool bietet sowohl eine moderne grafische Benutzeroberfläche (GUI) im SGC-Terminal-Design als auch ein Command-Line Interface (CLI).

Das Interface nutzt eine Kombination aus einem eingebetteten Kernvokabular und bis zu vier erweiterbaren Markdown-Wörterbuchdateien, um einzelne Wörter und ganze Sätze zu analysieren.

---

## ✨ Features

- **Bidirektionale Übersetzung** — Übersetzt fließend von Goa'uld nach Deutsch/Englisch und umgekehrt. Richtung und Zielsprache lassen sich jederzeit umschalten.

- **Intelligente Satzanalyse** — Analysiert ganze Sätze Token für Token und zeigt primäre Bedeutungen, Alternativen und linguistische Tipps im eigenen Tab *⊕ Satzanalyse* an.

- **Live-Übersetzer-Tab** — Eine Echtzeit-Übersetzungsansicht (*⚡ Übersetzer*) liest direkt aus der Hauptsuchleiste mit verzögerter Aktualisierung — ganz ohne Dialog-Popups.

- **Detailansicht** — Der Tab *◈ Detail* zeigt strukturierte Bedeutungsabschnitte, Grammatikhinweise, semantische Verwandte und quellenbasierte Alternativen für jeden ausgewählten Eintrag.

- **Fuzzy-Search Engine** — Findet Einträge durch exaktes Matching, Präfix-Matching und Fuzzy-Matching — auch Tippfehler führen zum richtigen Begriff. Enthält Sprachpräferenz-Scoring für Deutsch/Englisch-Einträge.

- **SGC-Design GUI** — Eine immersive Oberfläche basierend auf `customtkinter` im *Dark / Gold / Orange*-Look des Stargate Commands, mit verschiebbaren Panels über einen Tor-blauen Sash-Divider. Ein Fallback auf Standard-`tkinter` ist integriert.

- **Terminal / CLI-Modus** — Für schnelle Übersetzungen direkt in der Konsole über das `--cli`-Flag.

- **Markdown Auto-Parsing** — Liest Vokabeln automatisch aus Tabellen in Markdown-Dateien ein. Die vier mitgelieferten Wörterbücher decken das gesamte kanonische und erweiterte Vokabular ab.

- **Auto-Installer** — Versucht bei fehlendem `customtkinter` automatisch eine Hintergrundinstallation mit `ensurepip`-Fallback-Hinweis.

---

## 🚀 Installation

Stelle sicher, dass **Python 3** auf deinem System installiert ist.

Klone das Repository und installiere die benötigte Bibliothek für die moderne GUI:

```bash
git clone https://github.com/DaWasteh/goauld-translator.git
cd goauld-translator
pip install customtkinter
```

> **Hinweis:** Das Skript versucht bei fehlendem `customtkinter` eine automatische Installation im Hintergrund durchzuführen.

---

## 💻 Verwendung

### GUI-Modus (Grafische Oberfläche)

Starte die Anwendung einfach ohne Parameter, um die GUI zu öffnen:

```bash
python goauld_translator.py
```

Um direkt eine spezifische Markdown-Wörterbuchdatei zu laden:

```bash
python goauld_translator.py --md pfad/zur/datei.md
```

### CLI-Modus (Kommandozeile)

Verwende das `--cli`-Flag für ressourcenschonende Nutzung im Terminal. Du kannst direkt einen Text übergeben oder in den interaktiven Modus wechseln:

```bash
# Interaktiver Modus (Goa'uld nach Deutsch)
python goauld_translator.py --cli --dir goa2de

# Direkte Übersetzung eines Satzes
python goauld_translator.py --cli --dir goa2de --text "Jaffa kree"
```

---

## 📦 Als .EXE verpacken (Windows)

Wenn du das Skript als eigenständige Windows-Anwendung weitergeben willst, kompiliere es mit `pyinstaller`:

```bash
pip install pyinstaller
pyinstaller --onefile goauld_translator.py
```

Die fertige `.exe` findest du im neu erstellten `dist`-Ordner.

---

## 📚 Vokabular & Daten

Dieses Projekt liefert vier Markdown-Wörterbuchdateien sowie ein eingebettetes Fallback-Vokabular mit den wichtigsten Begriffen mit. Die Wörterbücher werden beim Start automatisch eingelesen.

### Offizielle Wörterbücher

Diese beiden Wörterbücher dokumentieren das kanonische Vokabular aus dem Stargate-Kinofilm, zehn Staffeln SG-1, *The Ultimate Visual Guide*, dem SG-1-Rollenspiel, dem Mobilspiel *Unleashed* sowie Fan-Community-Analysen. Jedes enthält rund **250 dokumentierte Einträge**.

| Datei | Sprache | Beschreibung |
|-------|---------|--------------|
| `Goa_uld-Dictionary.md` | Englisch | Vollständiges kanonisches Goa'uld-Vokabular mit Etymologien, Grammatikhinweisen und Episodenquellen |
| `Goa_uld-Wörterbuch.md` | Deutsch | Deutschsprachiges Pendant zum kanonischen Wörterbuch |

> **Erstellt von:** Claude Opus 4.6 Erweitert Recherche

---

### Fiktive Wörterbücher (Konstruierte Erweiterungen)

Diese beiden Wörterbücher erweitern das kanonische Vokabular systematisch in Bereiche, die die Serie undokumentiert ließ — Körperteile, Zahlen, Emotionen, Farben, Technologie und abstraktes Denken — ausschließlich auf Basis belegter kanonischer Wurzeln und dokumentierter Morphologieregeln (Swadesh-Rahmen, Kompositionslogik, Vokalverschiebung, Unas-Erbwörter).

| Datei | Sprache | Beschreibung |
|-------|---------|--------------|
| `Goa_uld-Fictionary.md` | Englisch | Swadesh-Grundlage, semantische Erweiterungen und moderne Konzepte |
| `Goa_uld-Neologikum.md` | Deutsch | Deutschsprachige Neologismen für moderne und abstrakte Begriffe |

> **Erstellt durch:** Gemeinschaftsarbeit von **Google Gemini 2.0 Pro Deep Research** und **Claude Opus 4.6 Erweitert Recherche**

---

## 🤝 Mitwirken

**Kree!** Du möchtest das Wörterbuch erweitern oder den Code verbessern? Pull Requests sind jederzeit willkommen.

- Neue Vokabeln einfach als Tabellenzeile in eine der Markdown-Dateien einfügen — der Parser erledigt den Rest.
- Einträge können Sprach-Tags tragen (`lang: "de"` / `lang: "en"`) für verbessertes Such-Scoring.
- Die fiktiven Wörterbücher folgen strengen kanonischen Morphologieregeln — bitte die Konsistenz mit belegten Wurzeln wahren.