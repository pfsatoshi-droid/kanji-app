import re
import streamlit as st
import pandas as pd
from data_store import load_df, save_df_to_sheet
from ui_helpers import set_flash, show_change_summary, show_database_status, show_flash

st.set_page_config(page_title="漢字ペア CSV取り込みアプリ", layout="wide")

st.title("漢字ペア CSV取り込みアプリ")
show_flash()

# =========================
# メインDB読み込み
# =========================
try:
    df = load_df()
except Exception as e:
    st.error("Googleスプレッドシートからの読み込みに失敗しました。")
    st.exception(e)
    st.stop()

original_df = df.copy(deep=True)
show_database_status(df)

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
        p1 = str(row.get(f"ペア{n}_部品1", "")).strip()
        p2 = str(row.get(f"ペア{n}_部品2", "")).strip()
        if p1 != "" or p2 != "":
            pairs.append((p1, p2))
    return pairs


def rewrite_pairs_to_row(df, row_index, pairs):
    """
    pairs は [(部品1, 部品2), ...] の形。
    既存のペア列をいったん空にして、ペア1から詰め直す。
    """

    for n in get_pair_numbers(df):
        df.loc[row_index, f"ペア{n}_部品1"] = ""
        df.loc[row_index, f"ペア{n}_部品2"] = ""

    for i, (p1, p2) in enumerate(pairs, start=1):
        df = ensure_pair_columns(df, i)
        df.loc[row_index, f"ペア{i}_部品1"] = p1
        df.loc[row_index, f"ペア{i}_部品2"] = p2

    return df


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


def read_uploaded_csv(uploaded_file):
    """
    CSVの文字コード違いに対応。
    Excel由来なら utf-8-sig / cp932 が多い。
    """

    encodings = ["utf-8-sig", "utf-8", "cp932"]

    for enc in encodings:
        try:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, dtype=str, encoding=enc).fillna("")
        except Exception:
            pass

    raise ValueError("CSVを読み込めませんでした。文字コードを確認してください。")


def detect_pair_numbers(columns):
    """
    ペア1_部品1, ペア1_部品2 のような列名からペア番号を検出する。
    """

    nums = set()

    for col in columns:
        m1 = re.match(r"ペア(\d+)_部品1", col)
        m2 = re.match(r"ペア(\d+)_部品2", col)

        if m1:
            nums.add(int(m1.group(1)))
        if m2:
            nums.add(int(m2.group(1)))

    return sorted(nums)


def build_import_result(
    source_df,
    import_df,
    kanji_col,
    pair_nums,
    overwrite_pairs,
    skip_duplicates,
    overwrite_info,
):
    result_df = source_df.copy()
    added_kanji_count = 0
    added_pair_count = 0
    replaced_kanji_count = 0
    skipped_pair_count = 0
    skipped_row_count = 0
    updated_info_count = 0

    for _, import_row in import_df.iterrows():
        k = str(import_row.get(kanji_col, "")).strip()

        if k == "" or len(k) != 1:
            skipped_row_count += 1
            continue

        imported_pairs = []

        for n in pair_nums:
            p1_col = f"ペア{n}_部品1"
            p2_col = f"ペア{n}_部品2"

            p1 = str(import_row.get(p1_col, "")).strip()
            p2 = str(import_row.get(p2_col, "")).strip()

            if p1 == "" and p2 == "":
                continue

            if p1 == "" or p2 == "":
                skipped_row_count += 1
                continue

            imported_pairs.append((p1, p2))

        matched = result_df[result_df["漢字"] == k]

        if not matched.empty:
            row_index = matched.index[0]
            current_pairs = get_pairs_from_row(result_df.loc[row_index], result_df)
        else:
            new_row = {
                "漢字": k,
                "画数": "",
                "漢検級": "",
                "メモ": "",
            }
            result_df = pd.concat([result_df, pd.DataFrame([new_row])], ignore_index=True)
            row_index = result_df.index[-1]
            current_pairs = []
            added_kanji_count += 1

        if overwrite_info:
            changed = False

            for col_name in ["画数", "漢検級", "メモ"]:
                if col_name in import_df.columns:
                    value = str(import_row.get(col_name, "")).strip()
                    if value != "":
                        result_df.loc[row_index, col_name] = value
                        changed = True

            if changed:
                updated_info_count += 1

        if overwrite_pairs:
            new_pairs = []
            for pair in imported_pairs:
                if pair not in new_pairs:
                    new_pairs.append(pair)

            result_df = rewrite_pairs_to_row(result_df, row_index, new_pairs)
            added_pair_count += len(new_pairs)
            replaced_kanji_count += 1
        else:
            new_pairs = current_pairs.copy()

            for pair in imported_pairs:
                if skip_duplicates and pair in new_pairs:
                    skipped_pair_count += 1
                    continue

                new_pairs.append(pair)
                added_pair_count += 1

            result_df = rewrite_pairs_to_row(result_df, row_index, new_pairs)

    stats = {
        "新規漢字": added_kanji_count,
        "追加ペア": added_pair_count,
        "置き換えた漢字": replaced_kanji_count,
        "重複スキップ": skipped_pair_count,
        "行・不完全ペアのスキップ": skipped_row_count,
        "漢字情報更新": updated_info_count,
    }

    return result_df, stats


