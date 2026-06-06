import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

DATA_PATH = Path("kanji.tsv")

st.set_page_config(page_title="TSVをCSVに変換", layout="wide")

st.title("TSVをCSVに変換")

st.write(
    """
    `kanji.tsv` を読み込み、列名を英語形式に変換してCSVとして出力します。
    """
)

# =========================
# データ読み込み
# =========================
if not DATA_PATH.exists():
    st.error("kanji.tsv が見つかりません。")
    st.stop()

df = pd.read_csv(DATA_PATH, sep="\t", dtype=str).fillna("")

st.success(f"kanji.tsv を読み込みました。行数：{len(df)} 件")

st.subheader("変換前プレビュー")
st.dataframe(df.head(20), use_container_width=True, hide_index=True)

# =========================
# 変換設定
# =========================
st.divider()
st.subheader("変換設定")

max_pairs = st.number_input(
    "出力するペア数",
    min_value=1,
    max_value=20,
    value=4,
    step=1
)

include_memo = st.checkbox("メモ列も出力する", value=True)

sort_output = st.checkbox(
    "CSV出力時にソートする",
    value=False
)

convert_level_to_number = st.checkbox(
    "漢検級を数字に変換して出力する",
    value=False
)

if sort_output:
    st.caption("ソート順：漢検級 → 画数 → 漢字")

if convert_level_to_number:
    st.caption("漢検級の変換例：10級→10、準2級→2.5、2級→2、準1級→1.5、1級→1")

st.caption("標準では st1_first, st1_second 〜 st4_first, st4_second まで出力します。")

# =========================
# 変換用関数
# =========================
def level_to_number(level):
    """
    漢検級を数値に変換する。
    10級 -> 10
    準2級 -> 2.5
    2級 -> 2
    準1級 -> 1.5
    1級 -> 1
    """

    mapping = {
        "10級": 10,
        "9級": 9,
        "8級": 8,
        "7級": 7,
        "6級": 6,
        "5級": 5,
        "4級": 4,
        "3級": 3,
        "準2級": 2.5,
        "2級": 2,
        "準1級": 1.5,
        "1級": 1,
    }

    if pd.isna(level):
        return ""

    level = str(level).strip()

    if level == "":
        return ""

    return mapping.get(level, level)


def level_sort_order(level):
    """
    ソート用の順序。
    10級 → 9級 → ... → 2級 → 準1級 → 1級
    の順に並べる。
    """

    mapping = {
        "10級": 1,
        "9級": 2,
        "8級": 3,
        "7級": 4,
        "6級": 5,
        "5級": 6,
        "4級": 7,
        "3級": 8,
        "準2級": 9,
        "2級": 10,
        "準1級": 11,
        "1級": 12,
        10: 1,
        9: 2,
        8: 3,
        7: 4,
        6: 5,
        5: 6,
        4: 7,
        3: 8,
        2.5: 9,
        2: 10,
        1.5: 11,
        1: 12,
        "10": 1,
        "9": 2,
        "8": 3,
        "7": 4,
        "6": 5,
        "5": 6,
        "4": 7,
        "3": 8,
        "2.5": 9,
        "2": 10,
        "1.5": 11,
        "1": 12,
    }

    if pd.isna(level):
        return 999

    level = str(level).strip()

    if level == "":
        return 999

    return mapping.get(level, 999)


def convert_df(df, max_pairs=4, include_memo=True, convert_level_to_number=False):
    out = pd.DataFrame()

    # 基本列
    out["kanji"] = df["漢字"] if "漢字" in df.columns else ""

    # 画数
    if "画数" in df.columns:
        out["strokes"] = df["画数"]
    else:
        out["strokes"] = ""

    # 漢検級
    if "漢検級" in df.columns:
        level_series = df["漢検級"]
    elif "級" in df.columns:
        level_series = df["級"]
    else:
        level_series = pd.Series([""] * len(df))

    if convert_level_to_number:
        out["taisyou"] = level_series.apply(level_to_number)
    else:
        out["taisyou"] = level_series

    # メモ
    if include_memo:
        if "メモ" in df.columns:
            out["memo"] = df["メモ"]
        else:
            out["memo"] = ""

    # 部品ペア
    for i in range(1, max_pairs + 1):
        src_first = f"ペア{i}_部品1"
        src_second = f"ペア{i}_部品2"

        dst_first = f"st{i}_first"
        dst_second = f"st{i}_second"

        if src_first in df.columns:
            out[dst_first] = df[src_first]
        else:
            out[dst_first] = ""

        if src_second in df.columns:
            out[dst_second] = df[src_second]
        else:
            out[dst_second] = ""

    return out


def sort_converted_df(df):
    """
    CSV出力用に並び替える。
    優先度：
    1. 漢検級 taisyou
    2. 画数 strokes
    3. 漢字 kanji
    """

    sorted_df = df.copy()

    # 級の並び順
    sorted_df["_level_order"] = sorted_df["taisyou"].apply(level_sort_order)

    # 画数を数値に変換
    sorted_df["_strokes_num"] = pd.to_numeric(
        sorted_df["strokes"],
        errors="coerce"
    ).fillna(999)

    # 漢字も最後の安定ソートに使う
    sorted_df = sorted_df.sort_values(
        by=["_level_order", "_strokes_num", "kanji"],
        ascending=[True, True, True]
    )

    sorted_df = sorted_df.drop(columns=["_level_order", "_strokes_num"])

    return sorted_df.reset_index(drop=True)


# =========================
# 変換実行
# =========================
converted_df = convert_df(
    df,
    max_pairs=max_pairs,
    include_memo=include_memo,
    convert_level_to_number=convert_level_to_number
)

if sort_output:
    converted_df = sort_converted_df(converted_df)

# =========================
# 変換後プレビュー
# =========================
st.divider()
st.subheader("変換後プレビュー")

if sort_output:
    st.info("現在のプレビューは、漢検級 → 画数 → 漢字 の順でソートされています。")
else:
    st.info("現在のプレビューは、kanji.tsv の元の順番です。")

if convert_level_to_number:
    st.info("漢検級は数字に変換されています。例：10級→10、準2級→2.5、準1級→1.5")
else:
    st.info("漢検級は元の表記のままです。")

st.dataframe(converted_df.head(50), use_container_width=True, hide_index=True)

# =========================
# CSVダウンロード
# =========================
st.divider()
st.subheader("CSVとして保存")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

filename_parts = ["kanji_converted"]

if sort_output:
    filename_parts.append("sorted")

if convert_level_to_number:
    filename_parts.append("levelnum")

default_filename = "_".join(filename_parts) + f"_{timestamp}.csv"

csv_data = converted_df.to_csv(index=False, encoding="utf-8-sig")

st.download_button(
    label="変換したCSVをダウンロード",
    data=csv_data,
    file_name=default_filename,
    mime="text/csv"
)

# =========================
# 任意でローカル保存
# =========================
st.divider()
st.subheader("ローカルにも保存する")

default_save_parts = ["kanji_converted"]

if sort_output:
    default_save_parts.append("sorted")

if convert_level_to_number:
    default_save_parts.append("levelnum")

default_save_name = "_".join(default_save_parts) + ".csv"

save_name = st.text_input(
    "保存ファイル名",
    value=default_save_name
)

if st.button("kanji_app フォルダにCSVを保存"):
    if not save_name.endswith(".csv"):
        save_name += ".csv"

    save_path = Path(save_name)
    converted_df.to_csv(save_path, index=False, encoding="utf-8-sig")

    st.success(f"保存しました：{save_path}")