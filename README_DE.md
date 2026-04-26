# Stargate — Goa'uld Linguistic Interface ⬡
### Version 0.2.8

Ein bidirektionaler Übersetzer für die Goa'uld-Sprache aus dem Stargate-Franchise. Dieses Tool bietet sowohl eine immersive grafische Benutzeroberfläche (GUI) im Stil eines SGC-Kommandoterminals als auch ein Command-Line Interface (CLI).

Das Interface kombiniert ein strukturiertes YAML-Lexikon, vier erweiterbare Markdown-Wörterbuchdateien und ein eingebettetes Kernvokabular, um einzelne Wörter und ganze Sätze zu analysieren.

---

## 🆕 Neu in v0.2.6

- **YAML-Lexikon als primäres Datenformat** — Das neue `goauld_lexicon.yaml` bündelt alle vier Wörterbücher in einer strukturierten Quelle mit **~5.850 Einträgen**, Prioritäts-Tiers (canon_series → fanon_derived), `glosses.de/en`-Feldern pro Bedeutung und expliziten Quellenangaben. Die vier Markdown-Dateien bleiben als vollwertiger **Fallback** erhalten — fehlt die YAML, greift der alte MD-Loader automatisch und das Tool läuft ohne Funktionsverlust weiter.

- **„Auch:"-Alternativen für polyseme Begriffe** — Wenn ein deutsches oder englisches Wort mehrere Goa'uld-Übersetzungen hat (z. B. `krieger → Jaffa` mit Alternative `mel'shak'tar`), wird die kanonische Wahl als Primärtreffer angezeigt und alle weiteren Varianten in einer kompakten **`auch:`**-Zeile direkt darunter. In der Satzanalyse (`⊕ DEBRIEF`) erscheint ein eigener **`AUCH`**-Block pro Token mit bis zu fünf Alternativen.

- **Bilinguale UI** — Die Richtungsbuttons zeigen jetzt konsistent **`DE/EN → Goa'uld`** und **`Goa'uld → DE/EN`** (vorher nur `DE`). Statusleiste und Eingabe-Platzhalter wurden entsprechend angeglichen. Der Sprach-Toggle (🇩🇪 DE / 🇬🇧 EN) entscheidet, welche Secondary-Map bei polysemen Begriffen zuerst konsultiert wird — mit automatischem Fallback auf die andere Sprache für Lehnwörter.

- **Robustheit in `.exe`-Bundles** — YAML und `yaml_loader.py` werden jetzt zuverlässig aus `sys._MEIPASS` (PyInstaller `--onefile`-Extraktverzeichnis) **und** dem Verzeichnis neben der `.exe` geladen. Damit funktioniert sowohl die eingebettete Auslieferung als auch eine extern austauschbare YAML-Datei ohne Rebuild.

- **Bugfixes** —
  - **Richtungs-Umschalter** reagierte auf das zweite Label nie korrekt wegen fragiler Whitespace-Matches (kaschiert durch hardcodierten Initialzustand); jetzt via robustem Pfeil-Split.
  - **Einrückungsfehler im `_browse_md`** zerlegte die `GoauldApp`-Klasse für den Parser (38+ Pylance-Folgefehler) — behoben.
  - **`log.warning()` vor Logger-Initialisierung** warf `NameError` beim Import-Fehler des YAML-Loaders — jetzt zurückgestellt bis nach `_setup_logging()`.
  - **`tk.messagebox`** crashte im GUI-Fehler-Fallback mangels expliziten Submodul-Imports — behoben mit `from tkinter import messagebox`.
  - **`--cli`-Modus in `--noconsole`-EXE** lief in `print`-Crashes wegen `sys.stdout is None` — Guard am Anfang von `run_cli()`.
  - **Typannotationen** für Optional-Variablen nachgeschärft (mypy-clean).

---

## ✨ Features

- **Bidirektionale Übersetzung** — Übersetzt fließend von Goa'uld nach Deutsch/Englisch und umgekehrt. Richtung und Zielsprache lassen sich jederzeit umschalten.

- **Intelligente Satzanalyse** — Analysiert ganze Sätze Token für Token und zeigt primäre Bedeutungen, Alternativen, polyseme `auch:`-Varianten und linguistische Tipps im Tab `⊕ DEBRIEF` an.

- **Live-Transmission** — Eine Echtzeit-Übersetzungsansicht (`⚡ LIVE-TRANSMISSION`) liest direkt aus der Hauptsuchleiste mit verzögerter Aktualisierung — ganz ohne Dialog-Popups.

- **Briefing-Ansicht** — Der Tab `◈ BRIEFING` zeigt strukturierte Bedeutungsabschnitte, Grammatikhinweise, semantische Verwandte und quellenbasierte Alternativen für jeden ausgewählten Eintrag.

- **Fuzzy-Search Engine** — Findet Einträge durch exaktes Matching, Präfix-Matching und Fuzzy-Matching — auch Tippfehler führen zum richtigen Begriff. Enthält Sprachpräferenz-Scoring, Quellen-Priorisierung und dynamische Fuzzy-Schwellen für kurze Wörter.

