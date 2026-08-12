import json

import pandas as pd

from json_export import (
    build_kanji_database,
    build_kanji_database_v2,
    find_pair_numbers,
    level_to_number,
    level_to_float,
    stroke_count_to_int,
    to_json_text,
)


def sample_df():
    return pd.DataFrame(
        [
            {"漢字": "一", "漢検級": "10級", "ペア1_部品1": "", "ペア1_部品2": ""},
            {"漢字": "白", "漢検級": "9級", "ペア1_部品1": "", "ペア1_部品2": ""},
            {"漢字": "百", "漢検級": "8級", "ペア1_部品1": "一", "ペア1_部品2": "白"},
            {"漢字": "自", "漢検級": "8級", "ペア1_部品1": "白", "ペア1_部品2": "一"},
        ]
    )


def test_find_pair_numbers_requires_both_sides():
    assert find_pair_numbers(["ペア2_部品2", "ペア1_部品1", "ペア1_部品2"]) == [1]


def test_find_pair_numbers_accepts_optional_third_part():
    assert find_pair_numbers(["ペア1_部品1", "ペア1_部品2", "ペア1_部品3"]) == [1]


def test_builds_bidirectional_transforms_and_groups_results():
    result = build_kanji_database(sample_df())
    entries = {item["baseKanji"]: item for item in result["kanjiDatas"]}

    assert entries["一"]["level"] == 10
    assert entries["一"]["kanjiTransforms"] == [
        {"modifier": "白", "results": ["百", "自"]}
    ]
    assert entries["白"]["kanjiTransforms"] == [
        {"modifier": "一", "results": ["百", "自"]}
    ]
    assert entries["百"]["kanjiTransforms"] == []


def test_json_keeps_japanese_characters():
    text = to_json_text(sample_df())
    assert '"baseKanji": "一"' in text
    assert json.loads(text)["kanjiDatas"][0]["baseKanji"] == "一"


def test_level_counts_down_for_pre_levels():
    assert [level_to_number(level) for level in [
        "3級", "準2級", "2級", "準1級", "1級"
    ]] == [3, 2, 1, 0, -1]


def test_three_part_decomposition_is_not_misrepresented_as_binary_json():
    df = sample_df()
    df.loc[df["漢字"] == "百", "ペア1_部品3"] = "自"
    result = build_kanji_database(df)
    entries = {item["baseKanji"]: item for item in result["kanjiDatas"]}
    assert entries["一"]["kanjiTransforms"] == [{"modifier": "白", "results": ["自"]}]


def test_v2_uses_float_levels_and_integer_stroke_count():
    df = sample_df()
    df["画数"] = ["1", "5", "6", "6"]
    df.loc[df["漢字"] == "百", "漢検級"] = "準2級"
    entries = {item["baseKanji"]: item for item in build_kanji_database_v2(df)["kanjiDatas"]}
    assert entries["百"]["level"] == 2.5
    assert isinstance(entries["百"]["level"], float)
    assert entries["百"]["strokeCount"] == 6


def test_v2_exports_two_and_three_part_modifiers_arrays():
    df = pd.DataFrame([
        {"漢字": "一", "漢検級": "10級", "画数": "1"},
        {"漢字": "二", "漢検級": "10級", "画数": "2", "ペア1_部品1": "一", "ペア1_部品2": "一"},
        {"漢字": "三", "漢検級": "10級", "画数": "3", "ペア1_部品1": "一", "ペア1_部品2": "一", "ペア1_部品3": "一"},
    ])
    entries = {item["baseKanji"]: item for item in build_kanji_database_v2(df)["kanjiDatas"]}
    assert entries["一"]["kanjiTransforms"] == [
        {"modifiers": ["一"], "results": ["二"]},
        {"modifiers": ["一", "一"], "results": ["三"]},
    ]


def test_v2_conversion_helpers_handle_invalid_values():
    assert level_to_float("1級") == 1.0
    assert level_to_float("準1級") == 1.5
    assert stroke_count_to_int("16") == 16
    assert stroke_count_to_int("16.5") is None
    assert stroke_count_to_int("") is None