# =========================
# CSVアップロード
# =========================
st.subheader("CSVをアップロード")

uploaded_file = st.file_uploader(
    "既存データベースのCSVを選択してください",
    type=["csv"]
)

st.caption("対応形式：漢字, ペア1_部品1, ペア1_部品2, ペア2_部品1, ペア2_部品2, ...")

if uploaded_file is not None:
    try:
        import_df = read_uploaded_csv(uploaded_file)

        # 列名の空白を削除
        import_df.columns = [str(c).strip() for c in import_df.columns]

        st.write("アップロードされたCSVのプレビュー")
        st.dataframe(import_df.head(20), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("列の確認")

        columns = list(import_df.columns)

        kanji_col = st.selectbox(
            "漢字が入っている列",
            columns,
            index=columns.index("漢字") if "漢字" in columns else 0
        )

        pair_nums = detect_pair_numbers(columns)

        if pair_nums:
            st.success(f"検出されたペア列：{', '.join([f'ペア{n}' for n in pair_nums])}")
        else:
            st.error("ペア列が見つかりませんでした。列名は ペア1_部品1, ペア1_部品2 のようにしてください。")

        overwrite_pairs = st.checkbox(
            "既存のペアを消して、CSVのペアで置き換える",
            value=False
        )

        skip_duplicates = st.checkbox(
            "同じペアがすでにある場合はスキップする",
            value=True
        )

        overwrite_info = st.checkbox(
            "CSVに画数・漢検級・メモ列がある場合、既存の情報を上書きする",
            value=False
        )

        st.warning(
            "安全に取り込むなら、最初は「既存のペアを消して置き換える」はOFFのままがおすすめです。"
        )

        if pair_nums:
            result_df, stats = build_import_result(
                df,
                import_df,
                kanji_col,
                pair_nums,
                overwrite_pairs,
                skip_duplicates,
                overwrite_info,
            )

            st.divider()
            st.subheader("取り込み前の確認")

            stat_cols = st.columns(3)
            for index, (label, value) in enumerate(stats.items()):
                with stat_cols[index % 3]:
                    st.metric(label, value)

            show_change_summary(df, result_df, title="取り込みによるDB変更")

            execute = st.button("この内容でCSVを取り込む", type="primary")

            if execute:
                save_df(result_df)
                set_flash(
                    "CSV取り込みが完了しました。"
                    f"新規漢字：{stats['新規漢字']}件、追加ペア：{stats['追加ペア']}件、"
                    f"置き換えた漢字：{stats['置き換えた漢字']}件"
                )
                st.rerun()

    except Exception as e:
        st.error("CSVの読み込み・取り込み中にエラーが起きました。")
        st.exception(e)

st.divider()

st.subheader("現在のデータベース")

st.dataframe(df, use_container_width=True, hide_index=True)
