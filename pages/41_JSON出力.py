from datetime import datetime

import streamlit as st

from data_store import load_df
from json_export import build_kanji_database, to_json_text


st.set_page_config(page_title="JSON出力", layout="wide")

st.title("JSON出力")
st.write(
    """
    Googleスプレッドシート上の全漢字を読み込み、
    漢字と部品の組み合わせをゲーム用JSONとして出力します。
    漢検級による絞り込みは行いません。
    """
)

try:
    df = load_df()
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

st.success(
    f"全 {len(kanji_datas)} 字、組み合わせ {transform_count} 件のJSONを作成しました。"
)

st.subheader("出力内容のプレビュー")
st.json({"kanjiDatas": kanji_datas[:5]}, expanded=2)
if len(kanji_datas) > 5:
    st.caption("画面には先頭5字のみ表示しています。ダウンロードには全件が含まれます。")

st.divider()
st.subheader("JSONとして保存")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
default_filename = f"KanjiDataBase_All_{timestamp}.json"

st.download_button(
    label="JSONをダウンロード",
    data=json_data,
    file_name=default_filename,
    mime="application/json",
)
