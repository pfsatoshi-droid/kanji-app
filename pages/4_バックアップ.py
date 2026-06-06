import streamlit as st
import pandas as pd
from datetime import datetime
from data_store import load_df, save_df_to_sheet

st.set_page_config(page_title="漢字DB バックアップアプリ", layout="wide")

st.title("漢字DB バックアップアプリ")

st.info(
    "現在は Googleスプレッドシートをデータ保存先にしています。"
    "このページでは、現在のデータをTSV/CSVとしてダウンロードしたり、"
    "バックアップファイルからスプレッドシートへ復元したりできます。"
)

# =========================
# 現在のDB確認
# =========================
st.subheader("現在のデータベース")

try:
    df = load_df()
except Exception as e:
    st.error("Googleスプレッドシートからの読み込みに失敗しました。")
    st.exception(e)
    st.stop()

st.success("Googleスプレッドシートからデータを読み込みました。")
st.write(f"現在の登録行数：{len(df)} 件")
st.dataframe(df, use_container_width=True, hide_index=True)

# =========================
# バックアップダウンロード
# =========================
st.divider()
st.subheader("バックアップをダウンロード")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

tsv_data = df.to_csv(sep="\t", index=False).encode("utf-8-sig")
csv_data = df.to_csv(index=False).encode("utf-8-sig")

col1, col2 = st.columns(2)

with col1:
    st.download_button(
        label="TSVでダウンロード",
        data=tsv_data,
        file_name=f"kanji_backup_{timestamp}.tsv",
        mime="text/tab-separated-values",
    )

with col2:
    st.download_button(
        label="CSVでダウンロード",
        data=csv_data,
        file_name=f"kanji_backup_{timestamp}.csv",
        mime="text/csv",
    )

st.caption("通常はTSVがおすすめです。Excelで扱いたい場合はCSVでもOKです。")

# =========================
# バックアップから復元
# =========================
st.divider()
st.subheader("バックアップファイルから復元")

st.warning(
    "復元すると、現在のGoogleスプレッドシートの内容がアップロードしたファイルの内容で上書きされます。"
)

uploaded_file = st.file_uploader(
    "復元に使うバックアップファイルを選択してください",
    type=["tsv", "csv"],
)

def read_uploaded_table(uploaded_file):
    file_name = uploaded_file.name.lower()

    encodings = ["utf-8-sig", "utf-8", "cp932"]

    if file_name.endswith(".tsv"):
        sep = "\t"
    else:
        sep = ","

    for enc in encodings:
        try:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, sep=sep, dtype=str, encoding=enc).fillna("")
        except Exception:
            pass

    raise ValueError("ファイルを読み込めませんでした。文字コードや形式を確認してください。")

if uploaded_file is not None:
    try:
        restore_df = read_uploaded_table(uploaded_file)

        st.write("復元予定データのプレビュー")
        st.write(f"復元予定の行数：{len(restore_df)} 件")
        st.dataframe(restore_df.head(50), use_container_width=True, hide_index=True)

        required_cols = ["漢字", "画数", "漢検級", "メモ"]
        missing_cols = [c for c in required_cols if c not in restore_df.columns]

        if missing_cols:
            st.error(f"必要な列がありません：{', '.join(missing_cols)}")
            st.stop()

        confirm_restore = st.checkbox(
            "現在のGoogleスプレッドシートを、このファイルの内容で上書きすることを確認しました"
        )

        if st.button("このバックアップから復元", type="primary"):
            if not confirm_restore:
                st.error("復元するには確認チェックを入れてください。")
            else:
                try:
                    save_df_to_sheet(restore_df)
                    st.success("Googleスプレッドシートへ復元しました。")
                    st.rerun()
                except Exception as e:
                    st.error("Googleスプレッドシートへの復元に失敗しました。")
                    st.exception(e)

    except Exception as e:
        st.error("バックアップファイルの読み込み中にエラーが起きました。")
        st.exception(e)

# =========================
# 補足
# =========================
st.divider()
st.subheader("補足")

st.write(
    "Googleスプレッドシート自体にも変更履歴があります。"
    "大きな編集やCSV取り込みの前には、このページからTSVバックアップをダウンロードしておくと安全です。"
)
