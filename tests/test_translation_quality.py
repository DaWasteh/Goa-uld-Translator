from __future__ import annotations

from pathlib import Path

import yaml

import goauld_translator as gt
import validate_translation_quality as vt


def test_yaml_overlay_lookup_invariants() -> None:
    vt.validate_lexicon_maps()


def test_language_development_artifacts() -> None:
    vt.validate_language_development_artifacts()


def test_golden_translations() -> None:
    analyzer = vt._load_analyzer()
    cases = yaml.safe_load(vt.GOLDEN_PATH.read_text(encoding="utf-8"))["cases"]
    for case in cases:
        actual = vt._translate(analyzer, case)
        assert actual == case["expected"]


def test_translation_mode_does_not_consume_prefix_fuzzy_phrases() -> None:
    analyzer = vt._load_analyzer()
    analysis = analyzer.analyze("You are a traitor", "de2goa", lang_pref="en")
    tokens = [item["token"] for item in analysis if not item.get("skipped")]
    output = analyzer.build_translation(analysis, direction="de2goa")

    assert "You are" not in tokens
    assert output == "Lo Shol'va"
    assert "Tak mal tiak" not in output


def test_negation_is_not_a_stopword() -> None:
    analyzer = vt._load_analyzer()
    analysis = analyzer.analyze("Ich bin nicht Jaffa", "de2goa", lang_pref="de")
    skipped_tokens = {item["token"].lower() for item in analysis if item.get("skipped")}
    output = analyzer.build_translation(analysis, direction="de2goa")

    assert "nicht" not in skipped_tokens
    assert output == "Ta ia Jaffa"


def test_semantic_modals_are_not_stopwords() -> None:
    analyzer = vt._load_analyzer()
    de_analysis = analyzer.analyze("Ich muss hören", "de2goa", lang_pref="de")
    en_analysis = analyzer.analyze("I can see", "de2goa", lang_pref="en")

    assert {item["token"].lower() for item in de_analysis if item.get("skipped")} == set()
    assert analyzer.build_translation(de_analysis, direction="de2goa") == "Ta Kree Leaa"
    assert analyzer.build_translation(en_analysis, direction="de2goa") == "Ta Dan'ryn Yu'yu"


def test_english_primary_map_is_used_directly() -> None:
    _entries, _paths, _de_map, en_map, _sec_de, _sec_en = gt._load_lexicon()
    assert en_map["traitor"] == "Shol'va"
    assert en_map["humans"] == "Tau'ri"
    assert en_map["human slave"] == "Lo'taur"
    assert en_map["who"] == "Kel'tar"


def test_planned_files_exist() -> None:
    assert Path("GOAULD_GRAMMAR.md").is_file()
    assert Path("goauld_root_registry.yaml").is_file()
