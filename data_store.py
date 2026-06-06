import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials


DEFAULT_COLUMNS = [
    "漢字",
    "画数",
    "漢検級",
    "メモ",
]


def get_worksheet():
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
    worksheet_name = st.secrets.get("worksheet_name", "シート1")

    spreadsheet = client.open(spreadsheet_name)
    worksheet = spreadsheet.worksheet(worksheet_name)

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


def save_df_to_sheet(df):
    worksheet = get_worksheet()

    df = df.astype(str).fillna("")

    values = [df.columns.tolist()] + df.values.tolist()

    worksheet.clear()
    worksheet.update(values)

    st.cache_data.clear()
