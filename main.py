import streamlit as st
from data_store import load_df

st.set_page_config(page_title="漢字データベース管理アプリ", layout="wide")

st.title("漢字データベース管理アプリ")

st.write(
    """
    このアプリでは、漢字データベースの登録・編集・取り込み・チェック・削除を行えます。
    
    左のサイドバーから使いたい機能を選んでください。
    """
)

st.divider()

st.subheader("現在のデータベース状況")

try:
    df = load_df()

    st.success("Googleスプレッドシートからデータを読み込みました。")
    st.write(f"登録行数：{len(df)} 件")

    if "漢字" in df.columns:
        registered_count = df["漢字"].dropna().astype(str).str.strip()
        registered_count = registered_count[registered_count != ""]
        st.write(f"登録漢字数：{len(registered_count)} 件")

    st.dataframe(df.head(20), use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Googleスプレッドシートの読み込みに失敗しました。")
    st.exception(e)

st.divider()

st.subheader("機能一覧")

st.markdown(
    """
    - **編集登録**：漢字情報・部品ペアを1件ずつ登録、編集、削除
    - **一括追加**：同じ画数・漢検級の漢字をまとめて追加
    - **CSV取り込み**：既存CSVから部品ペアをまとめて取り込み
    - **漢字チェック**：外部リストとデータベースの差分確認
    - **行削除**：漢字指定・行番号指定で行を削除
    - **TSVをCSVに変換**：データをCSV形式で出力
    """
)
