import json

import pandas as pd

from json_export import (
    build_kanji_database,
    find_pair_numbers,
    level_to_number,
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
