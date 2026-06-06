import streamlit as st
import pandas as pd
from data_store import load_df

st.set_page_config(page_title="軽量テーブル", layout="wide")

st.title("軽量テーブル")

st.write(
    """
    漢字データを軽く確認するための閲覧専用ページです。
    編集や保存は行いません。
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

for col in ["漢字", "画数", "漢検級", "メモ"]:
    if col not in df.columns:
        df[col] = ""

df = df.astype(str).fillna("")

st.success(f"読み込み完了：{len(df)} 件")


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


def make_compact_table(df, max_pairs=4):
    """
    表示用に、ペア列を見やすくまとめた軽量テーブルを作る。
    """
    records = []

    pair_nums = get_pair_numbers(df)

    for _, row in df.iterrows():
        kanji = str(row.get("漢字", "")).strip()
        if kanji == "":
            continue

        pairs = []
        review_marks = []

        for n in pair_nums[:max_pairs]:
            p1 = str(row.get(f"ペア{n}_部品1", "")).strip()
            p2 = str(row.get(f"ペア{n}_部品2", "")).strip()
            review = str(row.get(f"ペア{n}_審議", "")).strip()
            reason = str(row.get(f"ペア{n}_審議理由", "")).strip()

            if p1 != "" or p2 != "":
                pair_text = f"{p1}+{p2}"

                if review == "TRUE" or reason != "":
                    pair_text += " ⚠️"
                    review_marks.append(f"ペア{n}")

                pairs.append(pair_text)

        records.append(
            {
                "漢字": kanji,
                "画数": str(row.get("画数", "")).strip(),
                "漢検級": str(row.get("漢検級", "")).strip(),
                "ペア": " / ".join(pairs),
                "審議": "、".join(review_marks),
                "メモ": str(row.get("メモ", "")).strip(),
            }
        )

    return pd.DataFrame(records)


# =========================
# 表示設定
# =========================
st.divider()
st.subheader("表示設定")

col1, col2, col3, col4 = st.columns(4)

with col1:
    kanji_query = st.text_input("漢字検索", placeholder="例：橋")

with col2:
    part_query = st.text_input("部品検索", placeholder="例：木")

with col3:
    level_options = [
        "すべて",
        "10級",
        "9級",
        "8級",
        "7級",
        "6級",
        "5級",
        "4級",
        "3級",
        "準2級",
        "2級",
        "準1級",
        "1級",
    ]
    selected_level = st.selectbox("漢検級", level_options)

with col4:
    filter_mode = st.selectbox(
        "表示条件",
        [
            "すべて",
            "審議あり",
            "ペア未登録",
            "メモあり",
        ],
    )

col5, col6 = st.columns(2)

with col5:
    max_pairs = st.number_input(
        "表示する最大ペア数",
        min_value=1,
        max_value=20,
        value=4,
        step=1,
    )

with col6:
    max_rows = st.number_input(
        "最大表示件数",
        min_value=50,
        max_value=3000,
        value=300,
        step=50,
    )


# =========================
# 絞り込み処理
# =========================
filtered_df = df.copy()

if kanji_query.strip():
    q = kanji_query.strip()
    filtered_df = filtered_df[
        filtered_df["漢字"].astype(str).str.contains(q, na=False)
    ]

if selected_level != "すべて":
    filtered_df = filtered_df[
        filtered_df["漢検級"].astype(str) == selected_level
    ]

if part_query.strip():
    q = part_query.strip()

    part_cols = [
        col for col in filtered_df.columns
        if col.startswith("ペア") and ("_部品1" in col or "_部品2" in col)
    ]

    if part_cols:
        mask = pd.Series(False, index=filtered_df.index)

        for col in part_cols:
            mask = mask | filtered_df[col].astype(str).str.contains(q, na=False)

        filtered_df = filtered_df[mask]
    else:
        filtered_df = filtered_df.iloc[0:0]

if filter_mode == "審議あり":
    review_cols = [
        col for col in filtered_df.columns
        if col.startswith("ペア") and col.endswith("_審議")
    ]

    reason_cols = [
        col for col in filtered_df.columns
        if col.startswith("ペア") and col.endswith("_審議理由")
    ]

    mask = pd.Series(False, index=filtered_df.index)

    for col in review_cols:
        mask = mask | (filtered_df[col].astype(str) == "TRUE")

    for col in reason_cols:
        mask = mask | (filtered_df[col].astype(str).str.strip() != "")

    filtered_df = filtered_df[mask]

elif filter_mode == "ペア未登録":
    part_cols = [
        col for col in filtered_df.columns
        if col.startswith("ペア") and ("_部品1" in col or "_部品2" in col)
    ]

    if part_cols:
        has_pair = pd.Series(False, index=filtered_df.index)

        for col in part_cols:
            has_pair = has_pair | (filtered_df[col].astype(str).str.strip() != "")

        filtered_df = filtered_df[~has_pair]

elif filter_mode == "メモあり":
    filtered_df = filtered_df[
        filtered_df["メモ"].astype(str).str.strip() != ""
    ]


# =========================
# 軽量表示
# =========================
st.divider()

compact_df = make_compact_table(filtered_df, max_pairs=max_pairs)

total_count = len(compact_df)
display_df = compact_df.head(max_rows)

st.write(f"該当件数：{total_count} 件")
st.write(f"表示件数：{len(display_df)} 件")

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
)

if total_count > max_rows:
    st.info(f"表示を軽くするため、先頭 {max_rows} 件だけ表示しています。条件を絞るか、最大表示件数を増やしてください。")


# =========================
# コピー・ダウンロード
# =========================
st.divider()

kanji_text = "".join(display_df["漢字"].dropna().astype(str).tolist())

st.text_area(
    "表示中の漢字コピー用",
    value=kanji_text,
    height=100,
)

csv_data = compact_df.to_csv(index=False, encoding="utf-8-sig")

st.download_button(
    label="絞り込み結果をCSVでダウンロード",
    data=csv_data,
    file_name="kanji_light_table.csv",
    mime="text/csv",
)
