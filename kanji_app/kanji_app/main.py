import streamlit as st
import pandas as pd
from pathlib import Path

DATA_PATH = Path("kanji.tsv")
BACKUP_DIR = Path("backups")

st.set_page_config(page_title="漢字データベース管理アプリ", layout="wide")

st.title("漢字データベース管理アプリ")

st.write(
    """
    このアプリでは、漢字データベースの登録・編集・取り込み・バックアップ・チェック・削除を行えます。
    
    左のサイドバーから使いたい機能を選んでください。
    """
)

st.divider()

st.subheader("現在のデータベース状況")

if DATA_PATH.exists():
    df = pd.read_csv(DATA_PATH, sep="\t", dtype=str).fillna("")

    st.success("kanji.tsv が見つかりました。")
    st.write(f"登録行数：{len(df)} 件")

    if "漢字" in df.columns:
        registered_count = df["漢字"].dropna().astype(str).str.strip()
        registered_count = registered_count[registered_count != ""]
        st.write(f"登録漢字数：{len(registered_count)} 件")

    st.dataframe(df.head(20), use_container_width=True, hide_index=True)

else:
    st.warning("kanji.tsv がまだありません。編集登録ページや一括追加ページから作成できます。")

st.divider()

st.subheader("機能一覧")

st.markdown(
    """
    - **編集登録**：漢字情報・部品ペアを1件ずつ登録、編集、削除
    - **一括追加**：同じ画数・漢検級の漢字をまとめて追加
    - **CSV取り込み**：既存CSVから部品ペアをまとめて取り込み
    - **バックアップ**：kanji.tsv のバックアップ作成・復元
    - **漢字チェック**：外部リストと kanji.tsv の差分確認
    - **行削除**：漢字指定・行番号指定で行を削除
    """
)

st.info("起動はこの main.py だけでOKです。")