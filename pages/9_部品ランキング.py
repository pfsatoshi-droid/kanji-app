import streamlit as st
import pandas as pd
from data_store import load_df

st.set_page_config(page_title="部品ランキング・逆引き", layout="wide")

st.title("部品ランキング・逆引き")

st.write(
    """
    Googleスプレッドシート上の漢字データから、部品ごとの使用回数ランキングや、
    特定の部品がどの漢字に使われているかを確認できます。
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

if "漢字" not in df.columns:
    st.error("データベースに『漢字』列がありません。")
    st.stop()

st.success(f"Googleスプレッドシートを読み込みました。登録行数：{len(df)} 件")


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


def build_parts_long_df(df):
    """
    横持ちのペア列を、部品ごとの縦持ちデータに変換する。
    """

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
            p1_col = f"ペア{n}_部品1"
            p2_col = f"ペア{n}_部品2"

            part1 = str(row.get(p1_col, "")).strip()
            part2 = str(row.get(p2_col, "")).strip()

            if part1 != "":
                records.append(
                    {
                        "部品": part1,
                        "漢字": kanji,
                        "ペア番号": n,
                        "位置": "部品1",
                        "相方部品": part2,
                        "画数": strokes,
                        "漢検級": kanken_level,
                        "メモ": memo,
                    }
                )

            if part2 != "":
                records.append(
                    {
                        "部品": part2,
                        "漢字": kanji,
                        "ペア番号": n,
                        "位置": "部品2",
                        "相方部品": part1,
                        "画数": strokes,
                        "漢検級": kanken_level,
                        "メモ": memo,
                    }
                )

    if records:
        return pd.DataFrame(records)

    return pd.DataFrame(
        columns=[
            "部品",
            "漢字",
            "ペア番号",
            "位置",
            "相方部品",
            "画数",
            "漢検級",
            "メモ",
        ]
    )


parts_df = build_parts_long_df(df)

if parts_df.empty:
    st.warning("部品データがまだありません。")
    st.stop()


# =========================
# ランキング作成
# =========================
ranking_df = (
    parts_df
    .groupby("部品", as_index=False)
    .agg(
        使用回数=("漢字", "count"),
        使用漢字数=("漢字", lambda x: len(set(x))),
        使用漢字一覧=("漢字", lambda x: "、".join(sorted(set(x)))),
    )
    .sort_values(["使用漢字数", "使用回数", "部品"], ascending=[False, False, True])
    .reset_index(drop=True)
)

ranking_df.insert(0, "順位", range(1, len(ranking_df) + 1))


# =========================
# 概要
# =========================
st.divider()
st.subheader("概要")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("登録漢字数", df["漢字"].astype(str).str.strip().ne("").sum())

with col2:
    st.metric("登録部品種類数", parts_df["部品"].nunique())

with col3:
    st.metric("部品出現数", len(parts_df))


# =========================
# 部品ランキング
# =========================
st.divider()
st.subheader("部品使用ランキング")

min_count = st.number_input(
    "表示する最小使用漢字数",
    min_value=1,
    max_value=int(ranking_df["使用漢字数"].max()),
    value=1,
    step=1,
)

top_n = st.number_input(
    "ランキング表示件数",
    min_value=10,
    max_value=max(10, len(ranking_df)),
    value=min(50, len(ranking_df)),
    step=10,
)

filtered_ranking = ranking_df[ranking_df["使用漢字数"] >= min_count].head(top_n)

st.dataframe(
    filtered_ranking,
    use_container_width=True,
    hide_index=True,
)

csv_ranking = filtered_ranking.to_csv(index=False, encoding="utf-8-sig")

st.download_button(
    label="表示中のランキングをCSVでダウンロード",
    data=csv_ranking,
    file_name="parts_ranking.csv",
    mime="text/csv",
)


# =========================
# 部品逆引き
# =========================
st.divider()
st.subheader("部品から漢字を逆引き")

part_options = sorted(parts_df["部品"].dropna().astype(str).unique().tolist())

search_part = st.text_input(
    "調べたい部品を入力",
    placeholder="例：氵、女、木、口"
).strip()

selected_part = st.selectbox(
    "または一覧から選択",
    [""] + part_options,
)

target_part = search_part if search_part else selected_part

if target_part:
    matched_parts = parts_df[parts_df["部品"] == target_part].copy()

    if matched_parts.empty:
        st.warning(f"部品「{target_part}」は見つかりませんでした。")
    else:
        used_kanji = sorted(matched_parts["漢字"].dropna().astype(str).unique().tolist())

        st.success(
            f"部品「{target_part}」は {len(used_kanji)} 種類の漢字に使われています。"
        )

        st.text_area(
            "使用漢字一覧コピー用",
            value="".join(used_kanji),
            height=100,
        )

        st.write("使用漢字一覧")
        st.write("、".join(used_kanji))

        display_cols = [
            "漢字",
            "部品",
            "ペア番号",
            "位置",
            "相方部品",
            "画数",
            "漢検級",
            "メモ",
        ]

        matched_parts = matched_parts[display_cols].sort_values(
            ["漢検級", "画数", "漢字", "ペア番号"]
        )

        st.dataframe(
            matched_parts,
            use_container_width=True,
            hide_index=True,
        )

        csv_detail = matched_parts.to_csv(index=False, encoding="utf-8-sig")

        st.download_button(
            label=f"部品「{target_part}」の逆引き結果をCSVでダウンロード",
            data=csv_detail,
            file_name=f"part_{target_part}_kanji.csv",
            mime="text/csv",
        )


# =========================
# 詳細データ
# =========================
st.divider()

with st.expander("部品出現データ全体を見る"):
    st.dataframe(parts_df, use_container_width=True, hide_index=True)
