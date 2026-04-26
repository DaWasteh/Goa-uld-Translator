"""
CI Dictionary Check -- wird von GitHub Actions aufgerufen.
Prueft: goauld_lexicon.yaml + alle 4 MD-Woerterbuechdateien.
Cross-platform (Linux / macOS / Windows), keine Sonderzeichen im Code.
"""
import os
import pathlib
import sys

# YAML-Lexikon
try:
    import yaml
    lex = pathlib.Path("goauld_lexicon.yaml")
    assert lex.exists(), "goauld_lexicon.yaml fehlt!"
    data = yaml.safe_load(lex.read_text(encoding="utf-8"))
    entries = data.get("entries", {})
    assert len(entries) >= 500, f"Zu wenige Eintraege im YAML: {len(entries)}"
    print(f"[OK] YAML geladen: {len(entries)} Eintraege")
except ImportError:
    print("[SKIP] pyyaml nicht installiert -- YAML-Check uebersprungen")

# Markdown-Dateien (alle Namen ohne Sonderzeichen)
REQUIRED = [
    "Goauld-Dictionary.md",
    "Goauld-Fictionary.md",
    "Goauld-Neologikum.md",
    "Goauld-Woerterbuch.md",
]

files = os.listdir(".")
failed = False

for fname in REQUIRED:
    if fname not in files:
        print(f"[FAIL] Fehlende Datei: {fname}")
        failed = True
        continue
    content = pathlib.Path(fname).read_text(encoding="utf-8")
    if len(content) < 500:
        print(f"[FAIL] Datei zu kurz: {fname} ({len(content)} Zeichen)")
        failed = True
    else:
        print(f"[OK] {fname} ({len(content):,} Zeichen)")

if failed:
    print("\nEin oder mehrere Dictionary-Checks fehlgeschlagen!")
    sys.exit(1)

print("\nAlle Dictionary-Checks bestanden.")
