import httplib2
import pandas as pd
import streamlit as st
import google_auth_httplib2
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import HttpRequest


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "1VPDAayTH-ozwogddaZd3EQa9MdP6S5eu1GuHaj77tTM"
GSHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
SERVICE_ACCOUNT_FILE = "secrets/service_account.json"


credentials = service_account.Credentials.from_service_account_file(filename=SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build(serviceName="sheets", version="v4", credentials=credentials)

st.set_page_config(page_title="Language Hour", page_icon="🌐", layout="centered")
st.title("Language Hour Entry")
form = st.form(key="annotation")


def add_row(connector, sheet_name, row) -> None:
    connector.values().append(spreadsheetId=SPREADSHEET_ID,
    range=f"{sheet_name}!A:D",
    body=dict(values=row),
    valueInputOption="USER_ENTERED",
    ).execute()

@st.cache
def get_data(connector, sheet_name) -> pd.DataFrame:
    values = (connector.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{sheet_name}!A:D",
        ).execute()
    )
    df = pd.DataFrame(values["values"])
    df.columns = df.iloc[0]
    df = df[1:]
    return df

def read_form(form):
    with form:
        cols = st.columns((1, 1))
        name = cols[0].text_input(label="Name", placeholder="First Last")
        listening = cols[0].checkbox(label="Listening")
        reading = cols[0].checkbox(label="Reading")
        speaking = cols[0].checkbox(label="Speaking")
        description = st.text_area(label="Description", placeholder="what did you study?")
        cols = st.columns(2)
        date = cols[1].date_input(label="Date")
        minutes = cols[0].number_input(label="Minutes", min_value=0, max_value=240, step=15)
        submitted = st.form_submit_button(label="Submit")

    if submitted:
        if len(description) < 1:
            st.error("You need to include what you studied...")
        if minutes <= 0:
            st.error("You need to study longer than 0 minutes...")

        modality = ""
        if listening:
            modality += "L"
        if reading:
            modality += "R"
        if speaking:
            modality += "S"
            
        try:
            add_row(connector=service.spreadsheets(), sheet_name=name, row=[[str(date), minutes, modality, description]])
            st.success(f"Thanks {name.split()[0]}, your entry was submitted")
            st.balloons()
            expander = st.expander("show my entries")
            with expander:
                st.dataframe(get_data(connector=service.spreadsheets(), sheet_name=name))
        except:
            st.error("Name does not exist")

read_form(form)
