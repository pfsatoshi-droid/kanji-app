import json
from datetime import datetime, timezone, timedelta

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound


DEFAULT_COLUMNS = [
    "漢字",
    "画数",
    "漢検級",
    "メモ",
]

HISTORY_COLUMNS = [
    "timestamp",
    "action",
    "kanji",
    "field",
    "before",
    "after",
]


def now_jst_string():
    jst = timezone(timedelta(hours=9))
    return datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S")


def get_spreadsheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes,
    )

    client = gspread.authorize(credentials)

    spreadsheet_name = st.secrets["spreadsheet_name"]
    spreadsheet = client.open(spreadsheet_name)

    return spreadsheet


def get_worksheet():
    spreadsheet = get_spreadsheet()
    worksheet_name = st.secrets.get("worksheet_name", "シート1")
    worksheet = spreadsheet.worksheet(worksheet_name)
    return worksheet


def get_history_worksheet():
    spreadsheet = get_spreadsheet()
    history_sheet_name = st.secrets.get("history_worksheet_name", "history")

    try:
        worksheet = spreadsheet.worksheet(history_sheet_name)
    except WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=history_sheet_name,
            rows=1000,
            cols=len(HISTORY_COLUMNS),
        )
        worksheet.update([HISTORY_COLUMNS])

    return worksheet


@st.cache_data(ttl=10)
def load_df():
    worksheet = get_worksheet()
    records = worksheet.get_all_records()

    if records:
        df = pd.DataFrame(records)
    else:
        df = pd.DataFrame(columns=DEFAULT_COLUMNS)

    df = df.astype(str).fillna("")

    for col in DEFAULT_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df


@st.cache_data(ttl=10)
def load_history_df():
    worksheet = get_history_worksheet()
    records = worksheet.get_all_records()

    if records:
        df = pd.DataFrame(records)
    else:
        df = pd.DataFrame(columns=HISTORY_COLUMNS)

    df = df.astype(str).fillna("")

    for col in HISTORY_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df


def row_to_summary(row):
    data = {}

    for key, value in row.items():
        value = str(value).strip()
        if value != "":
            data[str(key)] = value

    return json.dumps(data, ensure_ascii=False)


def make_history_records(before_df, after_df):
    """
    before_df と after_df を比較して、変更履歴を作る。
    漢字列を主キーとして扱う。
    """

    timestamp = now_jst_string()
    records = []

    if "漢字" not in before_df.columns or "漢字" not in after_df.columns:
        return records

    before_df = before_df.astype(str).fillna("")
    after_df = after_df.astype(str).fillna("")

    before_df = before_df[before_df["漢字"].astype(str).str.strip() != ""].copy()
    after_df = after_df[after_df["漢字"].astype(str).str.strip() != ""].copy()

    before_map = {}
    after_map = {}

    for _, row in before_df.iterrows():
        k = str(row.get("漢字", "")).strip()
        if k != "" and k not in before_map:
            before_map[k] = row

    for _, row in after_df.iterrows():
        k = str(row.get("漢字", "")).strip()
        if k != "" and k not in after_map:
            after_map[k] = row

    before_keys = set(before_map.keys())
    after_keys = set(after_map.keys())

    # 追加
    for k in sorted(after_keys - before_keys):
        records.append([
            timestamp,
            "追加",
            k,
            "行",
            "",
            row_to_summary(after_map[k]),
        ])

    # 削除
    for k in sorted(before_keys - after_keys):
        records.append([
            timestamp,
            "削除",
            k,
            "行",
            row_to_summary(before_map[k]),
            "",
        ])

    # 更新
    common_keys = sorted(before_keys & after_keys)
    all_columns = sorted(set(before_df.columns) | set(after_df.columns))

    for k in common_keys:
        before_row = before_map[k]
        after_row = after_map[k]

        for col in all_columns:
            if col == "漢字":
                continue

            before_value = str(before_row.get(col, "")).strip()
            after_value = str(after_row.get(col, "")).strip()

            if before_value != after_value:
                records.append([
                    timestamp,
                    "更新",
                    k,
                    col,
                    before_value,
                    after_value,
                ])

    return records


def append_history(records):
    if not records:
        return

    worksheet = get_history_worksheet()
    worksheet.append_rows(records, value_input_option="USER_ENTERED")

    st.cache_data.clear()


def save_df_to_sheet(df):
    worksheet = get_worksheet()

    df = df.astype(str).fillna("")

    # 保存前の状態を取得して、差分から履歴を作る
    try:
        before_records = worksheet.get_all_records()
        before_df = pd.DataFrame(before_records) if before_records else pd.DataFrame(columns=df.columns)
        before_df = before_df.astype(str).fillna("")
    except Exception:
        before_df = pd.DataFrame(columns=df.columns)

    history_records = make_history_records(before_df, df)

    values = [df.columns.tolist()] + df.values.tolist()

    worksheet.clear()
    worksheet.update(values)

    append_history(history_records)

    st.cache_data.clear()
