import pandas as pd
import streamlit as st

from jukugo_store import (
    DEFAULT_JUKUGO_COLUMNS,
    INTERNAL_ROW_COLUMN,
    append_jukugo_record,
    delete_jukugo_record,
    load_jukugo_df,
    parse_jukugo_csv,
    save_jukugo_df,
    update_jukugo_record,
)


st.set_page_config(page_title="熟語編集・登録", layout="wide")
st.title("熟語編集・登録")
st.caption("熟語はGoogleスプレッドシート内の別シートで管理します。")


try:
    df = load_jukugo_df()
except Exception as error:
    st.error("熟語シートの読み込みに失敗しました。")
    st.exception(error)
    st.stop()


for column in DEFAULT_JUKUGO_COLUMNS:
    if column not in df.columns:
        df[column] = ""

registered_df = df[df["熟語"].astype(str).str.strip() != ""].copy()

metric1, metric2 = st.columns(2)
metric1.metric("登録熟語数", f"{len(registered_df):,} 件")
metric2.metric("読み登録済み", f"{(registered_df['読み'].astype(str).str.strip() != '').sum():,} 件")

edit_tab, import_tab, list_tab = st.tabs(["編集・登録", "CSV取り込み", "一覧・出力"])


with edit_tab:
    st.subheader("熟語を検索")
    query = st.text_input(
        "熟語",
        placeholder="例：学校",
        help="完全一致する熟語があれば編集し、未登録なら新規追加できます。",
    ).strip()

    candidates = registered_df
    if query:
        candidates = registered_df[
            registered_df["熟語"].astype(str).str.contains(query, regex=False, na=False)
        ].copy()

    selected_row = None
    selected_word = query

    if query and not candidates.empty:
        all_candidate_words = candidates["熟語"].astype(str).tolist()
        candidate_words = all_candidate_words[:200]
        if query in all_candidate_words and query not in candidate_words:
            candidate_words = [query] + candidate_words[:199]
        default_index = candidate_words.index(query) if query in candidate_words else 0
        selected_word = st.selectbox(
            "候補",
            candidate_words,
            index=default_index,
            help="部分一致の候補を最大200件表示します。",
        )
        selected_row = candidates[candidates["熟語"] == selected_word].iloc[0]
    elif query:
        st.info(f"「{query}」は未登録です。新しく追加できます。")
    else:
        st.info("編集・追加したい熟語を入力してください。")

    if query:
        is_existing = selected_row is not None
        current_word = str(selected_row["熟語"]) if is_existing else query
        current_reading = str(selected_row["読み"]) if is_existing else ""
        current_meaning = str(selected_row["意味"]) if is_existing else ""
        current_memo = str(selected_row["メモ"]) if is_existing else ""
        row_key = int(selected_row[INTERNAL_ROW_COLUMN]) if is_existing else "new"

        st.divider()
        st.subheader("登録内容")

        with st.form(f"jukugo_form_{row_key}"):
            word = st.text_input("熟語", value=current_word).strip()
            reading = st.text_input("読み", value=current_reading, placeholder="例：がっこう").strip()
            meaning = st.text_area("意味", value=current_meaning, placeholder="任意").strip()
            memo = st.text_area("メモ", value=current_memo, placeholder="ゲーム内での扱いなど").strip()

            submit_label = "更新する" if is_existing else "追加する"
            submitted = st.form_submit_button(submit_label, type="primary")

        if submitted:
            if not word:
                st.error("熟語を入力してください。")
            else:
                duplicate_rows = registered_df[registered_df["熟語"] == word]
                if is_existing:
                    duplicate_rows = duplicate_rows[
                        duplicate_rows[INTERNAL_ROW_COLUMN] != int(selected_row[INTERNAL_ROW_COLUMN])
                    ]

                if not duplicate_rows.empty:
                    st.error(f"「{word}」はすでに登録されています。")
                else:
                    record = {
                        "熟語": word,
                        "読み": reading,
                        "意味": meaning,
                        "メモ": memo,
                    }
                    try:
                        if is_existing:
                            update_jukugo_record(int(selected_row[INTERNAL_ROW_COLUMN]), record)
                            st.success(f"「{word}」を更新しました。")
                        else:
                            append_jukugo_record(record)
                            st.success(f"「{word}」を追加しました。")
                        st.rerun()
                    except Exception as error:
                        st.error("Googleスプレッドシートへの保存に失敗しました。")
                        st.exception(error)

        if is_existing:
            with st.expander("危険操作：この熟語を削除する"):
                confirmed = st.checkbox(f"「{selected_word}」を削除することを確認しました")
                if st.button("この熟語を削除"):
                    if not confirmed:
                        st.error("削除確認のチェックを入れてください。")
                    else:
                        try:
                            delete_jukugo_record(int(selected_row[INTERNAL_ROW_COLUMN]))
                            st.success(f"「{selected_word}」を削除しました。")
                            st.rerun()
                        except Exception as error:
                            st.error("熟語の削除に失敗しました。")
                            st.exception(error)

    if query and not candidates.empty:
        st.divider()
        st.subheader("検索結果")
        display_columns = [column for column in df.columns if column != INTERNAL_ROW_COLUMN]
        st.write(f"該当件数：{len(candidates):,} 件（先頭200件を表示）")
        st.dataframe(
            candidates[display_columns].head(200),
            use_container_width=True,
            hide_index=True,
        )


