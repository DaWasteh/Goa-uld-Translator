Stargate — Goa'uld Linguistic Interface ⬡

A bidirectional translator for the Goa'uld language from the Stargate franchise. This tool offers both a modern graphical user interface (GUI) in an SGC terminal design and a Command-Line Interface (CLI).

The interface uses a combination of an embedded core vocabulary and an extensible Markdown dictionary file (e.g., opus4.6-en-language-analysis.md) to analyze individual words and entire sentences.
✨ Features

    Bidirectional Translation: Translates fluently from Goa'uld to English/German and vice versa.

    Intelligent Sentence Analysis: Analyzes entire sentences token by token, showing primary meanings, alternatives, and linguistic tips.

    Fuzzy-Search Engine: Finds entries through exact matching, prefix matching, and fuzzy matching – meaning even typos will lead you to the right term.

    SGC-Design GUI: An immersive interface based on customtkinter featuring the "Dark / Gold / Orange" look of Stargate Command. A fallback to standard tkinter is also integrated.

    Terminal/CLI Mode: For quick translations directly in your console using the --cli flag.

    Markdown Auto-Parsing: Automatically reads vocabulary from tables within Markdown files. The default dictionary contains roughly 250 documented entries from the television series and the RPG.

🚀 Installation

Make sure you have Python 3 installed on your system.

Clone the repository and install the required library for the modern GUI:
Bash

git clone https://github.com/DaWasteh/goauld-translator.git
cd goauld-translator
pip install customtkinter

    Note: The script will attempt an automatic background installation if it detects that customtkinter is missing.

💻 Usage
GUI Mode (Graphical Interface)

Simply start the application without any parameters to open the GUI:
Bash

python goauld_translator.py

To load a specific Markdown dictionary file directly:
Bash

python goauld_translator.py --md path/to/file.md

CLI Mode (Command Line)

To run the tool efficiently in your terminal, use the --cli flag. You can translate a string of text directly or jump into interactive mode:
Bash

# Interactive Mode (Goa'uld to English/German)
python goauld_translator.py --cli --dir goa2de

# Direct translation of a specific sentence
python goauld_translator.py --cli --dir goa2de --text "Jaffa kree"

📦 Pack as .EXE (Windows)

If you want to distribute the script as a standalone Windows application, you can easily compile it using pyinstaller:
Bash

pip install pyinstaller
pyinstaller --onefile goauld_translator.py

(You will find the finished .exe inside the newly created dist folder).
📚 Vocabulary & Data

This project comes with an embedded fallback vocabulary containing the most crucial terms. For full functionality, it automatically reads included Markdown files (like opus4.6-en-language-analysis.md or goauld_dictionary.md).
The dictionary is based on detailed analyses of the TV series, RPG sourcebooks, and fan wikis.
🤝 Contributing

Kree! Want to expand the dictionary or improve the code? Pull requests are always welcome. Simply add new vocabulary as a new table row in the Markdown file – the parser will handle the rest.