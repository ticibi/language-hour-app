import pandas as pd
import streamlit as st
import streamlit_authenticator as stauth
from google.oauth2 import service_account
from googleapiclient.discovery import build
from io import BytesIO


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = st.secrets["SPREADSHEET_ID"]
SERVICE_INFO = st.secrets["google_service_account"]
USER_SHEET = st.secrets["USER_SHEET"]
#NAMES = st.secrets["USERS"]
#USERNAMES = st.secrets["USERNAMES"]
#PASSWORDS = st.secrets["PASSWORDS"]

st.set_page_config(page_title="Language Hour Entry", page_icon="🌐", layout="centered")

credentials = service_account.Credentials.from_service_account_info(SERVICE_INFO, scopes=SCOPES)
service = build(serviceName="sheets", version="v4", credentials=credentials)

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

def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, index=False, sheet_name="Sheet1")
    writer.save()
    data = output.getvalue()
    return data

def calculate_total_hours(name):
    pass

user_data = get_data(connector=service.spreadsheets(), sheet_name=USER_SHEET)
NAMES = user_data["Name"].tolist()
USERNAMES = user_data["Username"].tolist()
PASSWORDS = user_data["Password"].tolist()

hashed_passwords = stauth.Hasher(PASSWORDS).generate()
authenticator = stauth.Authenticate(NAMES, USERNAMES, hashed_passwords, "yummy_cookie", "key", cookie_expiry_days=30)
Name, authentication_status, username = authenticator.login("Language Hour Tracker Login", "main")

def main(form):
    with form:
        cols = st.columns(2)
        name = cols[0].text_input(label="Name", value=Name, placeholder="Last name", disabled=True)
        supervisor = cols[1].selectbox(label="Supervisor", options=NAMES)
        cols = st.columns((2, 1, 1))
        minutes = cols[1].number_input(label="Minutes", min_value=0, max_value=240, step=15)
        date = cols[2].date_input(label="Date")
        listening = cols[0].checkbox(label="Listening")
        reading = cols[0].checkbox(label="Reading")
        speaking = cols[0].checkbox(label="Speaking")
        description = st.text_area(label="Description", height=100, placeholder="what did you study?")
        cols = st.columns(2)
        cols = st.columns(2)
        submitted = cols[0].form_submit_button(label="Submit")

    name = name.title()

    if not name in NAMES:
        st.error("Name does not exist")
        return

    data = get_data(connector=service.spreadsheets(), sheet_name=name)
    st.download_button(label="📥 Download myLanguageHours", data=to_excel(data), file_name="myLanguageHours.xlsx")

    if submitted:
        if len(description) < 1:
            st.error("You need to include what you studied...")
            return
        if minutes <= 0:
            st.error("You need to study longer than 0 minutes...")
            return
        if not any([listening, reading, speaking]) == True:
            st.error("You need to select at least 1 modality...")
            return

        modality = ""
        if listening:
            modality += "L"
        if reading:
            modality += "R"
        if speaking:
            modality += "S"

        add_row(connector=service.spreadsheets(), sheet_name=name, row=[[str(date), minutes, modality, description]])
        st.success(f"Thanks {name}! Your entry has been submitted")
        expander = st.expander("Show my entries")
        with expander:
            st.dataframe(get_data(connector=service.spreadsheets(), sheet_name=name))
        st.balloons()


if authentication_status:
    #st.success("Login successful")
    st.title("Language Hour Entry")
    form = st.form(key="annotation")
    main(form)
elif authentication_status == False:
    st.error('Username/password is incorrect')
elif authentication_status == None:
    st.warning('Please enter your username and password')
    
