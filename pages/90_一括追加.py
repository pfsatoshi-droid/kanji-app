import streamlit as st
import pandas as pd
from data_store import load_df, save_df_to_sheet

st.set_page_config(page_title="漢字情報 一括追加アプリ", layout="centered")

st.title("漢字情報 一括追加アプリ")

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

# 必要な基本列を追加
for col in ["漢字", "画数", "漢検級", "メモ"]:
    if col not in df.columns:
        df[col] = ""


def get_pair_numbers(df):
    nums = []
    for col in df.columns:
        if col.startswith("ペア") and col.endswith("_部品1"):
            num = col.replace("ペア", "").replace("_部品1", "")
            if num.isdigit():
                nums.append(int(num))
    return sorted(nums)


def save_df(df):
    base_cols = ["漢字", "画数", "漢検級", "メモ"]

    pair_cols = []
    for n in get_pair_numbers(df):
        pair_cols.append(f"ペア{n}_部品1")
        pair_cols.append(f"ペア{n}_部品2")

    other_cols = [c for c in df.columns if c not in base_cols + pair_cols]
    ordered_cols = base_cols + pair_cols + other_cols

    df = df[ordered_cols]

    try:
        return save_df_to_sheet(df, expected_before_df=original_df)
    except Exception as e:
        st.error("Googleスプレッドシートへの保存に失敗しました。")
        st.exception(e)
        st.stop()


# =========================
# 一括追加フォーム
# =========================
st.subheader("同じ画数・漢検級の漢字をまとめて追加")

bulk_text = st.text_area(
    "追加したい漢字を貼り付けてください",
    placeholder="例：\n王\n玉\n主\n生"
)

bulk_strokes = st.text_input(
    "画数",
    placeholder="例：4"
)

kanken_options = [
    "",
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

bulk_level = st.selectbox(
    "漢検級",
    kanken_options
)

bulk_memo = st.text_area(
    "メモ",
    placeholder="全ての漢字に同じメモを入れる場合だけ入力"
)

overwrite = st.checkbox(
    "既存の漢字がある場合、画数・漢検級・メモを上書きする",
    value=False
)

if st.button("一括追加", type="primary"):
    if bulk_text.strip() == "":
        st.error("追加する漢字を入力してください。")
    else:
        kanji_list = []

        for line in bulk_text.splitlines():
            line = line.strip()
            if line == "":
                continue

            # 「王 玉 主」みたいなスペース区切りにも対応
            parts = line.replace("　", " ").split()

            if len(parts) == 1:
                # 「王玉主生」みたいに連続で貼った場合にも対応
                for ch in parts[0]:
                    kanji_list.append(ch)
            else:
                for p in parts:
                    kanji_list.append(p)

        added = []
        updated = []
        skipped = []

        for k in kanji_list:
            k = k.strip()

            if len(k) != 1:
                skipped.append(k)
                continue

            matched = df[df["漢字"] == k]

            if not matched.empty:
                row_index = matched.index[0]

                if overwrite:
                    df.loc[row_index, "画数"] = bulk_strokes
                    df.loc[row_index, "漢検級"] = bulk_level
                    df.loc[row_index, "メモ"] = bulk_memo
                    updated.append(k)
                else:
                    skipped.append(k)
            else:
                new_row = {
                    "漢字": k,
                    "画数": bulk_strokes,
                    "漢検級": bulk_level,
                    "メモ": bulk_memo,
                }

                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                added.append(k)

        save_df(df)

        st.success(f"追加：{len(added)}件、更新：{len(updated)}件、スキップ：{len(skipped)}件")

        if added:
            st.write("追加した漢字")
            st.write("、".join(added))

        if updated:
            st.write("更新した漢字")
            st.write("、".join(updated))

        if skipped:
            st.warning("スキップした漢字")
            st.write("、".join(skipped))

        st.rerun()

st.divider()

st.subheader("現在のデータ")

st.dataframe(df, use_container_width=True, hide_index=True)
