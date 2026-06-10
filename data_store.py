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

AUTO_BACKUP_PREFIX = "auto_backup_"
AUTO_BACKUP_KEEP_COUNT = 10


class StaleSheetError(Exception):
    pass


def now_jst_string():
    jst = timezone(timedelta(hours=9))
    return datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S")


def now_jst_backup_name():
    jst = timezone(timedelta(hours=9))
    return datetime.now(jst).strftime("%Y%m%d_%H%M%S")


def get_auto_backup_prefix():
    return st.secrets.get("auto_backup_sheet_prefix", AUTO_BACKUP_PREFIX)


def get_auto_backup_keep_count():
    try:
        keep_count = int(st.secrets.get("auto_backup_keep_count", AUTO_BACKUP_KEEP_COUNT))
    except Exception:
        keep_count = AUTO_BACKUP_KEEP_COUNT

    return max(1, keep_count)


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


def list_auto_backup_worksheets():
    spreadsheet = get_spreadsheet()
    prefix = get_auto_backup_prefix()

    backups = [
        worksheet
        for worksheet in spreadsheet.worksheets()
        if worksheet.title.startswith(prefix)
    ]

    return sorted(backups, key=lambda worksheet: worksheet.title, reverse=True)


def get_unique_backup_title(spreadsheet, base_title):
    existing_titles = {worksheet.title for worksheet in spreadsheet.worksheets()}

    if base_title not in existing_titles:
        return base_title

    counter = 2
    while True:
        title = f"{base_title}_{counter}"
        if title not in existing_titles:
            return title
        counter += 1


def trim_auto_backups(spreadsheet):
    keep_count = get_auto_backup_keep_count()
    prefix = get_auto_backup_prefix()

    backups = [
        worksheet
        for worksheet in spreadsheet.worksheets()
        if worksheet.title.startswith(prefix)
    ]
    backups = sorted(backups, key=lambda worksheet: worksheet.title, reverse=True)

    for worksheet in backups[keep_count:]:
        spreadsheet.del_worksheet(worksheet)


def create_auto_backup(df):
    df = df.astype(str).fillna("")

    if df.empty and len(df.columns) == 0:
        return None

    spreadsheet = get_spreadsheet()
    base_title = f"{get_auto_backup_prefix()}{now_jst_backup_name()}"
    title = get_unique_backup_title(spreadsheet, base_title)

    rows = max(len(df) + 1, 1)
    cols = max(len(df.columns), 1)
    worksheet = spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)

    values = [df.columns.tolist()] + df.values.tolist()
    if values:
        worksheet.update(values)

    trim_auto_backups(spreadsheet)

    return title


def load_auto_backup_df(worksheet_title):
    spreadsheet = get_spreadsheet()
    prefix = get_auto_backup_prefix()

    if not worksheet_title.startswith(prefix):
        raise ValueError("自動バックアップではないシート名です。")

    worksheet = spreadsheet.worksheet(worksheet_title)
    records = worksheet.get_all_records()

    if records:
        df = pd.DataFrame(records)
    else:
        header = worksheet.row_values(1)
        df = pd.DataFrame(columns=header)

    return df.astype(str).fillna("")


def normalize_df_for_compare(df, columns=None):
    df = df.copy().astype(str).fillna("")

    if columns is None:
        columns = sorted(df.columns.tolist())
    else:
        columns = sorted(columns)

    for col in columns:
        if col not in df.columns:
            df[col] = ""

    return df[columns].reset_index(drop=True)


def dataframes_equal(left_df, right_df):
    columns = set(left_df.columns) | set(right_df.columns)
    left_df = normalize_df_for_compare(left_df, columns)
    right_df = normalize_df_for_compare(right_df, columns)

    return left_df.equals(right_df)


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


def save_df_to_sheet(df, expected_before_df=None):
    worksheet = get_worksheet()

    df = df.astype(str).fillna("")

    # 保存前の状態を取得して、差分から履歴を作る
    try:
        before_records = worksheet.get_all_records()
        before_df = pd.DataFrame(before_records) if before_records else pd.DataFrame(columns=df.columns)
        before_df = before_df.astype(str).fillna("")
    except Exception:
        before_df = pd.DataFrame(columns=df.columns)

    if expected_before_df is not None and not dataframes_equal(before_df, expected_before_df):
        raise StaleSheetError(
            "読み込み後にGoogleスプレッドシートが変更されています。"
            "上書き事故を防ぐため保存を中止しました。ページを再読み込みしてから、もう一度編集してください。"
        )

    if dataframes_equal(before_df, df):
        st.cache_data.clear()
        return False

    history_records = make_history_records(before_df, df)

    values = [df.columns.tolist()] + df.values.tolist()

    create_auto_backup(before_df)

    worksheet.clear()
    worksheet.update(values)

    append_history(history_records)

    st.cache_data.clear()

    return True
