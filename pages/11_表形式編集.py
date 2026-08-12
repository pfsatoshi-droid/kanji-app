import pandas as pd
import streamlit as st

from bulk_editor import prepare_editor_df, validate_editor_df
from data_store import load_df, save_df_to_sheet
from pair_utils import get_pair_numbers


st.set_page_config(page_title="表形式で編集", layout="wide")
st.title("表形式で編集")
st.write("CSVや表計算ソフトのようにセルを直接編集し、まとめて保存できます。行の追加・削除も可能です。")

try:
    source_df = load_df()
except Exception as error:
    st.error("Googleスプレッドシートからの読み込みに失敗しました。")
    st.exception(error)
    st.stop()

existing_pair_count = max(get_pair_numbers(source_df), default=0)
visible_pair_count = st.number_input(
    "表示するペア数",
    min_value=1,
    max_value=20,
    value=max(existing_pair_count, 4),
    step=1,
    help="新しいペアを入力したい場合は、必要な数まで増やしてください。",
)

editor_df = prepare_editor_df(source_df, visible_pair_count=visible_pair_count)

st.caption(
    "部品1・部品2は必須、部品3は任意です。表の最下部から行を追加でき、左端の行メニューから削除できます。"
)

edited_df = st.data_editor(
    editor_df,
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    height=620,
    key="kanji_table_editor",
    column_config={
        "漢字": st.column_config.TextColumn("漢字", width="small", max_chars=1),
        "画数": st.column_config.TextColumn("画数", width="small"),
        "漢検級": st.column_config.SelectboxColumn(
            "漢検級",
            options=["", "10級", "9級", "8級", "7級", "6級", "5級", "4級", "3級", "準2級", "2級", "準1級", "1級"],
            width="small",
        ),
        "メモ": st.column_config.TextColumn("メモ", width="large"),
    },
)

cleaned_df, errors_df = validate_editor_df(edited_df)

source_kanji = set(source_df.get("漢字", pd.Series(dtype=str)).fillna("").astype(str).str.strip()) - {""}
edited_kanji = set(cleaned_df.get("漢字", pd.Series(dtype=str)).fillna("").astype(str).str.strip()) - {""}

col1, col2, col3 = st.columns(3)
col1.metric("保存後の行数", len(cleaned_df), delta=len(cleaned_df) - len(source_df))
col2.metric("追加される漢字", len(edited_kanji - source_kanji))
col3.metric("削除される漢字", len(source_kanji - edited_kanji))

if not errors_df.empty:
    st.error(f"修正が必要な箇所が {len(errors_df)} 件あります。")
    st.dataframe(errors_df, use_container_width=True, hide_index=True)

confirm_save = st.checkbox("表示中の内容でGoogleスプレッドシート全体を更新する")

if st.button(
    "表の内容を一括保存",
    type="primary",
    disabled=not confirm_save or not errors_df.empty,
):
    try:
        save_df_to_sheet(cleaned_df)
    except Exception as error:
        st.error("Googleスプレッドシートへの保存に失敗しました。")
        st.exception(error)
        st.stop()

    st.success(f"{len(cleaned_df)} 行を保存しました。保存前の状態は自動バックアップされています。")
    st.rerun()
