#!/usr/bin/env python3
"""Regression validation for the Goa'uld translation-quality pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

import goauld_translator as gt
from yaml_loader import find_lexicon_yaml, load_lexicon_yaml

ROOT = Path(__file__).resolve().parent
GOLDEN_PATH = ROOT / "tests" / "golden_translations.yaml"


def _load_analyzer() -> gt.SentenceAnalyzer:
    entries, _paths, _de_map, _en_map, _sec_de, _sec_en = gt._load_lexicon()
    return gt.SentenceAnalyzer(gt.SearchEngine(entries))


def _translate(analyzer: gt.SentenceAnalyzer, case: dict[str, Any]) -> str:
    analysis = analyzer.analyze(
        str(case["text"]),
        str(case.get("direction", "de2goa")),
        lang_pref=str(case.get("lang", "de")),
    )
    return analyzer.build_translation(analysis, direction=str(case.get("direction", "de2goa")))


def validate_lexicon_maps() -> None:
    yaml_path = find_lexicon_yaml()
    if not yaml_path:
        raise AssertionError("goauld_lexicon.yaml not found")

    _entries, de_map, en_map, secondary_de, secondary_en = load_lexicon_yaml(yaml_path)

    expected_primary = {
        ("de", "mensch"): "Tau'ri",
        ("de", "menschen"): "Tau'ri",
        ("en", "human"): "Tau'ri",
        ("en", "humans"): "Tau'ri",
        ("de", "menschheit"): "Tap'tar",
        ("en", "humanity"): "Tap'tar",
        ("de", "nicht"): "ia",
        ("en", "not"): "ia",
        ("de", "kein"): "Ka",
        ("en", "no"): "Ka",
    }
    maps = {"de": de_map, "en": en_map}
    for (lang, key), expected in expected_primary.items():
        actual = maps[lang].get(key)
        if actual != expected:
            raise AssertionError(f"{lang}:{key} -> {actual!r}, expected {expected!r}")

    for lang, primary, secondary in (
        ("de", de_map, secondary_de),
        ("en", en_map, secondary_en),
    ):
        for key, alternatives in secondary.items():
            if key not in primary:
                raise AssertionError(f"secondary {lang}:{key!r} has no primary source")
            if primary[key] in alternatives:
                raise AssertionError(f"secondary {lang}:{key!r} repeats primary {primary[key]!r}")

    bad_prefixes = ("auch ", "also ")
    for lang, primary in maps.items():
        for key in primary:
            lowered = key.lower().strip()
            if lowered.startswith(bad_prefixes) or 'auch "' in lowered or 'also "' in lowered:
                raise AssertionError(f"unexpected bridge gloss in {lang} map: {key!r}")


def validate_golden_translations() -> None:
    analyzer = _load_analyzer()
    data = yaml.safe_load(GOLDEN_PATH.read_text(encoding="utf-8")) or {}
    cases = data.get("cases", [])
    if not cases:
        raise AssertionError("no golden translation cases found")

    for case in cases:
        actual = _translate(analyzer, case)
        expected = str(case["expected"])
        if actual != expected:
            raise AssertionError(f"{case['text']!r}: {actual!r}, expected {expected!r}")
        for required in case.get("must_contain", []) or []:
            if str(required) not in actual:
                raise AssertionError(f"{case['text']!r}: missing required {required!r} in {actual!r}")
        for forbidden in case.get("forbidden", []) or []:
            if str(forbidden) in actual:
                raise AssertionError(f"{case['text']!r}: forbidden {forbidden!r} in {actual!r}")


def main() -> None:
    validate_lexicon_maps()
    validate_golden_translations()
    print("translation-quality validation passed")


if __name__ == "__main__":
    main()
