from datetime import datetime

import streamlit as st

from jukugo_json_export import (
    build_jukugo_database,
    get_jukugo_export_stats,
    jukugo_to_json_text,
)
from jukugo_store import load_jukugo_df


st.set_page_config(page_title="熟語JSON出力", layout="wide")

st.title("熟語JSON出力")
st.write(
    """
    Googleスプレッドシートの「熟語」シートを直接読み込み、
    2文字を昇順に並べたキーで熟語をまとめたJSONを出力します。

    例：「一同」と「同一」は、どちらも `key: "一同"` にまとめられます。
    """
)

try:
    df = load_jukugo_df()
    database = build_jukugo_database(df)
    stats = get_jukugo_export_stats(df)
    json_text = jukugo_to_json_text(df)
except Exception as error:
    st.error("熟語JSONデータの作成に失敗しました。")
    st.exception(error)
    st.stop()

col1, col2, col3, col4 = st.columns(4)
col1.metric("登録熟語数", f"{stats['registered_count']:,} 件")
col2.metric("出力熟語数", f"{stats['exported_word_count']:,} 件")
col3.metric("キー数", f"{stats['key_count']:,} 件")
col4.metric("2文字以外で除外", f"{stats['skipped_count']:,} 件")

st.success(
    f"{stats['exported_word_count']:,} 件の熟語を "
    f"{stats['key_count']:,} 個のキーにまとめました。"
)

st.subheader("出力内容のプレビュー")
preview = {"datas": database["datas"][:20]}
st.json(preview, expanded=2)

if len(database["datas"]) > 20:
    st.caption(
        "画面には先頭20キーだけ表示しています。"
        "ダウンロードされるJSONには全件が含まれます。"
    )

st.divider()
st.subheader("JSONとして保存")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
default_filename = f"JukugoDataBase_All_{timestamp}.json"

st.download_button(
    label="熟語JSONをダウンロード",
    data=json_text,
    file_name=default_filename,
    mime="application/json",
)
