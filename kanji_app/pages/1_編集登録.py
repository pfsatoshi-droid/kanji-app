import streamlit as st
import pandas as pd
from pathlib import Path

DATA_PATH = Path("kanji.tsv")

st.set_page_config(page_title="漢字部品ペア登録アプリ", layout="centered")

st.title("漢字部品ペア登録アプリ")

# =========================
# データ読み込み
# =========================
if DATA_PATH.exists():
    df = pd.read_csv(DATA_PATH, sep="\t", dtype=str).fillna("")
else:
    df = pd.DataFrame(columns=["漢字", "画数", "漢検級", "メモ"])

# 必要な基本列を追加
for col in ["漢字", "画数", "漢検級", "メモ"]:
    if col not in df.columns:
        df[col] = ""

# 古い形式「部品1」「部品2」がある場合、ペア1に変換
if "部品1" in df.columns and "部品2" in df.columns:
    if "ペア1_部品1" not in df.columns:
        df["ペア1_部品1"] = df["部品1"]
    if "ペア1_部品2" not in df.columns:
        df["ペア1_部品2"] = df["部品2"]
    df = df.drop(columns=["部品1", "部品2"])


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


def ensure_pair_columns(df, pair_num):
    col1 = f"ペア{pair_num}_部品1"
    col2 = f"ペア{pair_num}_部品2"

    if col1 not in df.columns:
        df[col1] = ""
    if col2 not in df.columns:
        df[col2] = ""

    return df


def get_pairs_from_row(row, df):
    pairs = []
    for n in get_pair_numbers(df):
        p1 = row.get(f"ペア{n}_部品1", "")
        p2 = row.get(f"ペア{n}_部品2", "")
        if p1 != "" or p2 != "":
            pairs.append((n, p1, p2))
    return pairs


def rewrite_pairs_to_row(df, row_index, pairs):
    """
    pairs は [(部品1, 部品2), ...] の形。
    既存のペア列をいったん空にして、ペア1から詰め直す。
    """

    # 既存ペア列を空にする
    for n in get_pair_numbers(df):
        df.loc[row_index, f"ペア{n}_部品1"] = ""
        df.loc[row_index, f"ペア{n}_部品2"] = ""

    # 新しいペアを1から順番に書き込む
    for i, (p1, p2) in enumerate(pairs, start=1):
        df = ensure_pair_columns(df, i)
        df.loc[row_index, f"ペア{i}_部品1"] = p1
        df.loc[row_index, f"ペア{i}_部品2"] = p2

    return df


def save_df(df):
    # 列順を整理する
    base_cols = ["漢字", "画数", "漢検級", "メモ"]
    pair_cols = []

    for n in get_pair_numbers(df):
        pair_cols.append(f"ペア{n}_部品1")
        pair_cols.append(f"ペア{n}_部品2")

    other_cols = [c for c in df.columns if c not in base_cols + pair_cols]
    ordered_cols = base_cols + pair_cols + other_cols

    df = df[ordered_cols]
    df.to_csv(DATA_PATH, sep="\t", index=False)


# =========================
# 入力フォーム
# =========================
st.subheader("漢字を入力してください")

kanji_input = st.text_input("漢字", placeholder="例：出")

kanji = kanji_input.strip()

if len(kanji) > 1:
    st.warning("漢字は1文字だけ使います。余分な文字は削除してください。")

