import streamlit as st
import pandas as pd
import re
from datetime import datetime
from data_store import load_df, save_df_to_sheet

st.set_page_config(page_title="漢字行 削除アプリ", layout="wide")

st.title("漢字行 削除アプリ")

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
    st.error("Googleスプレッドシートに『漢字』列がありません。")
    st.stop()

st.success(f"Googleスプレッドシートを読み込みました。現在の登録行数：{len(df)} 件")


# =========================
# 便利関数
# =========================
def extract_chars(text):
    """
    入力テキストから削除対象の漢字を抽出する。
    空白・句読点・区切り記号は無視する。
    重複は削除し、順番は保持する。
    """

    ignore_chars = {
        ",", "、", "，",
        ".", "。",
        "\t",
        " ", "　",
        "\n", "\r",
        "・",
        "|",
        "/",
        "\\",
        "／",
        "＼",
        "（", "）",
        "(", ")",
        "[", "]",
        "【", "】",
        "「", "」",
        "『", "』",
        ":", "：",
        ";", "；",
    }

    chars = []
    seen = set()

    for ch in text:
        if ch in ignore_chars:
            continue

        if ch.strip() == "":
            continue

        if ch in seen:
            continue

        seen.add(ch)
        chars.append(ch)

    return chars


def extract_line_numbers(text):
    """
    入力テキストから行番号を抽出する。
    例：
    2
    5
    10

    または
    2,5,10
    2 5 10

    に対応。
    """

    numbers = re.findall(r"\d+", text)

    line_numbers = []
    seen = set()

    for num in numbers:
        n = int(num)

        if n not in seen:
            seen.add(n)
            line_numbers.append(n)

    return line_numbers


def save_df(df):
    try:
        save_df_to_sheet(df)
    except Exception as e:
        st.error("Googleスプレッドシートへの保存に失敗しました。")
        st.exception(e)
        st.stop()


def get_rows_by_kanji(df, chars):
    """
    漢字指定から削除対象行を取得する。
    """

    registered_set = set(df["漢字"].astype(str).str.strip())

    found_chars = [ch for ch in chars if ch in registered_set]
    not_found_chars = [ch for ch in chars if ch not in registered_set]

    target_df = df[df["漢字"].isin(found_chars)].copy()

    return target_df, found_chars, not_found_chars


def get_rows_by_line_numbers(df, line_numbers):
    """
    Googleスプレッドシート上の行番号から削除対象行を取得する。
    ヘッダーを1行目として扱うので、データ1件目は2行目。
    """

    valid_records = []
    invalid_line_numbers = []

    for line_no in line_numbers:
        # スプレッドシートでは1行目がヘッダーなので、データ行のindexは line_no - 2
        idx = line_no - 2

        if 0 <= idx < len(df):
            valid_records.append({
                "スプレッドシート上の行番号": line_no,
                "index": idx,
            })
        else:
            invalid_line_numbers.append(line_no)

    if valid_records:
        indices = [r["index"] for r in valid_records]
        target_df = df.loc[indices].copy()
    else:
        target_df = df.iloc[0:0].copy()

    return target_df, valid_records, invalid_line_numbers


def add_display_line_number(df_part):
    """
    表示用に Googleスプレッドシート上の行番号を先頭に追加する。
    ヘッダーを1行目として、データ行は2行目から。
    """

    result = df_part.copy()
    result.insert(0, "スプレッドシート上の行番号", result.index + 2)
    return result


# =========================
# 削除前バックアップ案内
# =========================
st.subheader("削除前バックアップ")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_data = df.to_csv(sep="\t", index=False).encode("utf-8-sig")

st.download_button(
    label="現在のデータをTSVバックアップとしてダウンロード",
    data=backup_data,
    file_name=f"kanji_before_delete_{timestamp}.tsv",
    mime="text/tab-separated-values",
)

st.caption("削除前にバックアップをダウンロードしておくと安全です。Googleスプレッドシート側にも変更履歴があります。")

# =========================
# 削除方法選択
# =========================
st.divider()
st.subheader("削除方法を選択してください")

delete_mode = st.radio(
    "削除方法",
    [
        "漢字で削除",
        "行番号で削除",
        "漢字と行番号の両方で削除",
    ],
    index=0
)

st.caption("行番号は、Googleスプレッドシート上の行番号です。1行目はヘッダーなので、最初のデータ行は2行目です。")

target_indices = set()

