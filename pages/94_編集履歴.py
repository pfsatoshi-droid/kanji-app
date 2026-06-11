import streamlit as st
import pandas as pd
from data_store import load_history_df

st.set_page_config(page_title="編集履歴", layout="wide")

st.title("編集履歴")

st.write(
    """
    アプリからGoogleスプレッドシートに保存された変更履歴を表示します。
    """
)

try:
    history_df = load_history_df()
except Exception as e:
    st.error("編集履歴の読み込みに失敗しました。")
    st.exception(e)
    st.stop()

if history_df.empty:
    st.info("まだ編集履歴はありません。")
    st.stop()

# 必要な列がない場合に備える
for col in ["timestamp", "action", "kanji", "field", "before", "after"]:
    if col not in history_df.columns:
        history_df[col] = ""

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("履歴件数", len(history_df))
with col2:
    st.metric("対象漢字数", history_df["kanji"].astype(str).str.strip().replace("", pd.NA).dropna().nunique())
with col3:
    st.metric("操作種類", history_df["action"].astype(str).str.strip().replace("", pd.NA).dropna().nunique())

st.divider()

# =========================
# フィルター
# =========================
st.subheader("絞り込み")

col1, col2, col3 = st.columns(3)

with col1:
    actions = ["すべて"] + sorted([x for x in history_df["action"].unique().tolist() if x != ""])
    selected_action = st.selectbox("操作", actions)

with col2:
    kanji_query = st.text_input("漢字で検索", placeholder="例：阪")

with col3:
    field_query = st.text_input("列名で検索", placeholder="例：メモ, 画数, ペア1_部品1")

filtered_df = history_df.copy()

if selected_action != "すべて":
    filtered_df = filtered_df[filtered_df["action"] == selected_action]

if kanji_query.strip():
    q = kanji_query.strip()
    filtered_df = filtered_df[filtered_df["kanji"].astype(str).str.contains(q, na=False)]

if field_query.strip():
    q = field_query.strip()
    filtered_df = filtered_df[filtered_df["field"].astype(str).str.contains(q, na=False)]

# 新しい順に表示
if "timestamp" in filtered_df.columns:
    filtered_df = filtered_df.sort_values("timestamp", ascending=False)

st.write(f"表示件数：{len(filtered_df)} 件")

st.dataframe(filtered_df, use_container_width=True, hide_index=True)

# =========================
# CSVダウンロード
# =========================
st.divider()

csv_data = filtered_df.to_csv(index=False, encoding="utf-8-sig")

st.download_button(
    label="表示中の履歴をCSVでダウンロード",
    data=csv_data,
    file_name="kanji_edit_history.csv",
    mime="text/csv",
)

st.caption(
    "注意：この履歴は、履歴機能を追加した後にアプリ経由で保存された変更から記録されます。"
)
