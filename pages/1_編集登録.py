import streamlit as st
import pandas as pd
from data_store import load_df, save_df_to_sheet

st.set_page_config(page_title="漢字を見る・編集", layout="wide")

st.title("漢字を見る・編集")


# =========================
# データ読み込み
# =========================
try:
    df = load_df()
except Exception as e:
    st.error("Googleスプレッドシートからの読み込みに失敗しました。")
    st.exception(e)
    st.stop()


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
    review_col = f"ペア{pair_num}_審議"
    reason_col = f"ペア{pair_num}_審議理由"

    for col in [col1, col2, review_col, reason_col]:
        if col not in df.columns:
            df[col] = ""

    return df


def get_pairs_from_row(row, df):
    pairs = []

    for n in get_pair_numbers(df):
        p1 = str(row.get(f"ペア{n}_部品1", "")).strip()
        p2 = str(row.get(f"ペア{n}_部品2", "")).strip()
        review = str(row.get(f"ペア{n}_審議", "")).strip()
        reason = str(row.get(f"ペア{n}_審議理由", "")).strip()

        if p1 != "" or p2 != "":
            pairs.append(
                {
                    "num": n,
                    "part1": p1,
                    "part2": p2,
                    "review": review,
                    "reason": reason,
                }
            )

    return pairs


def rewrite_pairs_to_row(df, row_index, pairs):
    """
    pairs は以下の形：
    [
        {"part1": "木", "part2": "喬", "review": "TRUE", "reason": "..."},
        ...
    ]
    """

    # 既存ペア列を空にする
    for n in get_pair_numbers(df):
        df = ensure_pair_columns(df, n)
        df.loc[row_index, f"ペア{n}_部品1"] = ""
        df.loc[row_index, f"ペア{n}_部品2"] = ""
        df.loc[row_index, f"ペア{n}_審議"] = ""
        df.loc[row_index, f"ペア{n}_審議理由"] = ""

    # 新しいペアを1から順番に書き込む
    for i, pair in enumerate(pairs, start=1):
        df = ensure_pair_columns(df, i)

        df.loc[row_index, f"ペア{i}_部品1"] = pair.get("part1", "")
        df.loc[row_index, f"ペア{i}_部品2"] = pair.get("part2", "")
        df.loc[row_index, f"ペア{i}_審議"] = pair.get("review", "")
        df.loc[row_index, f"ペア{i}_審議理由"] = pair.get("reason", "")

    return df


def save_df(df):
    base_cols = ["漢字", "画数", "漢検級", "メモ"]
    pair_cols = []

    for n in get_pair_numbers(df):
        pair_cols.append(f"ペア{n}_部品1")
        pair_cols.append(f"ペア{n}_部品2")
        pair_cols.append(f"ペア{n}_審議")
        pair_cols.append(f"ペア{n}_審議理由")

    other_cols = [c for c in df.columns if c not in base_cols + pair_cols]
    ordered_cols = base_cols + pair_cols + other_cols

    df = df[ordered_cols]

    try:
        save_df_to_sheet(df)
    except Exception as e:
        st.error("Googleスプレッドシートへの保存に失敗しました。")
        st.exception(e)
        st.stop()


def find_kanji_using_part(df, part):
    results = []

    if part == "":
        return results

    for _, row in df.iterrows():
        kanji = str(row.get("漢字", "")).strip()
        if kanji == "":
            continue

        for n in get_pair_numbers(df):
            p1 = str(row.get(f"ペア{n}_部品1", "")).strip()
            p2 = str(row.get(f"ペア{n}_部品2", "")).strip()

            if part == p1 or part == p2:
                results.append(kanji)
                break

    return sorted(set(results))


def has_any_pair(row, df):
    for n in get_pair_numbers(df):
        p1 = str(row.get(f"ペア{n}_部品1", "")).strip()
        p2 = str(row.get(f"ペア{n}_部品2", "")).strip()
        if p1 != "" or p2 != "":
            return True
    return False


def has_review_pair(row, df):
    for n in get_pair_numbers(df):
        review = str(row.get(f"ペア{n}_審議", "")).strip()
        reason = str(row.get(f"ペア{n}_審議理由", "")).strip()
        if review == "TRUE" or reason != "":
            return True
    return False


