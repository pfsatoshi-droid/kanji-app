import csv
import io
from typing import Dict, Iterable

import pandas as pd
import streamlit as st
from gspread.exceptions import WorksheetNotFound
from gspread.utils import rowcol_to_a1

from data_store import get_spreadsheet


DEFAULT_JUKUGO_COLUMNS = ["熟語", "読み", "意味", "メモ"]
INTERNAL_ROW_COLUMN = "__sheet_row"
CSV_ENCODINGS = ("utf-8-sig", "utf-8", "cp932", "shift_jis")


def get_jukugo_worksheet():
    """熟語用ワークシートを取得し、存在しなければ作成する。"""
    spreadsheet = get_spreadsheet()
    worksheet_name = st.secrets.get("jukugo_worksheet_name", "熟語")

    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=worksheet_name,
            rows=1000,
            cols=len(DEFAULT_JUKUGO_COLUMNS),
        )
        worksheet.update([DEFAULT_JUKUGO_COLUMNS])

    header = [str(value).strip() for value in worksheet.row_values(1)]
    if not header:
        worksheet.update([DEFAULT_JUKUGO_COLUMNS])
    elif any(column not in header for column in DEFAULT_JUKUGO_COLUMNS):
        updated_header = header + [
            column for column in DEFAULT_JUKUGO_COLUMNS if column not in header
        ]
        worksheet.resize(cols=max(worksheet.col_count, len(updated_header)))
        worksheet.update([updated_header])

    return worksheet


def _clean_dataframe(df: pd.DataFrame, keep_internal_row: bool = False) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned.columns = [str(column).replace("\ufeff", "").strip() for column in cleaned.columns]
    cleaned = cleaned.fillna("").astype(str)

    for column in cleaned.columns:
        cleaned[column] = cleaned[column].str.strip()

    for column in DEFAULT_JUKUGO_COLUMNS:
        if column not in cleaned.columns:
            cleaned[column] = ""

    ordered_columns = DEFAULT_JUKUGO_COLUMNS + [
        column
        for column in cleaned.columns
        if column not in DEFAULT_JUKUGO_COLUMNS + [INTERNAL_ROW_COLUMN]
    ]

    if keep_internal_row and INTERNAL_ROW_COLUMN in cleaned.columns:
        ordered_columns.append(INTERNAL_ROW_COLUMN)

    return cleaned[ordered_columns]


@st.cache_data(ttl=10)
def load_jukugo_df() -> pd.DataFrame:
    """熟語シートを読み込み、物理行番号を内部列として保持する。"""
    worksheet = get_jukugo_worksheet()
    values = worksheet.get_all_values()

    if not values:
        return pd.DataFrame(columns=DEFAULT_JUKUGO_COLUMNS + [INTERNAL_ROW_COLUMN])

    header = [str(value).replace("\ufeff", "").strip() for value in values[0]]
    if not header:
        header = DEFAULT_JUKUGO_COLUMNS.copy()

    rows = []
    physical_rows = []

    for sheet_row, raw_row in enumerate(values[1:], start=2):
        row = list(raw_row[: len(header)])
        row.extend([""] * (len(header) - len(row)))

        if any(str(value).strip() for value in row):
            rows.append(row)
            physical_rows.append(sheet_row)

    df = pd.DataFrame(rows, columns=header)
    df[INTERNAL_ROW_COLUMN] = physical_rows
    return _clean_dataframe(df, keep_internal_row=True)


def _get_header(worksheet) -> list[str]:
    header = [str(value).replace("\ufeff", "").strip() for value in worksheet.row_values(1)]
    if not header:
        header = DEFAULT_JUKUGO_COLUMNS.copy()
        worksheet.update([header])

    missing_columns = [column for column in DEFAULT_JUKUGO_COLUMNS if column not in header]
    if missing_columns:
        header.extend(missing_columns)
        worksheet.resize(cols=max(worksheet.col_count, len(header)))
        worksheet.update([header])

    return header


