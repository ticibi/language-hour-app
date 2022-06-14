import pandas as pd
import streamlit as st
import streamlit_authenticator as stauth
from google.oauth2 import service_account
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = st.secrets["SPREADSHEET_ID"]
SERVICE_INFO = st.secrets["google_service_account"]
NAMES = st.secrets["USERS"]
USERNAMES = st.secrets["USERNAMES"]
PASSWORDS = st.secrets["PASSWORDS"]

hashed_passwords = stauth.Hasher(PASSWORDS).generate()
authenticator = stauth.Authenticate(NAMES, USERNAMES, hashed_passwords, "yummy_cookie", "key", cookie_expiry_days=30)
Name, authentication_status, username = authenticator.login("LHT Login", "main")

credentials = service_account.Credentials.from_service_account_info(SERVICE_INFO, scopes=SCOPES)
service = build(serviceName="sheets", version="v4", credentials=credentials)

#st.set_page_config(page_title="Language Hour", page_icon="🌐", layout="centered")

def add_row(connector, sheet_name, row) -> None:
    connector.values().append(spreadsheetId=SPREADSHEET_ID,
    range=f"{sheet_name}!A:E",
    body=dict(values=row),
    valueInputOption="USER_ENTERED",
    ).execute()

def get_data(connector, sheet_name) -> pd.DataFrame:
    values = (connector.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{sheet_name}!A:E",
        ).execute()
    )
    df = pd.DataFrame(values["values"])
    df.columns = df.iloc[0]
    df = df[1:]
    return df

def main(form):
    with form:
        name = st.text_input(label="Name", value=Name, placeholder="Last name")
        listening = st.checkbox(label="Listening")
        reading = st.checkbox(label="Reading")
        speaking = st.checkbox(label="Speaking")
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
        if not any([listening, reading, speaking]) == True:
            st.error("You need to select at least 1 modality...")

        modality = ""
        if listening:
            modality += "L"
        if reading:
            modality += "R"
        if speaking:
            modality += "S"

        name = name.title()

        try:
            add_row(connector=service.spreadsheets(), sheet_name=name, row=[[str(date), minutes, modality, description]])
            st.success(f"Thanks {name.split()[0]}, your entry was submitted")
            expander = st.expander("show my entries")
            with expander:
                st.dataframe(get_data(connector=service.spreadsheets(), sheet_name=name))
            st.balloons()
        except Exception:
            st.error("Name does not exist")
            return

if authentication_status:
    #authenticator.logout('Logout', 'main')
    st.success("Login successful")
    st.title("Language Hour Entry")
    form = st.form(key="annotation")
    main(form)
elif authentication_status == False:
    st.error('Username/password is incorrect')
elif authentication_status == None:
    st.warning('Please enter your username and password')
    