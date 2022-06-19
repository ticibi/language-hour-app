from io import BytesIO
from time import time
import pandas as pd
import streamlit as st
import streamlit_authenticator as stauth
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive",]
LHT = st.secrets["LHT_SHEET_ID"]
LST = st.secrets["LST_SHEET_ID"]
USER_SHEET = st.secrets["USER_SHEET"]
USER_SHEET_ID = st.secrets["USER_SHEET_ID"]
SERVICE_INFO = st.secrets["google_service_account"]
PASSWORD = st.secrets["PASSWORD"]

st.set_page_config(page_title="Language Hour Entry", page_icon="🌐", layout="centered")
credentials = service_account.Credentials.from_service_account_info(info=SERVICE_INFO, scopes=SCOPES)
service = build(serviceName="sheets", version="v4", credentials=credentials)

def timeit(func):
    def wrapper(*args, **kwargs):
        start = time()
        output = func(*args, **kwargs)
        stop = time()
        print(func.__name__, "executed in", int((stop - start) * 1000), "ms")
        return output
    return wrapper

@timeit
def get_data(column, sheet, worksheet):
    values = (CONNECTOR.values().get(
        spreadsheetId=worksheet,
        range=f"{sheet}!A:E",
        ).execute()
    )
    df = pd.DataFrame(values["values"])
    df.columns = df.iloc[0]
    df = df[1:]
    return df[column].tolist() if column is not None else df

@timeit
def add_entry(worksheet, sheet, data):
    CONNECTOR.values().append(
        spreadsheetId=worksheet,
        range=f"{sheet}!A:E",
        body=dict(values=data),
        valueInputOption="USER_ENTERED",
    ).execute()

def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, index=False, sheet_name="Sheet1")
    writer.save()
    data = output.getvalue()
    return data

def sum_hours(name):
    hours = get_data(column="Hours", sheet=name, worksheet=LHT)
    return sum([float(hr) for hr in hours])

def format_modality(*args, **kwargs):
    output = ""
    if kwargs["listening"]:
        output += "L"
    if kwargs["reading"]:
        output += "R"
    if kwargs["speaking"]:
        output += "S"
    return output

CONNECTOR = service.spreadsheets()

user_data = get_data(column=None, sheet="Members", worksheet=LHT)
hashed_passwords = stauth.Hasher(user_data["Password"].tolist()).generate()
authenticator = stauth.Authenticate(user_data["Name"].tolist(), user_data["Username"].tolist(), hashed_passwords, "lht_cookie", "lht", cookie_expiry_days=30)
Name, authentication_status, username = authenticator.login("Language Hour Tracker Login", "main")

if authentication_status:
    st.title("Language Hour Entry")
    form = st.form(key="user_form", clear_on_submit=True)
    with form:
        cols = st.columns((2, 1, 1))
        name = cols[0].text_input(label="Name", value=Name, placeholder="Last name", disabled=True)
        hours = cols[1].text_input(label=f"Hours - {sum_hours(name)} submitted")
        date = cols[2].date_input(label="Date")
        listening = cols[0].checkbox(label="Listening")
        reading = cols[0].checkbox(label="Reading")
        speaking = cols[0].checkbox(label="Speaking")
        cols = st.columns((2, 1))
        description = cols[0].text_area(label="Description", height=150, placeholder="describe what you did/understood/struggled with\nexample:\nlistened to lvl 2+ passages about politics in Lebanon etc...\nthen answered questions about it and scored 90%. etc")
        vocab = cols[1].text_area(label="Vocab", height=150, placeholder="list the vocab you learned and/or reviewed\nexample:\nبطيخ - watermelon\nاحتكار - monopoly")
        cols = st.columns(2)
        uploaded_file = st.file_uploader(label="or upload a 623A")
        submitted = cols[0].form_submit_button(label="Submit")

    if submitted:
        modality = format_modality(listening=listening, reading=reading, speaking=speaking)
        add_entry(worksheet=LHT, sheet=name, data=[[str(date), float(hours), modality, description, ",".join(vocab.split())]])
        st.success(f"Thanks {name.split(',')[1]}! Your entry has been submitted")
        st.balloons()

    expander = st.expander("Show my Language Hour entries")
    data = get_data(column=None, sheet=Name, worksheet=LHT)
    with expander:
        st.dataframe(data)

    st.download_button(label="📥 Download my Language Hours", data=to_excel(data), file_name="myLanguageHours.xlsx", key="download")
    authenticator.logout("Logout")

elif authentication_status == False:
    st.error('Username or password is incorrect')

elif authentication_status == None:
    pass
