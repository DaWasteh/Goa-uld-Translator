# Stargate — Goa'uld Linguistic Interface ⬡
### Version 0.2.5

Ein bidirektionaler Übersetzer für die Goa'uld-Sprache aus dem Stargate-Franchise. Dieses Tool bietet sowohl eine immersive grafische Benutzeroberfläche (GUI) im Stil eines SGC-Kommandoterminals als auch ein Command-Line Interface (CLI).

Das Interface nutzt eine Kombination aus einem eingebetteten Kernvokabular und bis zu vier erweiterbaren Markdown-Wörterbuchdateien, um einzelne Wörter und ganze Sätze zu analysieren.

---

## 🆕 Neu in v0.2.5

- **Parser-Fix für reversed Sections** — Die Sektionen `Deutsch → Goa'uld: Direktzuordnung (Neologikum)` und `English → Goa'uld: Direct lookup` werden jetzt korrekt als umgekehrte Spalten erkannt. Vorher wurden über 1.200 Einträge des Neologikums und Fictionarys mit vertauschten Feldern eingelesen, was die Suche verfälschte (z. B. `tap'tar → menschheit` statt `menschheit → tap'tar`). Robuste Regex-Erkennung ersetzt den starren Exact-Match.

- **Komplettes UI-Redesign: Level 28 / SGC-Kommandoterminal** — Die Oberfläche wurde militärisch überarbeitet:
  - Dauerhafte **`TOP SECRET // SCI // STARGATE COMMAND`** Classification Bar ganz oben
  - Erweiterter Header mit **Operator-ID**, **Stardate/Zulu-Zeit** und **Lexikon-Zähler**
  - Erweiterter Untertitel: *SGC Xenolinguistics Div · SG-1 Ops · Facility: Cheyenne Mountain*
  - Tabs umbenannt: **`◈ BRIEFING`** (ehem. Detail) und **`⊕ DEBRIEF`** (ehem. Satzanalyse)
  - Ergebnisliste heißt jetzt **`⊕ INTERCEPT FEED`** mit Hit-Counter
  - Live-Übersetzung heißt jetzt **`⚡ LIVE-TRANSMISSION · OUTGOING`** mit Signal-Locked-Indikator
  - **DEFCON 3** Statusleiste unten mit Versions-Badge

- **Bugfix: Spalten-Abschneidung in der Ergebnisliste** — Das alte Card-Layout mit hartkodierten `wraplength`-Werten schnitt Wörter ab, sobald das linke Panel schmaler als 400px wurde. Ersetzt durch ein sauberes 4-Spalten-Grid (Nr / Goa'uld / Bedeutung / Score) mit farbigem Akzentstreifen links (Phosphor-Grün bei ≥90 % Score, Gold bei ≥60 %, Grau darunter).

- **Fallback für "Mensch"** — Das Gap-Fill-Vokabular enthält jetzt `mensch → tau'ri` (SG1-Kanon) als niedrigpriorisierten Fallback, falls das Wörterbuch keinen Eintrag liefert.

---

## ✨ Features

- **Bidirektionale Übersetzung** — Übersetzt fließend von Goa'uld nach Deutsch/Englisch und umgekehrt. Richtung und Zielsprache lassen sich jederzeit umschalten.

- **Intelligente Satzanalyse** — Analysiert ganze Sätze Token für Token und zeigt primäre Bedeutungen, Alternativen und linguistische Tipps im Tab `⊕ DEBRIEF` an.

- **Live-Transmission** — Eine Echtzeit-Übersetzungsansicht (`⚡ LIVE-TRANSMISSION`) liest direkt aus der Hauptsuchleiste mit verzögerter Aktualisierung — ganz ohne Dialog-Popups.

- **Briefing-Ansicht** — Der Tab `◈ BRIEFING` zeigt strukturierte Bedeutungsabschnitte, Grammatikhinweise, semantische Verwandte und quellenbasierte Alternativen für jeden ausgewählten Eintrag.

- **Fuzzy-Search Engine** — Findet Einträge durch exaktes Matching, Präfix-Matching und Fuzzy-Matching — auch Tippfehler führen zum richtigen Begriff. Enthält Sprachpräferenz-Scoring, Quellen-Priorisierung und dynamische Fuzzy-Schwellen für kurze Wörter.

- **SGC-Kommandoterminal GUI** — Immersive Oberfläche auf Basis von `customtkinter` mit *Dark / Gold / Blue / Orange*-Palette, Classification Bar, pulsierenden Chevron-Anzeigen, Event-Horizon-Glyphen und verschiebbaren Panels über einen Tor-blauen Sash-Divider. Ein Fallback auf Standard-`tkinter` ist integriert.

- **Terminal / CLI-Modus** — Für schnelle Übersetzungen direkt in der Konsole über das `--cli`-Flag.

- **Markdown Auto-Parsing** — Liest Vokabeln automatisch aus Tabellen in Markdown-Dateien ein. Unterstützt sowohl direkte `Goa'uld → Deutsch`-Tabellen als auch umgekehrte `Deutsch → Goa'uld: Direktzuordnung`-Sektionen inklusive Varianten mit Suffix (`(Neologikum)`, `(Fictionary)` etc.).

- **Auto-Installer** — Versucht bei fehlendem `customtkinter` automatisch eine Hintergrundinstallation mit `ensurepip`-Fallback-Hinweis.

- **DE_MAP-Priorität** — Bei der Übersetzung von Deutsch nach Goa'uld (`de2goa`) hat das direkte Wörterbuch (DE_MAP) stets Vorrang vor der Fuzzy-Search-Engine.

- **Multi-Wort-Phrasen in der Engine** — Die Engine sucht nun auch nach Multi-Wort-Phrasen, nicht nur DE_MAP — das verbessert die Trefferquote für Satzfragmente und längere Ausdrücke.

- **Quellen-Priorisierung** — Die Engine dedupliziert Einträge nach Quelle: Hauptwörterbücher (Priorität 3) schlagen Fictionary/Neologikum (Priorität 2) schlagen Gap-Fill (Priorität 0). Sekundäre Quellen erhalten zusätzlich einen Score-Malus von −15.

- **Optimierte Scoring-Funktion** — Richtungsabhängige Bewertung: Bei `de2goa`-Übersetzungen erhalten exakte und Präfix-Übereinstimmungen Boni. Kurze Wörter (≤ 6 Zeichen) bekommen einen höheren Fuzzy-Schwellenwert, um Zufallstreffer zu vermeiden.

- **Erweitertes Stemming** — Deutsche Lemma-Erkennung mit Verbkonjugation (1./2./3. Person Singular → Infinitiv), Nomen-Pluralformen, Genitiv → Nominativ, Superlativ/Komparativ → Positiv, Kontraktionen (`im → in dem`, `zum → zu dem`, `ans → an das`, `beim → bei dem`), Umlaut-Varianten (ä↔a, ö↔o, ü↔u, ß↔ss) und Komposita-Brücken (`-heit`, `-keit`, `-ung`, `-lich`, `-isch`).

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

```powershell
pip install pyinstaller
pyinstaller --noconsole --onefile `
  --add-data "Goa'uld-Dictionary.md;." `
  --add-data "Goa'uld-Wörterbuch.md;." `
  --add-data "Goa'uld-Fictionary.md;." `
  --add-data "Goa'uld-Neologikum.md;." `
  goauld_translator.py
```

Die fertige `.exe` findest du im neu erstellten `dist`-Ordner.

> **Hinweis zu PowerShell:** Die Zeilenfortsetzung erfolgt mit Backtick (`` ` ``), nicht mit Caret (`^`). Unter Bash/CMD entsprechend anpassen.

