import json
from collections import defaultdict

import pandas as pd


def make_sorted_jukugo_key(word: str) -> str:
    """
    2文字熟語の文字を昇順に並べ、順序に依存しない辞書キーを作る。

    C#:
        return (a <= b) ? new string(new[] { a, b })
                        : new string(new[] { b, a });
    と同じ考え方。
    """
    value = str(word).strip()
    if len(value) != 2:
        raise ValueError("熟語は2文字である必要があります。")

    first, second = value[0], value[1]
    return value if first <= second else second + first


def build_jukugo_database(df: pd.DataFrame) -> dict:
    """
    「熟語」列からゲーム用の熟語辞書を作る。

    - 2文字の語だけを出力
    - 同じ熟語の重複を除外
    - 文字順を入れ替えた語は同じkeyにまとめる
    - keyとvaluesは昇順で固定し、毎回同じJSONになるようにする
    """
    if "熟語" not in df.columns:
        raise ValueError("「熟語」列が見つかりません。")

    words = (
        df["熟語"]
        .fillna("")
        .astype(str)
        .str.strip()
    )
    words = words[words != ""].drop_duplicates()

    groups = defaultdict(list)

    for word in words:
        if len(word) != 2:
            continue

        key = make_sorted_jukugo_key(word)
        groups[key].append(word)

    datas = [
        {
            "key": key,
            "values": sorted(set(groups[key])),
        }
        for key in sorted(groups)
    ]

    return {"datas": datas}


def get_jukugo_export_stats(df: pd.DataFrame) -> dict:
    """画面表示用の件数を返す。"""
    if "熟語" not in df.columns:
        raise ValueError("「熟語」列が見つかりません。")

    words = (
        df["熟語"]
        .fillna("")
        .astype(str)
        .str.strip()
    )
    words = words[words != ""]
    unique_words = words.drop_duplicates()
    two_character_words = unique_words[unique_words.str.len() == 2]

    database = build_jukugo_database(df)

    return {
        "registered_count": int(len(unique_words)),
        "exported_word_count": int(len(two_character_words)),
        "key_count": int(len(database["datas"])),
        "skipped_count": int(len(unique_words) - len(two_character_words)),
    }


def jukugo_to_json_text(df: pd.DataFrame) -> str:
    """日本語をエスケープせず、整形したJSON文字列を返す。"""
    return json.dumps(
        build_jukugo_database(df),
        ensure_ascii=False,
        indent=2,
    )
