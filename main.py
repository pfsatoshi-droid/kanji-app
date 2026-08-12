import pandas as pd
import streamlit as st

from app_ui import apply_app_style, feature_card, page_header
from data_store import load_df
from pair_utils import get_pair_numbers


st.set_page_config(page_title="Kanji Studio", page_icon="字", layout="wide")
apply_app_style()
page_header(
    "漢字データベース",
    "登録・品質確認・ゲーム用データ出力を、ひとつの場所で管理します。",
)

try:
    df = load_df().fillna("")
except Exception as error:
    st.error("Googleスプレッドシートに接続できませんでした。設定を確認してから再読み込みしてください。")
    with st.expander("エラーの詳細"):
        st.exception(error)
    st.stop()

kanji = df.get("漢字", pd.Series(dtype=str)).astype(str).str.strip()
registered_count = int(kanji.ne("").sum())
pair_numbers = get_pair_numbers(df)
pair_count = 0
three_part_count = 0
review_count = 0
incomplete_count = 0

for _, row in df.iterrows():
    for number in pair_numbers:
        parts = [str(row.get(f"ペア{number}_部品{i}", "")).strip() for i in (1, 2, 3)]
        review = str(row.get(f"ペア{number}_審議", "")).strip()
        reason = str(row.get(f"ペア{number}_審議理由", "")).strip()
        if any(parts):
            pair_count += 1
            three_part_count += int(bool(parts[2]))
            incomplete_count += int(not parts[0] or not parts[1])
        if review == "TRUE" or reason:
            review_count += 1

metric_columns = st.columns(4)
metric_columns[0].metric("登録漢字", f"{registered_count:,} 字")
metric_columns[1].metric("分解候補", f"{pair_count:,} 件")
metric_columns[2].metric("3部品分解", f"{three_part_count:,} 件")
metric_columns[3].metric("要審議", f"{review_count:,} 件")

if incomplete_count:
    st.warning(f"部品1・部品2が揃っていない分解候補が {incomplete_count} 件あります。品質管理画面で確認してください。")

st.markdown('<div class="ks-section-label">よく使う操作</div>', unsafe_allow_html=True)
action_columns = st.columns(3)
with action_columns[0]:
    feature_card("表形式でまとめて編集", "PCでの大量更新向け。並び替えや審議項目の表示切替にも対応します。")
    st.page_link("pages/11_表形式編集.py", label="表形式編集を開く", icon="🧾", use_container_width=True)
with action_columns[1]:
    feature_card("1文字ずつ丁寧に編集", "スマホにも適した個別画面で、漢字情報と分解候補を編集します。")
    st.page_link("pages/1_編集登録.py", label="個別編集を開く", icon="✏️", use_container_width=True)
with action_columns[2]:
    feature_card("ゲーム用JSONを出力", "新形式と旧ゲーム互換形式を選んでダウンロードできます。")
    st.page_link("pages/41_JSON出力.py", label="JSON出力を開く", icon="📦", use_container_width=True)

st.markdown('<div class="ks-section-label">品質管理</div>', unsafe_allow_html=True)
quality_columns = st.columns(3)
with quality_columns[0]:
    feature_card("審議中の分解", f"現在 {review_count} 件。判断が必要な候補をまとめて確認します。")
    st.page_link("pages/3_審議ペア一覧.py", label="審議一覧を開く", icon="🔎", use_container_width=True)
with quality_columns[1]:
    feature_card("漢字リスト照合", "外部リストとデータベースを比較し、過不足を見つけます。")
    st.page_link("pages/92_漢字チェック.py", label="漢字チェックを開く", icon="✓", use_container_width=True)
with quality_columns[2]:
    feature_card("バックアップと履歴", "保存前の状態や過去の変更を確認し、安全に運用します。")
    st.page_link("pages/5_バックアップ.py", label="バックアップを開く", icon="🕘", use_container_width=True)

with st.expander("データのプレビュー"):
    preview_columns = [column for column in ["漢字", "画数", "漢検級"] if column in df.columns]
    st.dataframe(df[preview_columns].head(20), use_container_width=True, hide_index=True)
