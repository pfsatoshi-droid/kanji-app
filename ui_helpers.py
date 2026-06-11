import pandas as pd
import streamlit as st

from data_store import make_history_records


FLASH_KEY = "kanji_app_flash"


def set_flash(message, level="success"):
    st.session_state[FLASH_KEY] = {
        "message": message,
        "level": level,
    }


def show_flash():
    flash = st.session_state.pop(FLASH_KEY, None)

    if not flash:
        return

    level = flash.get("level", "success")
    message = flash.get("message", "")

    if level == "warning":
        st.warning(message)
    elif level == "error":
        st.error(message)
    elif level == "info":
        st.info(message)
    else:
        st.success(message)


def count_registered_kanji(df):
    if "漢字" not in df.columns:
        return 0

    kanji = df["漢字"].dropna().astype(str).str.strip()
    return len(kanji[kanji != ""])


def count_pair_cells(df):
    pair_cols = [
        col
        for col in df.columns
        if col.startswith("ペア") and (col.endswith("_部品1") or col.endswith("_部品2"))
    ]

    if not pair_cols:
        return 0

    return int((df[pair_cols].astype(str).apply(lambda col: col.str.strip()) != "").sum().sum())


def count_review_pairs(df):
    review_cols = [col for col in df.columns if col.startswith("ペア") and col.endswith("_審議")]
    reason_cols = [col for col in df.columns if col.startswith("ペア") and col.endswith("_審議理由")]

    review_count = 0

    for col in review_cols:
        review_count += int((df[col].astype(str).str.strip() == "TRUE").sum())

    for col in reason_cols:
        review_count += int((df[col].astype(str).str.strip() != "").sum())

    return review_count


def show_database_status(df):
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("登録行数", len(df))
    with col2:
        st.metric("登録漢字数", count_registered_kanji(df))
    with col3:
        st.metric("部品入力数", count_pair_cells(df))
    with col4:
        st.metric("審議中", count_review_pairs(df))


def build_change_records(before_df, after_df):
    records = make_history_records(before_df, after_df)

    return pd.DataFrame(
        records,
        columns=["timestamp", "action", "kanji", "field", "before", "after"],
    )


def show_change_summary(before_df, after_df, title="保存前の変更確認"):
    change_df = build_change_records(before_df, after_df)

    st.subheader(title)

    if change_df.empty:
        st.info("保存対象の変更はありません。")
        return False

    added = int((change_df["action"] == "追加").sum())
    updated = int((change_df["action"] == "更新").sum())
    deleted = int((change_df["action"] == "削除").sum())

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("追加", added)
    with col2:
        st.metric("更新", updated)
    with col3:
        st.metric("削除", deleted)
    with col4:
        st.metric("変更項目", len(change_df))

    with st.expander("変更内容を表示", expanded=False):
        st.dataframe(
            change_df[["action", "kanji", "field", "before", "after"]],
            use_container_width=True,
            hide_index=True,
        )

    return True
