import pandas as pd

from bulk_editor import clean_editor_df, prepare_editor_df, validate_editor_df


def test_prepare_adds_optional_third_part_without_changing_two_part_values():
    source = pd.DataFrame([{"漢字": "明", "ペア1_部品1": "日", "ペア1_部品2": "月"}])
    result = prepare_editor_df(source, visible_pair_count=1)
    assert result.loc[0, "ペア1_部品1"] == "日"
    assert result.loc[0, "ペア1_部品2"] == "月"
    assert result.loc[0, "ペア1_部品3"] == ""


def test_clean_removes_only_completely_empty_rows():
    source = pd.DataFrame([{"漢字": "明", "メモ": ""}, {"漢字": "", "メモ": ""}])
    assert clean_editor_df(source).to_dict("records") == [{"漢字": "明", "メモ": ""}]


def test_validation_accepts_two_and_three_parts():
    source = pd.DataFrame([
        {"漢字": "明", "ペア1_部品1": "日", "ペア1_部品2": "月", "ペア1_部品3": ""},
        {"漢字": "想", "ペア1_部品1": "木", "ペア1_部品2": "目", "ペア1_部品3": "心"},
    ])
    _, errors = validate_editor_df(source)
    assert errors.empty


def test_validation_rejects_duplicate_kanji_and_incomplete_parts():
    source = pd.DataFrame([
        {"漢字": "明", "ペア1_部品1": "日", "ペア1_部品2": ""},
        {"漢字": "明", "ペア1_部品1": "日", "ペア1_部品2": "月"},
    ])
    _, errors = validate_editor_df(source)
    assert len(errors[errors["内容"].str.contains("重複")]) == 2
    assert len(errors[errors["内容"].str.contains("部品1・部品2")]) == 1


def test_hidden_review_data_does_not_block_table_save():
    source = pd.DataFrame([{"漢字": "明", "ペア1_審議": "TRUE", "ペア1_審議理由": "確認中"}])
    cleaned, errors = validate_editor_df(source)
    assert errors.empty
    assert cleaned.loc[0, "ペア1_審議"] == "TRUE"
    assert cleaned.loc[0, "ペア1_審議理由"] == "確認中"