---

## 📚 Vokabular & Daten

Dieses Projekt liefert vier Markdown-Wörterbuchdateien sowie ein eingebettetes Gap-Fill-Vokabular mit häufig gebrauchten Begriffen mit. Die Wörterbücher werden beim Start automatisch eingelesen und zu einem einheitlichen Lexikon von **ca. 3.244 deduplizierten Einträgen** (3.463 roh) zusammengeführt.

### Offizielle Wörterbücher

Diese beiden Wörterbücher dokumentieren das kanonische Vokabular aus dem Stargate-Kinofilm, zehn Staffeln SG-1, *The Ultimate Visual Guide*, dem SG-1-Rollenspiel, dem Mobilspiel *Unleashed* sowie Fan-Community-Analysen. Jedes enthält rund **230 dokumentierte Einträge** plus rund **272 Deutsch-Goa'uld-Direktzuordnungen**.

| Datei | Sprache | Beschreibung |
|-------|---------|--------------|
| `Goa_uld-Dictionary.md` | Englisch | Vollständiges kanonisches Goa'uld-Vokabular mit Etymologien, Grammatikhinweisen und Episodenquellen |
| `Goa_uld-Wörterbuch.md` | Deutsch | Deutschsprachiges Pendant zum kanonischen Wörterbuch |

> **Erstellt von:** Claude Opus 4.6 Erweiterte Recherche

---

### Fiktive Wörterbücher (Konstruierte Erweiterungen)

Diese beiden Wörterbücher erweitern das kanonische Vokabular systematisch in Bereiche, die die Serie undokumentiert ließ — Körperteile, Zahlen, Emotionen, Farben, Technologie und abstraktes Denken — ausschließlich auf Basis belegter kanonischer Wurzeln und dokumentierter Morphologieregeln (Swadesh-Rahmen, Kompositionslogik, Vokalverschiebung, Unas-Erbwörter). Jedes enthält rund **1.000–1.500 Einträge** plus **800+ Direktzuordnungen**.

| Datei | Sprache | Beschreibung |
|-------|---------|--------------|
| `Goa_uld-Fictionary.md` | Englisch | Swadesh-Grundlage, semantische Erweiterungen und moderne Konzepte |
| `Goa_uld-Neologikum.md` | Deutsch | Deutschsprachige Neologismen für moderne und abstrakte Begriffe |

> **Erstellt durch:** Gemeinschaftsarbeit von **Google Gemini 3.1 Pro Deep Research** und **Claude Opus 4.6 Erweiterte Recherche**

---

## 🤝 Mitwirken

**Kree!** Du möchtest das Wörterbuch erweitern oder den Code verbessern? Pull Requests sind jederzeit willkommen.

- Neue Vokabeln einfach als Tabellenzeile in eine der Markdown-Dateien einfügen — der Parser erledigt den Rest.
- Für rückwärtige Zuordnungen (Deutsch → Goa'uld) eine Sektion mit Titel `Deutsch → Goa'uld: Direktzuordnung` (oder Varianten mit Suffix) verwenden.
- Einträge können Sprach-Tags tragen (`lang: "de"` / `lang: "en"`) für verbessertes Such-Scoring.
- Die fiktiven Wörterbücher folgen strengen kanonischen Morphologieregeln — bitte die Konsistenz mit belegten Wurzeln wahren.

**Tek'ma'te.**