# =========================
# 漢字指定
# =========================
if delete_mode in ["漢字で削除", "漢字と行番号の両方で削除"]:
    st.divider()
    st.subheader("漢字で削除")

    delete_text = st.text_area(
        "削除したい漢字を貼り付けてください",
        height=180,
        placeholder="例：\n王玉主\nまたは\n王\n玉\n主"
    )

    delete_chars = extract_chars(delete_text)

    if delete_chars:
        st.write(f"抽出された削除候補：{len(delete_chars)} 件")
        st.text_area(
            "削除候補 コピー確認用",
            value="".join(delete_chars),
            height=80,
            key="delete_chars_preview"
        )

        target_by_kanji, found_chars, not_found_chars = get_rows_by_kanji(df, delete_chars)

        if not target_by_kanji.empty:
            st.warning("漢字指定により、以下の行が削除候補です。")
            st.dataframe(
                add_display_line_number(target_by_kanji),
                use_container_width=True,
                hide_index=True
            )

            target_indices.update(target_by_kanji.index.tolist())

        if not_found_chars:
            st.info("以下の文字はデータベースに存在しないため、削除されません。")
            st.text_area(
                "未登録・削除対象外",
                value="".join(not_found_chars),
                height=80,
                key="not_found_chars"
            )
    else:
        st.info("漢字指定で削除する場合は、削除したい漢字を入力してください。")


# =========================
# 行番号指定
# =========================
if delete_mode in ["行番号で削除", "漢字と行番号の両方で削除"]:
    st.divider()
    st.subheader("行番号で削除")

    line_text = st.text_area(
        "削除したいGoogleスプレッドシート上の行番号を入力してください",
        height=150,
        placeholder="例：\n2\n5\n10\nまたは 2,5,10"
    )

    line_numbers = extract_line_numbers(line_text)

    if line_numbers:
        st.write(f"抽出された行番号：{len(line_numbers)} 件")
        st.text_area(
            "行番号 コピー確認用",
            value=", ".join(map(str, line_numbers)),
            height=80,
            key="line_numbers_preview"
        )

        target_by_line, valid_records, invalid_line_numbers = get_rows_by_line_numbers(df, line_numbers)

        if not target_by_line.empty:
            st.warning("行番号指定により、以下の行が削除候補です。必ず漢字を確認してください。")
            st.dataframe(
                add_display_line_number(target_by_line),
                use_container_width=True,
                hide_index=True
            )

            target_indices.update(target_by_line.index.tolist())

        if invalid_line_numbers:
            st.info("以下の行番号は範囲外のため、削除されません。")
            st.write(", ".join(map(str, invalid_line_numbers)))
    else:
        st.info("行番号指定で削除する場合は、削除したい行番号を入力してください。")


# =========================
# 削除対象の最終確認
# =========================
st.divider()
st.subheader("削除対象の最終確認")

if target_indices:
    sorted_indices = sorted(target_indices)

    final_target_df = df.loc[sorted_indices].copy()
    final_preview = add_display_line_number(final_target_df)

    st.error("以下の行が削除されます。漢字を必ず確認してください。")
    st.dataframe(
        final_preview,
        use_container_width=True,
        hide_index=True
    )

    target_kanji = final_target_df["漢字"].astype(str).tolist()

    st.write(f"削除対象行数：{len(final_target_df)} 件")
    st.write("削除対象漢字：")
    st.text_area(
        "削除対象漢字 コピー確認用",
        value="".join(target_kanji),
        height=100,
        key="final_target_kanji"
    )

    # =========================
    # 削除実行
    # =========================
    st.divider()
    st.subheader("削除実行")

    st.error("削除すると、対象漢字の画数・漢検級・メモ・部品ペアがすべて消えます。")

    confirm_text = st.text_input(
        "削除を実行するには DELETE と入力してください"
    )

    confirm_kanji = st.text_input(
        "さらに確認のため、削除対象漢字をそのまま入力してください",
        placeholder="上の『削除対象漢字』と同じ文字列を入力"
    )

    confirm_checkbox = st.checkbox(
        "削除前に必要なバックアップを取ったことを確認しました",
        value=False
    )

    if st.button("対象行を削除する", type="primary"):
        expected_kanji_text = "".join(target_kanji)

        if confirm_text != "DELETE":
            st.error("削除するには DELETE と入力してください。")
        elif confirm_kanji != expected_kanji_text:
            st.error("削除対象漢字の確認入力が一致していません。")
        elif not confirm_checkbox:
            st.error("確認チェックを入れてください。")
        else:
            before_count = len(df)

            df_after = df.drop(index=sorted_indices).reset_index(drop=True)

            after_count = len(df_after)
            deleted_count = before_count - after_count

            save_df(df_after)

            st.success(f"{deleted_count} 行をGoogleスプレッドシートから削除しました。")

            st.rerun()

else:
    st.info("削除対象はまだ選択されていません。")


# =========================
# 現在のデータ表示
# =========================
st.divider()

with st.expander("現在のデータベースを表示"):
    display_df = add_display_line_number(df)
    st.dataframe(display_df, use_container_width=True, hide_index=True)
