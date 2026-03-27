Stargate — Goa'uld Linguistic Interface ⬡

Ein bidirektionaler Übersetzer für die Goa'uld-Sprache aus dem Stargate-Franchise. Dieses Tool bietet sowohl eine moderne grafische Benutzeroberfläche (GUI) im SGC-Terminal-Design als auch ein Command-Line Interface (CLI).

Das Interface nutzt eine Kombination aus einem eingebetteten Kernvokabular und einer erweiterbaren Markdown-Wörterbuchdatei (z. B. opus4.6-en-language-analysis.md), um einzelne Wörter und ganze Sätze zu analysieren.
✨ Features

    Bidirektionale Übersetzung: Übersetzt fließend von Goa'uld nach Deutsch/Englisch und umgekehrt.

    Intelligente Satzanalyse: Analysiert ganze Sätze Token für Token, zeigt primäre Bedeutungen, Alternativen und linguistische Tipps an.

    Fuzzy-Search Engine: Findet Einträge durch exaktes Matching, Präfix-Matching und Fuzzy-Matching – so führen auch Tippfehler zum richtigen Begriff.

    SGC-Design GUI: Eine immersive Oberfläche basierend auf customtkinter im "Dark / Gold / Orange"-Look des Stargate Commands. Ein Fallback auf Standard-tkinter ist ebenfalls integriert.

    Terminal/CLI-Modus: Für schnelle Übersetzungen direkt in der Konsole (--cli).

    Markdown Auto-Parsing: Liest Vokabeln automatisch aus Tabellen in Markdown-Dateien ein. Das Standard-Wörterbuch umfasst dabei rund 250 dokumentierte Einträge aus den Serien und dem RPG.

🚀 Installation

Stelle sicher, dass Python 3 auf deinem System installiert ist.

Klone das Repository und installiere die benötigte Bibliothek für die moderne GUI:
Bash

git clone https://github.com/DaWasteh/goauld-translator.git
cd goauld-translator
pip install customtkinter

    Hinweis: Das Skript versucht bei fehlendem customtkinter eine automatische Installation im Hintergrund durchzuführen.

💻 Verwendung
GUI-Modus (Grafische Oberfläche)

Starte die Anwendung einfach ohne Parameter, um die GUI zu öffnen:
Bash

python goauld_translator.py

Um direkt eine spezifische Markdown-Wörterbuchdatei zu laden:
Bash

python goauld_translator.py --md pfad/zur/datei.md

CLI-Modus (Kommandozeile)

Um das Tool ressourcenschonend im Terminal zu nutzen, verwende das --cli Flag. Du kannst direkt einen Text übergeben oder in den interaktiven Modus wechseln:
Bash

# Interaktiver Modus (Goa'uld nach Deutsch)
python goauld_translator.py --cli --dir goa2de

# Direkte Übersetzung eines Satzes
python goauld_translator.py --cli --dir goa2de --text "Jaffa kree"

📦 Als .EXE verpacken (Windows)

Wenn du das Skript als eigenständige Windows-Anwendung weitergeben willst, kannst du es mit pyinstaller ganz einfach kompilieren:
Bash

pip install pyinstaller
pyinstaller --onefile goauld_translator.py

(Die fertige .exe findest du danach im neu erstellten dist-Ordner).
📚 Vokabular & Daten

Dieses Projekt liefert ein eingebettetes Fallback-Vokabular mit den wichtigsten Begriffen mit. Für den vollen Funktionsumfang liest es automatisch beiliegende Markdown-Dateien (wie opus4.6-en-language-analysis.md oder goauld_dictionary.md) aus.
Das Wörterbuch basiert auf Analysen der Serie, RPG-Sourcebooks und Fan-Wikis.
🤝 Mitwirken

Kree! Du möchtest das Wörterbuch erweitern oder den Code verbessern? Pull Requests sind jederzeit willkommen. Füge neue Vokabeln einfach als Tabellenzeile in die Markdown-Datei ein – der Parser erledigt den Rest.