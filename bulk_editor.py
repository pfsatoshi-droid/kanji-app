import pandas as pd

from pair_utils import ensure_pair_columns, get_pair_numbers, normalize_legacy_columns, normalize_part


BASE_COLUMNS = ["漢字", "画数", "漢検級", "メモ"]


def prepare_editor_df(df, visible_pair_count=4):
    """編集表用に列を揃え、既存値を文字列として安全に保持する。"""
    result = normalize_legacy_columns(df.copy()).fillna("").astype(str)
    for column in BASE_COLUMNS:
        if column not in result.columns:
            result[column] = ""

    existing_numbers = get_pair_numbers(result)
    max_existing = max(existing_numbers, default=0)
    pair_count = max(int(visible_pair_count), max_existing, 1)
    for pair_number in range(1, pair_count + 1):
        result = ensure_pair_columns(result, pair_number, include_review=True)

    pair_columns = []
    for pair_number in range(1, pair_count + 1):
        pair_columns.extend([
            f"ペア{pair_number}_部品1",
            f"ペア{pair_number}_部品2",
            f"ペア{pair_number}_部品3",
            f"ペア{pair_number}_審議",
            f"ペア{pair_number}_審議理由",
        ])

    other_columns = [column for column in result.columns if column not in BASE_COLUMNS + pair_columns]
    return result[BASE_COLUMNS + pair_columns + other_columns].reset_index(drop=True)


def clean_editor_df(df):
    """完全な空行を除去し、キー項目と部品の前後空白を取り除く。"""
    result = df.copy().fillna("").astype(str)
    strip_columns = ["漢字", "画数", "漢検級"] + [
        column for column in result.columns if column.startswith("ペア")
    ]
    for column in strip_columns:
        if column in result.columns:
            result[column] = result[column].map(normalize_part)

    nonempty_mask = result.apply(
        lambda row: any(normalize_part(value) for value in row),
        axis=1,
    )
    return result[nonempty_mask].reset_index(drop=True)


def validate_editor_df(df):
    """保存可否と、表で確認できるエラー一覧を返す。"""
    cleaned = clean_editor_df(df)
    errors = []

    for row_index, row in cleaned.iterrows():
        sheet_row = row_index + 2
        kanji = normalize_part(row.get("漢字", ""))
        if not kanji:
            errors.append({"行": sheet_row, "列": "漢字", "内容": "漢字を入力してください。"})
        elif len(kanji) != 1:
            errors.append({"行": sheet_row, "列": "漢字", "内容": "漢字は1文字で入力してください。"})

        for pair_number in get_pair_numbers(cleaned):
            parts = [normalize_part(row.get(f"ペア{pair_number}_部品{i}", "")) for i in (1, 2, 3)]
            if any(parts) and (not parts[0] or not parts[1]):
                errors.append({
                    "行": sheet_row,
                    "列": f"ペア{pair_number}",
                    "内容": "部品1・部品2は必須、部品3は任意です。",
                })
    kanji_series = cleaned.get("漢字", pd.Series(dtype=str)).map(normalize_part)
    duplicate_values = set(kanji_series[kanji_series.ne("") & kanji_series.duplicated(keep=False)])
    for row_index, kanji in kanji_series.items():
        if kanji in duplicate_values:
            errors.append({"行": row_index + 2, "列": "漢字", "内容": f"「{kanji}」が重複しています。"})

    return cleaned, pd.DataFrame(errors, columns=["行", "列", "内容"])
