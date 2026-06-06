import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import shutil

DATA_PATH = Path("kanji.tsv")
BACKUP_DIR = Path("backups")

st.set_page_config(page_title="漢字DB バックアップアプリ", layout="wide")

st.title("漢字DB バックアップアプリ")

BACKUP_DIR.mkdir(exist_ok=True)

# =========================
# 現在のDB確認
# =========================
st.subheader("現在のデータベース")

if DATA_PATH.exists():
    df = pd.read_csv(DATA_PATH, sep="\t", dtype=str).fillna("")
    st.success("kanji.tsv が見つかりました。")
    st.write(f"現在の登録行数：{len(df)} 件")
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.error("kanji.tsv が見つかりません。")
    st.stop()

# =========================
# バックアップ作成
# =========================
st.divider()
st.subheader("バックアップを作成")

if st.button("今すぐバックアップを作成", type="primary"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"kanji_backup_{timestamp}.tsv"

    shutil.copy2(DATA_PATH, backup_path)

    st.success(f"バックアップを作成しました：{backup_path}")

# =========================
# バックアップ一覧
# =========================
st.divider()
st.subheader("バックアップ一覧")

backup_files = sorted(
    BACKUP_DIR.glob("kanji_backup_*.tsv"),
    reverse=True
)

if not backup_files:
    st.info("まだバックアップはありません。")
else:
    backup_names = [file.name for file in backup_files]

    selected_backup_name = st.selectbox(
        "確認・復元するバックアップを選択",
        backup_names
    )

    selected_backup_path = BACKUP_DIR / selected_backup_name

    st.write(f"選択中：{selected_backup_name}")

    backup_df = pd.read_csv(selected_backup_path, sep="\t", dtype=str).fillna("")

    st.write(f"バックアップ内の登録行数：{len(backup_df)} 件")
    st.dataframe(backup_df, use_container_width=True, hide_index=True)

    # =========================
    # ダウンロード
    # =========================
    st.divider()
    st.subheader("バックアップをダウンロード")

    with open(selected_backup_path, "rb") as f:
        st.download_button(
            label="選択したバックアップをダウンロード",
            data=f,
            file_name=selected_backup_name,
            mime="text/tab-separated-values"
        )

    # =========================
    # 復元
    # =========================
    st.divider()
    st.subheader("バックアップから復元")

    st.warning("復元すると、現在の kanji.tsv は選択したバックアップの内容で上書きされます。")

    confirm_restore = st.checkbox("このバックアップから復元することを確認しました")

    if st.button("選択したバックアップから復元"):
        if confirm_restore:
            # 復元前にも自動バックアップを作る
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            before_restore_path = BACKUP_DIR / f"kanji_before_restore_{timestamp}.tsv"
            shutil.copy2(DATA_PATH, before_restore_path)

            shutil.copy2(selected_backup_path, DATA_PATH)

            st.success("復元しました。")
            st.info(f"復元前の状態も保存しました：{before_restore_path}")
            st.rerun()
        else:
            st.error("復元するには確認チェックを入れてください。")