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
OVERLAY_PATH = ROOT / "goauld_overrides.yaml"
GRAMMAR_PATH = ROOT / "GOAULD_GRAMMAR.md"
ROOT_REGISTRY_PATH = ROOT / "goauld_root_registry.yaml"


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
        ("de", "ich"): "Ta",
        ("en", "i"): "Ta",
        ("de", "ich habe"): "Tel",
        ("en", "i have"): "Tel",
        ("de", "mensch"): "Tau'ri",
        ("de", "menschen"): "Tau'ri",
        ("en", "human"): "Tau'ri",
        ("en", "humans"): "Tau'ri",
        ("de", "menschheit"): "Tap'tar",
        ("en", "humanity"): "Tap'tar",
        ("de", "menschlicher sklave"): "Lo'taur",
        ("en", "human slave"): "Lo'taur",
        ("de", "nicht"): "ia",
        ("en", "not"): "ia",
        ("de", "kein"): "Ka",
        ("en", "no"): "Ka",
        ("de", "wer"): "Kel'tar",
        ("en", "who"): "Kel'tar",
        ("de", "was"): "Kel'shak",
        ("en", "what"): "Kel'shak",
        ("de", "wo"): "Kel'pac",
        ("en", "where"): "Kel'pac",
        ("de", "wann"): "Kel'nok",
        ("en", "when"): "Kel'nok",
        ("de", "wie"): "Kel'met",
        ("en", "how"): "Kel'met",
        ("de", "groß"): "Tun'le",
        ("en", "large"): "Tun'le",
        ("de", "gott"): "Onak",
        ("en", "god"): "Onak",
        ("de", "tor"): "Chappa'ai",
        ("en", "gate"): "Chappa'ai",
        ("de", "muss"): "Kree",
        ("en", "must"): "Kree",
        ("de", "kann"): "Dan'ryn",
        ("en", "can"): "Dan'ryn",
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


def validate_language_development_artifacts() -> None:
    for path in (OVERLAY_PATH, GRAMMAR_PATH, ROOT_REGISTRY_PATH):
        if not path.is_file():
            raise AssertionError(f"required language-development artifact missing: {path.name}")

    overlay = yaml.safe_load(OVERLAY_PATH.read_text(encoding="utf-8")) or {}
    substrate = overlay.get("egyptian_substrate") or {}
    entries = overlay.get("entries") or {}
    if len(substrate) < 8:
        raise AssertionError("egyptian_substrate reservoir is too small")
    for key in ("rn", "nTr", "pr", "ib", "ankh", "ra", "mAat", "mdw"):
        if key not in substrate:
            raise AssertionError(f"missing Egyptian substrate root: {key}")
        if "tla_id" not in substrate[key]:
            raise AssertionError(f"Egyptian substrate root {key} has no tla_id field")

    required_overlay_entries = {
        "app_override_pronoun_ta",
        "app_override_pronoun_tel_special",
        "app_override_lo_taur_slave",
        "app_override_interrogative_who",
        "app_override_interrogative_what",
        "app_override_negation_ia",
        "app_core_gate",
        "app_core_life_root",
    }
    missing = required_overlay_entries.difference(entries)
    if missing:
        raise AssertionError(f"missing planned overlay entries: {sorted(missing)}")

    for key, entry in entries.items():
        if not entry.get("review_status"):
            raise AssertionError(f"overlay entry {key} has no review_status")
        senses = entry.get("senses") or []
        if not senses:
            raise AssertionError(f"overlay entry {key} has no senses")
        for sense in senses:
            glosses = sense.get("glosses") or {}
            if not glosses.get("de") or not glosses.get("en"):
                raise AssertionError(f"overlay sense {key}:{sense.get('id')} lacks DE+EN glosses")
            if not sense.get("examples"):
                raise AssertionError(f"overlay sense {key}:{sense.get('id')} has no examples")

    root_registry = yaml.safe_load(ROOT_REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    roots = root_registry.get("roots") or {}
    for root in ("kree", "kek", "kel", "tok", "onak", "tar", "tau_ri", "sha", "ren", "vol", "delmac"):
        if root not in roots:
            raise AssertionError(f"root registry missing root: {root}")
        if not roots[root].get("core_meaning"):
            raise AssertionError(f"root registry root {root} has no core_meaning")

    grammar = GRAMMAR_PATH.read_text(encoding="utf-8")
    for required in ("SVO", "Pronouns", "Negation", "Egyptian substrate", "root"):
        if required not in grammar:
            raise AssertionError(f"grammar spec missing required section/content: {required}")


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
    validate_language_development_artifacts()
    validate_golden_translations()
    print("translation-quality validation passed")


if __name__ == "__main__":
    main()
