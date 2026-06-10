import streamlit as st
import pandas as pd
from data_store import load_df, save_df_to_sheet

st.set_page_config(page_title="審議ペア一覧", layout="wide")

st.title("審議ペア一覧")

st.write(
    """
    シート1に登録されている部品ペアのうち、
    審議対象になっているものだけを一覧表示します。
    """
)


# =========================
# データ読み込み
# =========================
try:
    df = load_df()
except Exception as e:
    st.error("Googleスプレッドシートからの読み込みに失敗しました。")
    st.exception(e)
    st.stop()

original_df = df.copy(deep=True)

if "漢字" not in df.columns:
    st.error("データベースに『漢字』列がありません。")
    st.stop()


# =========================
# 便利関数
# =========================
def get_pair_numbers(df):
    nums = []
    for col in df.columns:
        if col.startswith("ペア") and col.endswith("_部品1"):
            num = col.replace("ペア", "").replace("_部品1", "")
            if num.isdigit():
                nums.append(int(num))
    return sorted(nums)


def build_review_pairs_df(df):
    records = []

    pair_nums = get_pair_numbers(df)

    for row_index, row in df.iterrows():
        kanji = str(row.get("漢字", "")).strip()

        if kanji == "":
            continue

        strokes = str(row.get("画数", "")).strip()
        kanken_level = str(row.get("漢検級", "")).strip()
        memo = str(row.get("メモ", "")).strip()

        for n in pair_nums:
            part1 = str(row.get(f"ペア{n}_部品1", "")).strip()
            part2 = str(row.get(f"ペア{n}_部品2", "")).strip()
            review = str(row.get(f"ペア{n}_審議", "")).strip()
            reason = str(row.get(f"ペア{n}_審議理由", "")).strip()

            if part1 == "" and part2 == "":
                continue

            if review == "TRUE" or reason != "":
                records.append(
                    {
                        "df_index": row_index,
                        "スプレッドシート行": row_index + 2,
                        "漢字": kanji,
                        "画数": strokes,
                        "漢検級": kanken_level,
                        "ペア番号": n,
                        "部品1": part1,
                        "部品2": part2,
                        "審議": "TRUE" if review == "TRUE" else "",
                        "審議理由": reason,
                        "メモ": memo,
                    }
                )

    if records:
        return pd.DataFrame(records)

    return pd.DataFrame(
        columns=[
            "df_index",
            "スプレッドシート行",
            "漢字",
            "画数",
            "漢検級",
            "ペア番号",
            "部品1",
            "部品2",
            "審議",
            "審議理由",
            "メモ",
        ]
    )


def save_df(df):
    try:
        return save_df_to_sheet(df, expected_before_df=original_df)
    except Exception as e:
        st.error("Googleスプレッドシートへの保存に失敗しました。")
        st.exception(e)
        st.stop()


review_df = build_review_pairs_df(df)

st.success(f"読み込み完了：登録行数 {len(df)} 件")

st.divider()

if review_df.empty:
    st.info("審議対象のペアはまだありません。")
    st.stop()


# =========================
# 絞り込み
# =========================
st.subheader("審議対象ペア")

col1, col2, col3 = st.columns(3)

with col1:
    kanji_query = st.text_input("漢字で検索", placeholder="例：橋")

with col2:
    part_query = st.text_input("部品で検索", placeholder="例：木")

with col3:
    reason_query = st.text_input("理由で検索", placeholder="例：分け方")

filtered_df = review_df.copy()

if kanji_query.strip():
    q = kanji_query.strip()
    filtered_df = filtered_df[filtered_df["漢字"].astype(str).str.contains(q, na=False)]

if part_query.strip():
    q = part_query.strip()
    filtered_df = filtered_df[
        filtered_df["部品1"].astype(str).str.contains(q, na=False)
        | filtered_df["部品2"].astype(str).str.contains(q, na=False)
    ]

if reason_query.strip():
    q = reason_query.strip()
    filtered_df = filtered_df[filtered_df["審議理由"].astype(str).str.contains(q, na=False)]

st.write(f"審議対象：{len(filtered_df)} 件")

display_df = filtered_df.drop(columns=["df_index"], errors="ignore")

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
)


# =========================
# 審議解除
# =========================
st.divider()
st.subheader("審議を解除する")

if filtered_df.empty:
    st.info("解除対象がありません。")
else:
    labels = []

    for _, row in filtered_df.iterrows():
        labels.append(
            f"{row['df_index']}|{row['ペア番号']}|{row['漢字']} → {row['部品1']}, {row['部品2']}｜{row['審議理由']}"
        )

    selected_label = st.selectbox(
        "審議を解除するペアを選択",
        labels
    )

    selected_parts = selected_label.split("|")
    selected_df_index = int(selected_parts[0])
    selected_pair_num = int(selected_parts[1])

    selected_row = filtered_df[
        (filtered_df["df_index"] == selected_df_index)
        & (filtered_df["ペア番号"] == selected_pair_num)
    ].iloc[0]

    st.write("選択中のペア")
    st.json(
        {
            "漢字": selected_row["漢字"],
            "部品1": selected_row["部品1"],
            "部品2": selected_row["部品2"],
            "審議理由": selected_row["審議理由"],
        }
    )

    clear_reason = st.checkbox(
        "審議理由も空にする",
        value=False
    )

    if st.button("このペアの審議を解除", type="primary"):
        review_col = f"ペア{selected_pair_num}_審議"
        reason_col = f"ペア{selected_pair_num}_審議理由"

        if review_col not in df.columns:
            df[review_col] = ""

        if reason_col not in df.columns:
            df[reason_col] = ""

        df.loc[selected_df_index, review_col] = ""

        if clear_reason:
            df.loc[selected_df_index, reason_col] = ""

        save_df(df)

        st.success("審議を解除しました。")
        st.rerun()


# =========================
# コピー・ダウンロード
# =========================
st.divider()

st.subheader("コピー用")

kanji_text = "".join(filtered_df["漢字"].dropna().astype(str).unique().tolist())

st.text_area(
    "審議対象の漢字一覧",
    value=kanji_text,
    height=100,
)

csv_data = display_df.to_csv(index=False, encoding="utf-8-sig")

st.download_button(
    label="審議ペア一覧をCSVでダウンロード",
    data=csv_data,
    file_name="review_pairs.csv",
    mime="text/csv",
)
