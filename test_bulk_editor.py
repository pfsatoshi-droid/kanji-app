import pandas as pd

from bulk_editor import clean_editor_df, prepare_editor_df, sort_editor_df, validate_editor_df


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


def test_sort_by_strokes_uses_numbers_and_leaves_blank_last():
    source = pd.DataFrame([
        {"漢字": "橋", "画数": "16"},
        {"漢字": "明", "画数": "8"},
        {"漢字": "空", "画数": ""},
    ])
    result = sort_editor_df(source, sort_by="画数", ascending=True)
    assert result["漢字"].tolist() == ["明", "橋", "空"]


def test_sort_by_kanken_uses_learning_order():
    source = pd.DataFrame([
        {"漢字": "乙", "漢検級": "1級", "画数": "1"},
        {"漢字": "甲", "漢検級": "10級", "画数": "5"},
        {"漢字": "丙", "漢検級": "準2級", "画数": "5"},
    ])
    result = sort_editor_df(source, sort_by="漢検級", ascending=True)
    assert result["漢字"].tolist() == ["甲", "丙", "乙"]


def test_sort_by_kanji_can_descend():
    source = pd.DataFrame([{"漢字": "一"}, {"漢字": "三"}, {"漢字": "二"}])
    result = sort_editor_df(source, sort_by="漢字", ascending=False)
    assert result["漢字"].tolist() == ["二", "三", "一"]