- **SGC-Kommandoterminal GUI** — Immersive Oberfläche auf Basis von `customtkinter` mit *Dark / Gold / Blue / Orange*-Palette, Classification Bar, pulsierenden Chevron-Anzeigen, Event-Horizon-Glyphen und verschiebbaren Panels über einen Tor-blauen Sash-Divider. Ein Fallback auf Standard-`tkinter` ist integriert.

- **Terminal / CLI-Modus** — Für schnelle Übersetzungen direkt in der Konsole über das `--cli`-Flag.

- **YAML-Lexikon mit Tier-System** — Kanonische Quellen (`canon_series`, `canon_film`) schlagen Fanon-Erweiterungen, wodurch polyseme Begriffe eine kanonisch fundierte Primär-Entscheidung bekommen und alle weiteren Varianten als `secondary` angezeigt werden.

- **Markdown Auto-Parsing als Fallback** — Liest Vokabeln automatisch aus Tabellen in Markdown-Dateien ein. Unterstützt sowohl direkte `Goa'uld → Deutsch`-Tabellen als auch umgekehrte `Deutsch → Goa'uld: Direktzuordnung`-Sektionen inklusive Varianten mit Suffix (`(Neologikum)`, `(Fictionary)` etc.).

- **Auto-Installer** — Versucht bei fehlendem `customtkinter` automatisch eine Hintergrundinstallation mit `ensurepip`-Fallback-Hinweis.

- **DE_MAP-Priorität** — Bei der Übersetzung von Deutsch nach Goa'uld (`de2goa`) hat das direkte Wörterbuch (DE_MAP) stets Vorrang vor der Fuzzy-Search-Engine.

- **Multi-Wort-Phrasen in der Engine** — Die Engine sucht nun auch nach Multi-Wort-Phrasen, nicht nur DE_MAP — das verbessert die Trefferquote für Satzfragmente und längere Ausdrücke.

- **Quellen-Priorisierung** — Die Engine dedupliziert Einträge nach Quelle: Hauptwörterbücher (Priorität 3) schlagen Fictionary/Neologikum (Priorität 2) schlagen Gap-Fill (Priorität 0). Sekundäre Quellen erhalten zusätzlich einen Score-Malus von −15.

- **Optimierte Scoring-Funktion** — Richtungsabhängige Bewertung: Bei `de2goa`-Übersetzungen erhalten exakte und Präfix-Übereinstimmungen Boni. Kurze Wörter (≤ 6 Zeichen) bekommen einen höheren Fuzzy-Schwellenwert, um Zufallstreffer zu vermeiden.

- **Erweitertes Stemming** — Deutsche Lemma-Erkennung mit Verbkonjugation (1./2./3. Person Singular → Infinitiv), Nomen-Pluralformen, Genitiv → Nominativ, Superlativ/Komparativ → Positiv, Kontraktionen (`im → in dem`, `zum → zu dem`, `ans → an das`, `beim → bei dem`), Umlaut-Varianten (ä↔a, ö↔o, ü↔u, ß↔ss) und Komposita-Brücken (`-heit`, `-keit`, `-ung`, `-lich`, `-isch`).

---

## 🚀 Installation

Stelle sicher, dass **Python 3** auf deinem System installiert ist.

Klone das Repository und installiere die benötigten Bibliotheken:

```bash
git clone https://github.com/DaWasteh/goauld-translator.git
cd goauld-translator
pip install customtkinter pyyaml
```

> **Hinweis:** Das Skript versucht bei fehlendem `customtkinter` eine automatische Installation im Hintergrund durchzuführen. Fehlt `pyyaml`, fällt das Tool automatisch auf den Markdown-Loader zurück — mit entsprechender Warnmeldung im Log.

---

## 💻 Verwendung

### GUI-Modus (Grafische Oberfläche)

Starte die Anwendung einfach ohne Parameter, um die GUI zu öffnen:

```bash
python goauld_translator.py
```

Um direkt eine spezifische Markdown-Wörterbuchdatei zu laden (erzwingt MD-Modus, überspringt YAML):

```bash
python goauld_translator.py --md pfad/zur/datei.md
```

### CLI-Modus (Kommandozeile)

Verwende das `--cli`-Flag für ressourcenschonende Nutzung im Terminal. Du kannst direkt einen Text übergeben oder in den interaktiven Modus wechseln:

```bash
# Interaktiver Modus (Goa'uld nach Deutsch/Englisch)
python goauld_translator.py --cli --dir goa2de

# Direkte Übersetzung eines Satzes
python goauld_translator.py --cli --dir goa2de --text "Jaffa kree"
```

---

## 📦 Als .EXE verpacken (Windows)

Wenn du das Skript als eigenständige Windows-Anwendung weitergeben willst, kompiliere es mit `pyinstaller`:

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

Die fertige `.exe` findest du im neu erstellten `dist`-Ordner.