if kanji:
    st.markdown(f"## {kanji} の情報")

    matched = df[df["漢字"] == kanji]

    if not matched.empty:
        row_index = matched.index[0]
        row = df.loc[row_index]
        existing_pairs = get_pairs_from_row(row, df)

        current_strokes = row.get("画数", "")
        current_level = row.get("漢検級", "")
        current_memo = row.get("メモ", "")

        st.info(f"{kanji} は登録済みです。")

    else:
        row_index = None
        existing_pairs = []

        current_strokes = ""
        current_level = ""
        current_memo = ""

        st.warning(f"{kanji} はまだ登録されていません。新しく追加できます。")

    # =========================
    # 漢字そのものの情報
    # =========================
    st.divider()
    st.subheader("漢字情報")

    strokes = st.text_input(
        "画数",
        value=current_strokes,
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

    if current_level in kanken_options:
        level_index = kanken_options.index(current_level)
    else:
        level_index = 0

    kanken_level = st.selectbox(
        "漢検級",
        kanken_options,
        index=level_index
    )

    memo = st.text_area(
        "メモ",
        value=current_memo,
        placeholder="例：四画。玉・主などの構成要素にもなる。"
    )

    if st.button("漢字情報を保存"):
        if row_index is None:
            new_row = {
                "漢字": kanji,
                "画数": strokes,
                "漢検級": kanken_level,
                "メモ": memo,
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        else:
            df.loc[row_index, "画数"] = strokes
            df.loc[row_index, "漢検級"] = kanken_level
            df.loc[row_index, "メモ"] = memo

        save_df(df)
        st.success(f"{kanji} の情報を保存しました。")
        st.rerun()

    # =========================
    # 登録済みペア表示
    # =========================
    st.divider()
    st.subheader("登録済みペア")

    if existing_pairs:
        pair_table = pd.DataFrame(
            [
                {
                    "ペア番号": n,
                    "部品1": p1,
                    "部品2": p2,
                }
                for n, p1, p2 in existing_pairs
            ]
        )
        st.dataframe(pair_table, use_container_width=True, hide_index=True)
    else:
        st.write("まだペアは登録されていません。")

    # =========================
    # ペア追加
    # =========================
    st.divider()
    st.subheader("新しいペアを追加")

    add_part1 = st.text_input("追加する部品1", placeholder="例：一", key="add_part1")
    add_part2 = st.text_input("追加する部品2", placeholder="例：土", key="add_part2")

    if st.button("このペアを追加", type="primary"):
        if add_part1 == "" or add_part2 == "":
            st.error("部品1と部品2を両方入力してください。")
        else:
            if row_index is None:
                new_row = {
                    "漢字": kanji,
                    "画数": strokes,
                    "漢検級": kanken_level,
                    "メモ": memo,
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                row_index = df.index[-1]
                existing_pairs = []

            current_pairs = [(p1, p2) for _, p1, p2 in existing_pairs]

            if (add_part1, add_part2) in current_pairs:
                st.error(f"すでに登録されています：{kanji} → {add_part1}, {add_part2}")
            else:
                current_pairs.append((add_part1, add_part2))
                df = rewrite_pairs_to_row(df, row_index, current_pairs)
                save_df(df)
                st.success(f"追加しました：{kanji} → {add_part1}, {add_part2}")
                st.rerun()

    # =========================
    # ペア編集・削除
    # =========================
    if existing_pairs:
        st.divider()
        st.subheader("登録済みペアを編集・削除")

        pair_labels = [
            f"ペア{n}: {p1}, {p2}"
            for n, p1, p2 in existing_pairs
        ]

        selected_label = st.selectbox("編集・削除するペアを選択", pair_labels)

        selected_index = pair_labels.index(selected_label)
        selected_num, old_p1, old_p2 = existing_pairs[selected_index]

        edit_part1 = st.text_input("編集後の部品1", value=old_p1, key="edit_part1")
        edit_part2 = st.text_input("編集後の部品2", value=old_p2, key="edit_part2")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("このペアを更新"):
                if edit_part1 == "" or edit_part2 == "":
                    st.error("部品1と部品2を両方入力してください。")
                else:
                    current_pairs = [(p1, p2) for _, p1, p2 in existing_pairs]
                    current_pairs[selected_index] = (edit_part1, edit_part2)

                    if len(current_pairs) != len(set(current_pairs)):
                        st.error("同じペアが重複しています。別の内容にしてください。")
                    else:
                        df = rewrite_pairs_to_row(df, row_index, current_pairs)
                        save_df(df)
                        st.success(f"更新しました：{kanji} → {edit_part1}, {edit_part2}")
                        st.rerun()

        with col2:
            if st.button("このペアを削除"):
                current_pairs = [(p1, p2) for _, p1, p2 in existing_pairs]
                deleted_pair = current_pairs.pop(selected_index)

                df = rewrite_pairs_to_row(df, row_index, current_pairs)
                save_df(df)

                st.success(f"削除しました：{kanji} → {deleted_pair[0]}, {deleted_pair[1]}")
                st.rerun()

        # =========================
        # 漢字行そのものを削除
        # =========================
        st.divider()
        st.subheader("危険操作")

        st.warning("この漢字の行を削除すると、この漢字に登録された情報と全ペアが消えます。")

        confirm_delete = st.checkbox(f"{kanji} の行を削除することを確認しました")

        if st.button("この漢字を削除"):
            if confirm_delete:
                df = df.drop(index=row_index).reset_index(drop=True)
                save_df(df)
                st.success(f"{kanji} の行を削除しました。")
                st.rerun()
            else:
                st.error("削除するには確認チェックを入れてください。")

# =========================
# データ全体表示
# =========================
st.divider()

st.subheader("登録済みデータ")

st.dataframe(df, use_container_width=True, hide_index=True)