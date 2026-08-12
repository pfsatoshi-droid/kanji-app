from datetime import datetime

import streamlit as st

from app_ui import apply_app_style, page_header
from data_store import load_df
from json_export import (
    build_kanji_database,
    build_kanji_database_v2,
    to_json_text,
    to_json_text_v2,
)


st.set_page_config(page_title="JSON出力", layout="wide")
apply_app_style()
page_header("ゲーム用JSONを出力", "新しいゲーム向け形式と、旧バージョン互換形式を選んで書き出します。", "データ出力")

output_format = st.radio(
    "形式を選択",
    ["新形式（2・3部品対応）", "旧ゲーム互換形式（2部品のみ）"],
    help="旧形式は既存ゲームとの互換性を保ちます。新形式はmodifiers配列・画数・小数の級に対応します。",
)

try:
    df = load_df()
    if output_format.startswith("新形式"):
        json_database = build_kanji_database_v2(df)
        json_data = to_json_text_v2(df)
    else:
        json_database = build_kanji_database(df)
        json_data = to_json_text(df)
except Exception as e:
    st.error("JSONデータの作成に失敗しました。")
    st.exception(e)
    st.stop()

kanji_datas = json_database["kanjiDatas"]
transform_count = sum(
    len(item["kanjiTransforms"])
    for item in kanji_datas
)
third_part_columns = [column for column in df.columns if str(column).endswith("_部品3")]
three_part_count = sum(
    df[column].fillna("").astype(str).str.strip().ne("").sum()
    for column in third_part_columns
)

st.success(
    f"全 {len(kanji_datas)} 字、組み合わせ {transform_count} 件のJSONを作成しました。"
)
if three_part_count and output_format.startswith("旧ゲーム互換形式"):
    st.info(
        f"3部品の分解 {three_part_count} 件は保存されていますが、"
        "旧ゲーム互換形式は2部品のみのため、この出力には含めていません。"
    )

st.subheader("内容を確認")
st.json({"kanjiDatas": kanji_datas[:5]}, expanded=2)
if len(kanji_datas) > 5:
    st.caption("画面には先頭5字のみ表示しています。ダウンロードには全件が含まれます。")

st.divider()
st.subheader("ダウンロード")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
format_suffix = "v2" if output_format.startswith("新形式") else "legacy"
default_filename = f"KanjiDataBase_All_{format_suffix}_{timestamp}.json"

st.download_button(
    label="JSONをダウンロード",
    data=json_data,
    file_name=default_filename,
    mime="application/json",
)