def append_jukugo_record(record: Dict[str, str]) -> None:
    worksheet = get_jukugo_worksheet()
    header = _get_header(worksheet)
    row = [str(record.get(column, "")).strip() for column in header]
    worksheet.append_row(row, value_input_option="USER_ENTERED")
    st.cache_data.clear()


def update_jukugo_record(sheet_row: int, record: Dict[str, str]) -> None:
    worksheet = get_jukugo_worksheet()
    header = _get_header(worksheet)
    values = [str(record.get(column, "")).strip() for column in header]
    end_cell = rowcol_to_a1(int(sheet_row), len(header))
    worksheet.update(
        range_name=f"A{int(sheet_row)}:{end_cell}",
        values=[values],
        value_input_option="USER_ENTERED",
    )
    st.cache_data.clear()


def delete_jukugo_record(sheet_row: int) -> None:
    worksheet = get_jukugo_worksheet()
    worksheet.delete_rows(int(sheet_row))
    st.cache_data.clear()


def save_jukugo_df(df: pd.DataFrame, chunk_size: int = 5000) -> None:
    """熟語シートを全置換する。大量データは分割して書き込む。"""
    worksheet = get_jukugo_worksheet()
    cleaned = _clean_dataframe(df, keep_internal_row=False)

    cleaned = cleaned[cleaned["熟語"].astype(str).str.strip() != ""].copy()
    cleaned = cleaned.drop_duplicates(subset=["熟語"], keep="first").reset_index(drop=True)

    rows_needed = max(len(cleaned) + 1, 2)
    cols_needed = max(len(cleaned.columns), 1)
    worksheet.clear()
    worksheet.resize(rows=rows_needed, cols=cols_needed)

    header = cleaned.columns.tolist()
    worksheet.update(range_name=f"A1:{rowcol_to_a1(1, cols_needed)}", values=[header])

    if not cleaned.empty:
        values = cleaned.values.tolist()
        for start in range(0, len(values), chunk_size):
            chunk = values[start : start + chunk_size]
            start_row = start + 2
            end_row = start_row + len(chunk) - 1
            end_cell = rowcol_to_a1(end_row, cols_needed)
            worksheet.update(
                range_name=f"A{start_row}:{end_cell}",
                values=chunk,
                value_input_option="USER_ENTERED",
            )

    st.cache_data.clear()


def parse_jukugo_csv(file_bytes: bytes) -> pd.DataFrame:
    """ヘッダーあり・なしの両方の熟語CSVを読み込む。"""
    text = None
    last_error = None

    for encoding in CSV_ENCODINGS:
        try:
            text = file_bytes.decode(encoding)
            break
        except UnicodeDecodeError as error:
            last_error = error

    if text is None:
        raise ValueError("CSVの文字コードを判定できませんでした。") from last_error

    rows = [row for row in csv.reader(io.StringIO(text)) if any(cell.strip() for cell in row)]
    if not rows:
        return pd.DataFrame(columns=DEFAULT_JUKUGO_COLUMNS)

    first_cell = rows[0][0].replace("\ufeff", "").strip() if rows[0] else ""
    has_header = first_cell in {"熟語", "語", "word", "jukugo"}

    if has_header:
        df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
        df.columns = [str(column).replace("\ufeff", "").strip() for column in df.columns]
        if "熟語" not in df.columns:
            df = df.rename(columns={df.columns[0]: "熟語"})
    else:
        width = max(len(row) for row in rows)
        normalized_rows = [row + [""] * (width - len(row)) for row in rows]
        columns = DEFAULT_JUKUGO_COLUMNS[:width]
        if width > len(DEFAULT_JUKUGO_COLUMNS):
            columns += [f"追加列{i}" for i in range(1, width - len(DEFAULT_JUKUGO_COLUMNS) + 1)]
        df = pd.DataFrame(normalized_rows, columns=columns)

    cleaned = _clean_dataframe(df, keep_internal_row=False)
    cleaned = cleaned[cleaned["熟語"] != ""].copy()
    cleaned = cleaned.drop_duplicates(subset=["熟語"], keep="first").reset_index(drop=True)
    return cleaned
