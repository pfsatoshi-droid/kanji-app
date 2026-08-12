import pandas as pd

from pair_utils import (
    ensure_pair_columns,
    get_pair_numbers,
    normalize_legacy_columns,
    pair_key,
    validate_parts,
)


def test_existing_two_part_data_remains_valid():
    parts, error = validate_parts("日", "月", "")
    assert error is None
    assert parts == ("日", "月", "")


def test_third_part_is_supported_and_part_two_stays_required():
    assert validate_parts("木", "目", "心") == (("木", "目", "心"), None)
    assert validate_parts("木", "", "心")[0] is None
    assert validate_parts("日", "月", float("nan")) == (("日", "月", ""), None)


def test_pair_columns_include_optional_third_part():
    df = ensure_pair_columns(pd.DataFrame({"漢字": ["想"]}), 1, include_review=True)
    assert [
        "ペア1_部品1", "ペア1_部品2", "ペア1_部品3", "ペア1_審議", "ペア1_審議理由"
    ] == [column for column in df.columns if column != "漢字"]


def test_legacy_two_part_columns_are_migrated_without_requiring_part_three():
    df = normalize_legacy_columns(pd.DataFrame([{"漢字": "明", "部品1": "日", "部品2": "月"}]))
    assert df.loc[0, "ペア1_部品1"] == "日"
    assert df.loc[0, "ペア1_部品2"] == "月"
    assert "ペア1_部品3" not in df.columns
    assert "部品1" not in df.columns


def test_pair_identity_includes_third_part_but_normalizes_two_part_tuples():
    assert pair_key(("日", "月")) == ("日", "月", "")
    assert pair_key({"part1": "木", "part2": "目", "part3": "心"}) == ("木", "目", "心")


def test_pair_numbers_are_found_from_any_part_column():
    df = pd.DataFrame(columns=["ペア2_部品3", "ペア1_部品1"])
    assert get_pair_numbers(df) == [1, 2]
