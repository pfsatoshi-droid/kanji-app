import streamlit as st
import pandas as pd
from data_store import load_df

st.set_page_config(page_title="漢字リスト照合アプリ", layout="wide")

st.title("漢字リスト照合アプリ")

# =========================
# Googleスプレッドシート 読み込み
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

registered_kanji_list = (
    df["漢字"]
    .dropna()
    .astype(str)
    .str.strip()
    .tolist()
)

registered_kanji_list = [k for k in registered_kanji_list if k != ""]
registered_kanji_set = set(registered_kanji_list)

st.success(f"Googleスプレッドシートの登録漢字数：{len(registered_kanji_set)} 件")


# =========================
# 漢字抽出関数
# =========================
def extract_chars_with_location(text):
    """
    入力テキストから文字を抽出する。
    行番号・位置・Unicode・その行の内容も記録する。
    同じ文字が複数回出た場合は、最初の出現だけ残す。
    """

    records = []
    seen = set()

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

    lines = text.splitlines()

    for line_no, line in enumerate(lines, start=1):
        for pos, ch in enumerate(line, start=1):
            if ch in ignore_chars:
                continue

            if ch.strip() == "":
                continue

            # 同じ文字は最初に出た場所だけ記録
            if ch in seen:
                continue

            seen.add(ch)

            records.append({
                "漢字": ch,
                "行番号": line_no,
                "位置": pos,
                "Unicode": f"U+{ord(ch):04X}",
                "その行の内容": line,
            })

    return records


def make_copy_text(chars):
    return "".join(chars)


# =========================
# 入力フォーム
# =========================
st.subheader("基準にしたい漢字リストを貼り付けてください")

input_text = st.text_area(
    "漢字リスト",
    height=260,
    placeholder="例：\n王玉主生沙婚痕\nまたは\n王\n玉\n主\n生"
)

st.divider()

check_mode = st.radio(
    "チェック内容",
    [
        "貼り付けリストにあるが、データベースにない漢字を出す",
        "データベースにあるが、貼り付けリストにない漢字を出す",
        "両方チェックする",
    ],
    index=0
)

show_location = st.checkbox(
    "行番号・位置・Unicodeも表示する",
    value=False
)

show_replacement_warning = st.checkbox(
    "文字化け文字 � があったら警告する",
    value=True
)

if st.button("チェックする", type="primary"):
    input_records = extract_chars_with_location(input_text)
    input_chars = [r["漢字"] for r in input_records]
    input_set = set(input_chars)

    if not input_chars:
        st.error("チェックする漢字リストを入力してください。")
        st.stop()

    st.divider()
    st.subheader("入力リストの概要")

    st.write(f"貼り付けたユニーク文字数：{len(input_chars)} 件")
    st.write(f"データベースの登録漢字数：{len(registered_kanji_set)} 件")

    # 文字化け文字チェック
    replacement_records = [r for r in input_records if r["漢字"] == "�"]

    if show_replacement_warning and replacement_records:
        st.error("入力リスト内に文字化けの可能性がある文字 `�` が含まれています。")

        replacement_df = pd.DataFrame(replacement_records)
        st.dataframe(replacement_df, use_container_width=True, hide_index=True)

    # =========================
    # 1. 入力にあるがDBにない
    # =========================
    if check_mode in [
        "貼り付けリストにあるが、データベースにない漢字を出す",
        "両方チェックする",
    ]:
        missing_records = [
            r for r in input_records
            if r["漢字"] not in registered_kanji_set
        ]

        missing_chars = [r["漢字"] for r in missing_records]

        st.divider()
        st.subheader("貼り付けリストにあるが、データベースにない漢字")

        st.write(f"未登録：{len(missing_chars)} 件")

        if missing_chars:
            st.warning("データベースに含まれていない漢字があります。")

            st.text_area(
                "コピー用",
                value=make_copy_text(missing_chars),
                height=120,
                key="missing_copy"
            )

            if show_location:
                missing_df = pd.DataFrame(missing_records)
            else:
                missing_df = pd.DataFrame({"未登録漢字": missing_chars})

            st.dataframe(missing_df, use_container_width=True, hide_index=True)

            csv_data = pd.DataFrame(missing_records).to_csv(
                index=False,
                encoding="utf-8-sig"
            )

            st.download_button(
                label="未登録漢字をCSVでダウンロード",
                data=csv_data,
                file_name="missing_kanji.csv",
                mime="text/csv"
            )
        else:
            st.success("貼り付けリストの文字はすべてデータベースに登録済みです。")

    # =========================
    # 2. DBにあるが入力にない
    # =========================
    if check_mode in [
        "データベースにあるが、貼り付けリストにない漢字を出す",
        "両方チェックする",
    ]:
        extra_chars = [
            k for k in registered_kanji_list
            if k not in input_set
        ]

        st.divider()
        st.subheader("データベースにあるが、貼り付けリストにない漢字")

        st.write(f"対象外候補：{len(extra_chars)} 件")

        if extra_chars:
            st.warning("データベースにはあるが、貼り付けリストには含まれていない漢字があります。")

            st.text_area(
                "コピー用",
                value=make_copy_text(extra_chars),
                height=120,
                key="extra_copy"
            )

            # スプレッドシート側の行番号を付ける
            extra_records = []

            for row_no, row in df.reset_index(drop=True).iterrows():
                k = str(row.get("漢字", "")).strip()

                if k != "" and k in extra_chars:
                    record = {
                        "漢字": k,
                        "スプレッドシート上の行番号": row_no + 2,  # ヘッダーが1行目なのでデータは2行目から
                    }

                    # 追加情報もあると便利
                    if "画数" in df.columns:
                        record["画数"] = row.get("画数", "")
                    if "漢検級" in df.columns:
                        record["漢検級"] = row.get("漢検級", "")
                    if "メモ" in df.columns:
                        record["メモ"] = row.get("メモ", "")

                    record["Unicode"] = f"U+{ord(k):04X}" if len(k) == 1 else ""

                    extra_records.append(record)

            if show_location:
                extra_df = pd.DataFrame(extra_records)
            else:
                extra_df = pd.DataFrame({"余分な登録漢字": extra_chars})

            st.dataframe(extra_df, use_container_width=True, hide_index=True)

            csv_data = pd.DataFrame(extra_records).to_csv(
                index=False,
                encoding="utf-8-sig"
            )

            st.download_button(
                label="余分な登録漢字をCSVでダウンロード",
                data=csv_data,
                file_name="extra_kanji.csv",
                mime="text/csv"
            )
        else:
            st.success("データベースの漢字はすべて貼り付けリストに含まれています。")

    # =========================
    # 入力リスト全体を確認
    # =========================
    with st.expander("抽出された入力文字を確認する"):
        if show_location:
            input_df = pd.DataFrame(input_records)
        else:
            input_df = pd.DataFrame({"入力文字": input_chars})

        st.dataframe(input_df, use_container_width=True, hide_index=True)

st.divider()

with st.expander("現在のデータベースを表示"):
    st.dataframe(df, use_container_width=True, hide_index=True)