def make_pair_table(existing_pairs):
    return pd.DataFrame(
        [
            {
                "ペア番号": pair["num"],
                "部品1": pair["part1"],
                "部品2": pair["part2"],
                "審議": "審議中" if pair["review"] == "TRUE" else "",
                "審議理由": pair["reason"],
            }
            for pair in existing_pairs
        ]
    )


# =========================
# 入力
# =========================
st.subheader("漢字を入力してください")

kanji_input = st.text_input("漢字", placeholder="例：橋")
kanji = kanji_input.strip()

if len(kanji) > 1:
    st.warning("漢字は1文字だけ使います。余分な文字は削除してください。")

matched = pd.DataFrame()
row_index = None
row = None
existing_pairs = []

current_strokes = ""
current_level = ""
current_memo = ""

if kanji:
    matched = df[df["漢字"] == kanji]

    if not matched.empty:
        row_index = matched.index[0]
        row = df.loc[row_index]
        existing_pairs = get_pairs_from_row(row, df)

        current_strokes = row.get("画数", "")
        current_level = row.get("漢検級", "")
        current_memo = row.get("メモ", "")


tab_view, tab_edit, tab_table = st.tabs(["見る", "編集する", "絞り込みテーブル"])


# =========================
# 見るタブ
# =========================
with tab_view:
    st.subheader("見る")

    if not kanji:
        st.info("見たい漢字を上の入力欄に入れてください。")

    elif matched.empty:
        st.warning(f"{kanji} はまだ登録されていません。")
        st.write("登録する場合は「編集する」タブから追加できます。")

    else:
        st.markdown(f"# {kanji}")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("画数", current_strokes if current_strokes else "未登録")

        with col2:
            st.metric("漢検級", current_level if current_level else "未登録")

        with col3:
            st.metric("登録ペア数", len(existing_pairs))

        if current_memo:
            st.divider()
            st.subheader("メモ")
            st.write(current_memo)

        st.divider()
        st.subheader("部品ペア")

        if not existing_pairs:
            st.info("まだ部品ペアは登録されていません。")
        else:
            for pair in existing_pairs:
                p1 = pair["part1"]
                p2 = pair["part2"]
                review = pair["review"]
                reason = pair["reason"]

                if review == "TRUE":
                    st.warning(f"ペア{pair['num']}：{p1} + {p2}　【審議中】")
                    if reason:
                        st.caption(f"理由：{reason}")
                else:
                    st.success(f"ペア{pair['num']}：{p1} + {p2}")

            st.dataframe(
                make_pair_table(existing_pairs),
                use_container_width=True,
                hide_index=True,
            )

        st.divider()
        st.subheader("部品の逆引き")

        if existing_pairs:
            used_parts = []

            for pair in existing_pairs:
                if pair["part1"]:
                    used_parts.append(pair["part1"])
                if pair["part2"]:
                    used_parts.append(pair["part2"])

            used_parts = sorted(set(used_parts))

            for part in used_parts:
                related_kanji = find_kanji_using_part(df, part)

                with st.expander(f"部品「{part}」が使われている漢字：{len(related_kanji)} 件"):
                    st.text_area(
                        f"「{part}」使用漢字コピー用",
                        value="".join(related_kanji),
                        height=80,
                        key=f"view_part_copy_{part}",
                    )

                    st.write("、".join(related_kanji) if related_kanji else "なし")