with import_tab:
    st.subheader("熟語CSVを取り込む")
    st.write("ヘッダーなしの1列CSVと、先頭列が「熟語」のヘッダー付きCSVに対応しています。")

    uploaded_file = st.file_uploader("CSVファイル", type=["csv"], key="jukugo_csv")

    if uploaded_file is not None:
        try:
            imported_df = parse_jukugo_csv(uploaded_file.getvalue())
        except Exception as error:
            st.error("CSVを読み込めませんでした。")
            st.exception(error)
            st.stop()

        existing_words = set(registered_df["熟語"].astype(str))
        imported_words = set(imported_df["熟語"].astype(str))
        new_count = len(imported_words - existing_words)
        duplicate_count = len(imported_words & existing_words)
        non_two_character_count = int((imported_df["熟語"].str.len() != 2).sum())

        col1, col2, col3 = st.columns(3)
        col1.metric("CSV内の熟語", f"{len(imported_df):,} 件")
        col2.metric("新規候補", f"{new_count:,} 件")
        col3.metric("既存と重複", f"{duplicate_count:,} 件")

        if non_two_character_count:
            st.warning(f"2文字ではない語が {non_two_character_count:,} 件含まれています。")

        st.dataframe(imported_df.head(100), use_container_width=True, hide_index=True)

        import_mode = st.radio(
            "取り込み方法",
            ["既存データに追加（重複は除外）", "熟語シートをCSV内容で置き換える"],
        )

        if import_mode.startswith("既存データ"):
            st.info(f"現在のデータを残し、新しい熟語を最大 {new_count:,} 件追加します。")
        else:
            st.warning("現在の熟語シート全体を置き換えます。読み・意味・メモもCSVの内容になります。")

        confirm_replace = True
        if import_mode.startswith("熟語シート"):
            confirm_replace = st.checkbox("全置換することを確認しました")

        if st.button("CSVを取り込む", type="primary", disabled=not confirm_replace):
            try:
                current_df = registered_df.drop(columns=[INTERNAL_ROW_COLUMN], errors="ignore")

                if import_mode.startswith("既存データ"):
                    target_df = pd.concat([current_df, imported_df], ignore_index=True, sort=False)
                    target_df = target_df.drop_duplicates(subset=["熟語"], keep="first")
                else:
                    target_df = imported_df

                with st.spinner("熟語シートへ書き込んでいます…"):
                    save_jukugo_df(target_df)

                st.success(f"取り込みが完了しました。登録熟語数：{len(target_df):,} 件")
                st.rerun()
            except Exception as error:
                st.error("CSVの取り込みに失敗しました。")
                st.exception(error)


with list_tab:
    st.subheader("熟語一覧")
    list_query = st.text_input(
        "一覧を絞り込む",
        placeholder="熟語・読み・意味・メモから検索",
        key="jukugo_list_query",
    ).strip()

    list_df = registered_df.drop(columns=[INTERNAL_ROW_COLUMN], errors="ignore").copy()

    if list_query:
        searchable_columns = [column for column in DEFAULT_JUKUGO_COLUMNS if column in list_df.columns]
        mask = pd.Series(False, index=list_df.index)
        for column in searchable_columns:
            mask |= list_df[column].astype(str).str.contains(list_query, regex=False, na=False)
        list_df = list_df[mask]

    st.write(f"該当件数：{len(list_df):,} 件（画面には先頭500件を表示）")
    st.dataframe(list_df.head(500), use_container_width=True, hide_index=True)

    csv_bytes = list_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        "表示中の熟語をCSVでダウンロード",
        data=csv_bytes,
        file_name="jukugo_database.csv",
        mime="text/csv",
    )
