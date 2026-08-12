import json
import re

import pandas as pd


LEVEL_NUMBERS = {
    "10級": 10,
    "9級": 9,
    "8級": 8,
    "7級": 7,
    "6級": 6,
    "5級": 5,
    "4級": 4,
    "3級": 3,
    "準2級": 2,
    "2級": 1,
    "準1級": 0,
    "1級": -1,
}

PAIR_COLUMN_PATTERN = re.compile(r"^ペア(\d+)_部品([123])$")


def level_to_number(level):
    """10級を10として、級区分が上がるごとに1ずつ減らす。"""
    if pd.isna(level):
        return None

    value = str(level).strip()
    if not value:
        return None
    if value in LEVEL_NUMBERS:
        return LEVEL_NUMBERS[value]

    try:
        number = float(value)
        return int(number) if number.is_integer() else number
    except ValueError:
        return None


def find_pair_numbers(columns):
    """データに実在する部品ペア番号を昇順で返す。"""
    found = {}
    for column in columns:
        match = PAIR_COLUMN_PATTERN.match(str(column))
        if match:
            pair_number = int(match.group(1))
            found.setdefault(pair_number, set()).add(int(match.group(2)))

    return sorted(number for number, sides in found.items() if {1, 2}.issubset(sides))


def build_kanji_database(df):
    """
    漢字行と部品ペアから、ゲーム用の逆引きJSONデータを作る。

    出力対象は「漢字」列に登録されている全漢字。部品も登録漢字である
    組み合わせだけを収録し、同じ結果は重複させない。
    """
    if "漢字" not in df.columns:
        raise ValueError("「漢字」列が見つかりません。")

    working_df = df.fillna("").astype(str).copy()
    working_df["漢字"] = working_df["漢字"].str.strip()
    working_df = working_df[working_df["漢字"] != ""]
    working_df = working_df.drop_duplicates(subset=["漢字"], keep="first")

    level_column = "漢検級" if "漢検級" in working_df.columns else "級"
    pair_numbers = find_pair_numbers(working_df.columns)
    registered_kanji = set(working_df["漢字"])

    transforms = {kanji: {} for kanji in working_df["漢字"]}

    for _, row in working_df.iterrows():
        result = row["漢字"]

        for pair_number in pair_numbers:
            first = str(row.get(f"ペア{pair_number}_部品1", "")).strip()
            second = str(row.get(f"ペア{pair_number}_部品2", "")).strip()
            third = str(row.get(f"ペア{pair_number}_部品3", "")).strip()

            if not first or not second:
                continue
            # 現行ゲームJSONは2項変換のため、3部品分解を誤って2部品として出力しない。
            if third:
                continue
            if first not in registered_kanji or second not in registered_kanji:
                continue

            for base, modifier in ((first, second), (second, first)):
                results = transforms[base].setdefault(modifier, [])
                if result not in results:
                    results.append(result)

    kanji_datas = []
    for _, row in working_df.iterrows():
        base_kanji = row["漢字"]
        kanji_transforms = [
            {"modifier": modifier, "results": results}
            for modifier, results in transforms[base_kanji].items()
        ]
        kanji_datas.append(
            {
                "baseKanji": base_kanji,
                "level": level_to_number(row.get(level_column, "")),
                "kanjiTransforms": kanji_transforms,
            }
        )

    return {"kanjiDatas": kanji_datas}


def to_json_text(df):
    """日本語をエスケープせず、見やすく整形したJSON文字列を返す。"""
    return json.dumps(build_kanji_database(df), ensure_ascii=False, indent=2)