# =========================
# 編集タブ
# =========================
with tab_edit:
    st.subheader("編集する")

    if not kanji:
        st.info("編集したい漢字を上の入力欄に入れてください。")
    else:
        st.markdown(f"## {kanji} の情報")

        if not matched.empty:
            st.info(f"{kanji} は登録済みです。")
        else:
            st.warning(f"{kanji} はまだ登録されていません。新しく追加できます。")

        # =========================
        # 漢字そのものの情報
        # =========================
        st.divider()
        st.subheader("漢字情報")

        strokes = st.text_input(
            "画数",
            value=current_strokes,
            placeholder="例：16",
            key="edit_strokes",
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
            index=level_index,
            key="edit_kanken_level",
        )

        memo = st.text_area(
            "メモ",
            value=current_memo,
            placeholder="例：分解についての補足など",
            key="edit_memo",
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
            st.success(f"{kanji} の情報をGoogleスプレッドシートに保存しました。")
            st.rerun()

        # =========================
        # 登録済みペア表示
        # =========================
        st.divider()
        st.subheader("登録済みペア")

        if existing_pairs:
            st.dataframe(
                make_pair_table(existing_pairs),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.write("まだペアは登録されていません。")

        # =========================
        # ペア追加
        # =========================
        st.divider()
        st.subheader("新しいペアを追加")

        add_part1 = st.text_input("追加する部品1", placeholder="例：木", key="add_part1")
        add_part2 = st.text_input("追加する部品2", placeholder="例：喬", key="add_part2")

        add_review = st.checkbox(
            "このペアを審議対象にする",
            value=False,
            key="add_review",
        )

        add_review_reason = st.text_area(
            "審議理由",
            placeholder="例：右側をさらに分けるか迷う",
            key="add_review_reason",
        )

        if st.button("このペアを追加", type="primary"):
            add_part1 = add_part1.strip()
            add_part2 = add_part2.strip()

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

                current_pairs = [
                    {
                        "part1": pair["part1"],
                        "part2": pair["part2"],
                        "review": pair["review"],
                        "reason": pair["reason"],
                    }
                    for pair in existing_pairs
                ]

                if any(pair["part1"] == add_part1 and pair["part2"] == add_part2 for pair in current_pairs):
                    st.error(f"すでに登録されています：{kanji} → {add_part1}, {add_part2}")
                else:
                    current_pairs.append(
                        {
                            "part1": add_part1,
                            "part2": add_part2,
                            "review": "TRUE" if add_review else "",
                            "reason": add_review_reason.strip(),
                        }
                    )

                    df = rewrite_pairs_to_row(df, row_index, current_pairs)
                    save_df(df)

                    if add_review:
                        st.success(f"審議対象として追加しました：{kanji} → {add_part1}, {add_part2}")
                    else:
                        st.success(f"追加しました：{kanji} → {add_part1}, {add_part2}")

                    st.rerun()

        # =========================
        # ペア編集・削除
        # =========================
        if existing_pairs:
            st.divider()
            st.subheader("登録済みペアを編集・削除")

            pair_labels = [
                f"ペア{pair['num']}: {pair['part1']}, {pair['part2']}"
                + ("【審議中】" if pair["review"] == "TRUE" else "")
                for pair in existing_pairs
            ]

            selected_label = st.selectbox("編集・削除するペアを選択", pair_labels)

            selected_index = pair_labels.index(selected_label)
            selected_pair = existing_pairs[selected_index]

            old_p1 = selected_pair["part1"]
            old_p2 = selected_pair["part2"]
            old_review = selected_pair["review"]
            old_reason = selected_pair["reason"]

            edit_part1 = st.text_input("編集後の部品1", value=old_p1, key="edit_part1")
            edit_part2 = st.text_input("編集後の部品2", value=old_p2, key="edit_part2")

            edit_review = st.checkbox(
                "このペアを審議対象にする",
                value=(old_review == "TRUE"),
                key="edit_review",
            )

            edit_review_reason = st.text_area(
                "審議理由",
                value=old_reason,
                placeholder="例：別の分け方もありそう",
                key="edit_review_reason",
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button("このペアを更新"):
                    edit_part1 = edit_part1.strip()
                    edit_part2 = edit_part2.strip()

                    if edit_part1 == "" or edit_part2 == "":
                        st.error("部品1と部品2を両方入力してください。")
                    else:
                        current_pairs = [
                            {
                                "part1": pair["part1"],
                                "part2": pair["part2"],
                                "review": pair["review"],
                                "reason": pair["reason"],
                            }
                            for pair in existing_pairs
                        ]

                        current_pairs[selected_index] = {
                            "part1": edit_part1,
                            "part2": edit_part2,
                            "review": "TRUE" if edit_review else "",
                            "reason": edit_review_reason.strip(),
                        }

                        pair_keys = [(pair["part1"], pair["part2"]) for pair in current_pairs]

                        if len(pair_keys) != len(set(pair_keys)):
                            st.error("同じペアが重複しています。別の内容にしてください。")
                        else:
                            df = rewrite_pairs_to_row(df, row_index, current_pairs)
                            save_df(df)
                            st.success(f"更新しました：{kanji} → {edit_part1}, {edit_part2}")
                            st.rerun()

            with col2:
                if st.button("このペアを削除"):
                    current_pairs = [
                        {
                            "part1": pair["part1"],
                            "part2": pair["part2"],
                            "review": pair["review"],
                            "reason": pair["reason"],
                        }
                        for pair in existing_pairs
                    ]

                    deleted_pair = current_pairs.pop(selected_index)

                    df = rewrite_pairs_to_row(df, row_index, current_pairs)
                    save_df(df)

                    st.success(f"削除しました：{kanji} → {deleted_pair['part1']}, {deleted_pair['part2']}")
                    st.rerun()

            # =========================
            # 危険操作
            # =========================
            with st.expander("危険操作：この漢字の行を削除する"):
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
# 絞り込みテーブル
# =========================
with tab_table:
    st.subheader("絞り込みテーブル")

    table_df = df.copy()

    for col in ["漢字", "画数", "漢検級", "メモ"]:
        if col not in table_df.columns:
            table_df[col] = ""

    kanji_query = st.text_input(
        "漢字で検索",
        placeholder="例：橋",
        key="table_kanji_query",
    )

    part_query = st.text_input(
        "部品で検索",
        placeholder="例：木、氵、女",
        key="table_part_query",
    )

    memo_query = st.text_input(
        "メモで検索",
        placeholder="例：旧字体、要確認",
        key="table_memo_query",
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        stroke_values = [
            x for x in table_df["画数"].dropna().astype(str).str.strip().unique().tolist()
            if x != ""
        ]

        stroke_options = ["すべて"] + sorted(
            stroke_values,
            key=lambda x: int(x) if x.isdigit() else 999,
        )

        selected_strokes = st.selectbox(
            "画数",
            stroke_options,
            key="table_strokes",
        )

    with col2:
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

        selected_level = st.selectbox(
            "漢検級",
            level_options,
            key="table_level",
        )

    with col3:
        filter_mode = st.selectbox(
            "表示条件",
            [
                "すべて",
                "審議中ペアあり",
                "ペア未登録",
                "メモあり",
            ],
            key="table_filter_mode",
        )

    # =========================
    # 絞り込み処理
    # =========================
    filtered_df = table_df.copy()

    if kanji_query.strip():
        q = kanji_query.strip()
        filtered_df = filtered_df[
            filtered_df["漢字"].astype(str).str.contains(q, na=False)
        ]

    if memo_query.strip():
        q = memo_query.strip()
        filtered_df = filtered_df[
            filtered_df["メモ"].astype(str).str.contains(q, na=False)
        ]

    if selected_strokes != "すべて":
        filtered_df = filtered_df[
            filtered_df["画数"].astype(str) == selected_strokes
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

    if filter_mode == "審議中ペアあり":
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
    # 表示列を調整
    # =========================
    st.write(f"表示件数：{len(filtered_df)} 件")

    show_all_columns = st.checkbox(
        "すべての列を表示する",
        value=False,
        key="table_show_all_columns",
    )

    if show_all_columns:
        display_df = filtered_df
    else:
        display_cols = ["漢字", "画数", "漢検級", "メモ"]

        for n in get_pair_numbers(filtered_df):
            display_cols.extend(
                [
                    f"ペア{n}_部品1",
                    f"ペア{n}_部品2",
                    f"ペア{n}_審議",
                    f"ペア{n}_審議理由",
                ]
            )

        display_cols = [c for c in display_cols if c in filtered_df.columns]
        display_df = filtered_df[display_cols]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    # =========================
    # コピー・ダウンロード
    # =========================
    st.divider()

    kanji_text = "".join(
        filtered_df["漢字"].dropna().astype(str).str.strip().tolist()
    )

    st.text_area(
        "表示中の漢字コピー用",
        value=kanji_text,
        height=100,
        key="table_kanji_copy",
    )

    csv_data = display_df.to_csv(index=False, encoding="utf-8-sig")

    st.download_button(
        label="表示中のテーブルをCSVでダウンロード",
        data=csv_data,
        file_name="filtered_kanji_table.csv",
        mime="text/csv",
    )