> **Hinweis zu PowerShell:** Die Zeilenfortsetzung erfolgt mit Backtick (`` ` ``), nicht mit Caret (`^`). Unter Bash/CMD entsprechend anpassen.

> **Tipp bei `PermissionError` während des Builds:** Stelle sicher, dass keine alte `goauld_translator.exe` im Task-Manager noch läuft und dass keine Explorer-Fenster den `dist`-Ordner offen haben. Vorher einmal `Remove-Item -Recurse -Force .\build, .\dist` ausführen beseitigt Reste aus vorherigen Builds.

> **Austauschbare YAML:** Das Tool sucht `goauld_lexicon.yaml` sowohl im `_MEIPASS`-Bundle als auch **neben der `.exe`**. Dadurch kannst du eine aktualisierte YAML ausliefern, ohne die EXE neu zu bauen — einfach die neue Datei ins gleiche Verzeichnis legen.

---

## 📚 Vokabular & Daten

Dieses Projekt liefert ein strukturiertes YAML-Lexikon sowie vier Markdown-Wörterbuchdateien mit. Beim Start wird bevorzugt `goauld_lexicon.yaml` geladen (**~5.850 Einträge** mit Prioritäts-Tiers und Mehrsprachigkeit); fehlt die YAML, parst der Fallback-Loader alle vier Markdown-Dateien zu einem vereinheitlichten Lexikon (**~3.463 Einträge, 3.244 nach Deduplizierung**).

### Offizielle Wörterbücher

Diese beiden Wörterbücher dokumentieren das kanonische Vokabular aus dem Stargate-Kinofilm, zehn Staffeln SG-1, *The Ultimate Visual Guide*, dem SG-1-Rollenspiel, dem Mobilspiel *Unleashed* sowie Fan-Community-Analysen. Jedes enthält rund **230 dokumentierte Einträge** plus rund **272 Deutsch-Goa'uld-Direktzuordnungen**.

| Datei | Sprache | Beschreibung |
|-------|---------|--------------|
| `Goauld-Dictionary.md` | Englisch | Vollständiges kanonisches Goa'uld-Vokabular mit Etymologien, Grammatikhinweisen und Episodenquellen |
| `Goauld-Woerterbuch.md` | Deutsch | Deutschsprachiges Pendant zum kanonischen Wörterbuch |

> **Erstellt von:** Claude Opus 4.6 Erweiterte Recherche

---

### Fiktive Wörterbücher (Konstruierte Erweiterungen)

Diese beiden Wörterbücher erweitern das kanonische Vokabular systematisch in Bereiche, die die Serie undokumentiert ließ — Körperteile, Zahlen, Emotionen, Farben, Technologie und abstraktes Denken — ausschließlich auf Basis belegter kanonischer Wurzeln und dokumentierter Morphologieregeln (Swadesh-Rahmen, Kompositionslogik, Vokalverschiebung, Unas-Erbwörter). Jedes enthält rund **1.000–1.500 Einträge** plus **800+ Direktzuordnungen**.

| Datei | Sprache | Beschreibung |
|-------|---------|--------------|
| `Goauld-Fictionary.md` | Englisch | Swadesh-Grundlage, semantische Erweiterungen und moderne Konzepte |
| `Goauld-Neologikum.md` | Deutsch | Deutschsprachige Neologismen für moderne und abstrakte Begriffe |

> **Erstellt durch:** Gemeinschaftsarbeit von **Google Gemini 3.1 Pro Deep Research** und **Claude Opus 4.6 Erweiterte Recherche**

---

### Konsolidiertes YAML-Lexikon

`goauld_lexicon.yaml` ist die zusammengeführte Auswertung aller vier Markdown-Wörterbücher mit zusätzlichen Metadaten pro Bedeutung:

- **Tier-System** (`canon_series`, `canon_film`, `canon_guide`, `canon_rpg`, `abydonian`, `fanon_strict`, `fanon_derived`, …) als Autoritätssignal
- **Prioritäten** für Tiebreaker bei polysemen Begriffen (kanonische Wahl gewinnt Primärtreffer)
- **`glosses.de` / `glosses.en`** pro Bedeutung für saubere bilinguale Suche
- **~163 DE- und ~132 EN-Secondary-Einträge** für die neue `auch:`-Anzeige

---

## 🤝 Mitwirken

**Kree!** Du möchtest das Wörterbuch erweitern oder den Code verbessern? Pull Requests sind jederzeit willkommen.

- Neue Vokabeln einfach als Tabellenzeile in eine der Markdown-Dateien einfügen — der Parser erledigt den Rest.
- Für rückwärtige Zuordnungen (Deutsch → Goa'uld) eine Sektion mit Titel `Deutsch → Goa'uld: Direktzuordnung` (oder Varianten mit Suffix) verwenden.
- Einträge können Sprach-Tags tragen (`lang: "de"` / `lang: "en"`) für verbessertes Such-Scoring.
- Die fiktiven Wörterbücher folgen strengen kanonischen Morphologieregeln — bitte die Konsistenz mit belegten Wurzeln wahren.
- Für strukturierte YAML-Beiträge: neue Einträge in `goauld_lexicon.yaml` mit passendem `tier` und `priority` ergänzen; `yaml_loader.py` übernimmt die Expansion.

**Tek'ma'te.**