import os
from io import BytesIO
from time import time
import pandas as pd
import streamlit as st
import streamlit_authenticator as stauth
from google.oauth2 import service_account
from googleapiclient.discovery import build, MediaFileUpload



SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.metadata",
]
LHT = st.secrets["LHT_SHEET_ID"]
LST = st.secrets["LST_SHEET_ID"]
USER_SHEET_ID = st.secrets["USER_SHEET_ID"]
SERVICE_INFO = st.secrets["service_account"]
PASSWORD = st.secrets["PASSWORD"]
LST_URL = st.secrets["LST_URL"]
LHT_URL = st.secrets["LHT_URL"]
FOLDER_ID = st.secrets["FOLDER_ID"]
DRIVE_URL = st.secrets["DRIVE_URL"]


st.set_page_config(page_title="Language Hour Entry", page_icon="🌐", layout="centered")
credentials = service_account.Credentials.from_service_account_info(info=SERVICE_INFO, scopes=SCOPES)
sheets_service = build(serviceName="sheets", version="v4", credentials=credentials)
drive_service = build(serviceName="drive", version="v3", credentials=credentials)


def format_modality(*args, **kwargs):
    output = ""
    if kwargs["listening"]:
        output += "L"
    if kwargs["reading"]:
        output += "R"
    if kwargs["speaking"]:
        output += "S"
    return output

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

def timeit(func):
    def wrapper(*args, **kwargs):
        start = time()
        output = func(*args, **kwargs)
        stop = time()
        print(func.__name__, "executed in", int((stop - start) * 1000), "ms")
        return output
    return wrapper

@st.cache
def get_data(column, sheet, worksheet, range="A:E"):
    values = (sheets_service.spreadsheets().values().get(
        spreadsheetId=worksheet,
        range=f"{sheet}!{range}",
        ).execute()
    )
    df = pd.DataFrame(values["values"])
    df.columns = df.iloc[0]
    df = df[1:]
    return df[column].tolist() if column is not None else df

def add_entry(worksheet, sheet, data:list, range="A:E"):
    sheets_service.spreadsheets().values().append(
        spreadsheetId=worksheet,
        range=f"{sheet}!{range}",
        body=dict(values=data),
        valueInputOption="USER_ENTERED",
    ).execute()

def get_folder_id(name):
    query = f"mimeType='application/vnd.google-apps.folder' and name='{name}'"
    file = drive_service.files().list(q=query, fields="files(id)").execute()
    return file["files"][0]["id"]

def upload_file(file, folder_name):
        with open(f"temp/{file.name}", "wb") as f:
            f.write(file.getbuffer())
        file_metadata = {
                "name": f"{file.name}",
                "parents": [get_folder_id(folder_name)],
            }
        media = MediaFileUpload(f"temp/{file.name}", mimetype="*/*")
        drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()

def entry_page(*args, **kwargs):
    st.title("Language Hour Entry")
    with st.sidebar:
        st.header(f"Welcome {kwargs['name'].split(',')[1]}")
        if st.button("Update My Info"):
            account_page(args, kwargs)
        data = get_data(column=None, sheet=kwargs["name"], worksheet=LHT)
        st.download_button(label="📥 Download my Language Hours", data=to_excel(data), file_name="myLanguageHours.xlsx")
        uploaded_file = st.file_uploader(label="Upload a 623A entry or ILTP", type=["pdf", "txt", "docx"])

    form = st.form(key="user_form", clear_on_submit=True)
    with form:
        cols = st.columns((2, 1, 1))
        name = cols[0].text_input(label="Name", value=kwargs['name'], placeholder="Last name", disabled=True)
        hours = cols[1].text_input(label=f"Hours - {sum_hours(name)} submitted")
        date = cols[2].date_input(label="Date")
        listening = cols[0].checkbox(label="Listening")
        reading = cols[0].checkbox(label="Reading")
        speaking = cols[0].checkbox(label="Speaking")
        cols = st.columns((2, 1))
        description = cols[0].text_area(label="Description", height=150, placeholder="describe what you did/understood/struggled with\nexample:\nlistened to lvl 2+ passages about politics in Lebanon etc...\nthen answered questions about it and scored 90%. etc")
        vocab = cols[1].text_area(label="Vocab", height=150, placeholder="list the vocab you learned and/or reviewed\nexample:\nبطيخ - watermelon\nاحتكار - monopoly")
        cols = st.columns(2)
        submitted = cols[0].form_submit_button(label="Submit")

    if uploaded_file:
        with st.spinner(text="uploading file..."):
            try:
                upload_file(file=uploaded_file, folder_name=name)
                st.sidebar.success("File uploaded successfully!")
            except:
                st.sidebar.error("File upload failed")
        os.remove(f"temp/{uploaded_file.name}")

    if submitted:
        modality = format_modality(listening=listening, reading=reading, speaking=speaking)
        add_entry(worksheet=LHT, sheet=name, data=[[str(date), float(hours), modality, description, ",".join(vocab.split())]])
        st.success(f"Thanks {name.split(',')[1]}! Your entry has been submitted")
        st.balloons()

    expander = st.expander("Show my Language Hour entries")
    data = get_data(column=None, sheet=kwargs["name"], worksheet=LHT)
    with expander:
        st.dataframe(data)

def admin_page(*args, **kwargs):
    with st.sidebar:
        st.header("Admin Tools")
        with st.expander(label="Add Member"):
            with st.form(key="add_member"):
                lst_data = get_data(column="Name", sheet="Main", worksheet=LST, range="A:K")
                st.text_input(label="Name", placeholder="Last, First")
                st.text_input(label="Username", placeholder="jsmith")
                st.selectbox(label="CLang", options=["AP", "AD", "DG",])
                st.text_input(label="ILTP Status", placeholder="ILTP or RLTP")
                st.date_input(label="SLTE Date")
                st.date_input(label="DLPT Date")
                st.text_input(label="CL - Listening")
                st.text_input(label="MSA - Listening")
                st.text_input(label="MSA - Reading")
                st.text_input(label="Dialects", placeholder="with only score of 2 or higher")
                st.text_input(label="Mentor")
                st.selectbox(label="Supervisor", options=lst_data)
                st.form_submit_button(label="Add Member")

        with st.expander(label="Remove Member"):
            with st.form(key="remove_member"):
                lst_data = get_data(column="Name", sheet="Main", worksheet=LST, range="A:K")
                lht_data = get_data(column="Name", sheet="Members", worksheet=LHT, range="A:D")
                st.selectbox(label="Name", options=lst_data)
                st.form_submit_button(label="Remove Member")

        def update_member_data(name):
            pass

        with st.expander(label="Update Information"):
            with st.form(key="update_member"):
                lst_data = get_data(column="Name", sheet="Main", worksheet=LST, range="A:K")
                lht_data = get_data(column="Name", sheet="Members", worksheet=LHT, range="A:D")
                st.selectbox(label="Name", options=lst_data)
                st.form_submit_button(label="Update Info")

        #st.text_input(label="Query", placeholder="search terms")
        st.write(f"Go to [Language Score Tracker]({LST_URL})")
        st.write(f"Go to [Language Hour Tracker]({LHT_URL})")
        st.write(f"Go to [Google Drive]({DRIVE_URL})")

    # update info
    # search, download user entry
    # download complete tracker
    pass

def account_page(*args, **kwargs):
    st.title("My Info")
    form = st.form(key="info_form")
    with form:
        lst_data = get_data(column="Name", sheet="Main", worksheet=LST, range="A:K")
        st.text_input(label="Name")
        st.text_input(label="Username")
        st.selectbox(label="CLang", options=["AP", "AD", "DG",])
        st.text_input(label="ILTP Status")
        st.date_input(label="SLTE Date")
        st.date_input(label="DLPT Date")
        st.text_input(label="CL - Listening")
        st.text_input(label="MSA - Listening")
        st.text_input(label="MSA - Reading")
        st.text_input(label="Dialects", placeholder="dialect 1+, dialect 3...")
        st.text_input(label="Mentor")
        st.selectbox(label="Supervisor", options=lst_data)

def create_folder(name):
    file_metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [FOLDER_ID],
    }
    file = drive_service.files().create(body=file_metadata, fields="id").execute()
    return file

def add_member(name, username, password, flags):
    data = [name, username, password, flags]
    # add user info to the Members sheet on LHT
    add_entry(worksheet=LHT, sheet="Members", data=data, range="A:D")
    body = {
        "requests": [
            {
                "addSheet": {
                    "properties": {
                        "title": name,
                    }
                }
            }
        ]
    }
    # create a new tab with the users name
    response = sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=USER_SHEET_ID,
        body=body
    ).execute()
    # create folder on the drive with the users name
    create_folder(name)
    
def check_permissions(name) -> bool:
    df = get_data(column=None, sheet="Members", worksheet=LHT)
    output = df.query(f"Name == '{name}'")["Flags"]
    return True if output is not None else False

def login():
    user_data = get_data(column=None, sheet="Members", worksheet=LHT)
    hashed_passwords = stauth.Hasher(user_data["Password"].tolist()).generate()
    authenticator = stauth.Authenticate(user_data["Name"].tolist(), user_data["Username"].tolist(), hashed_passwords, "lht_cookie", "lht", cookie_expiry_days=30)
    name, authentication_status, username = authenticator.login("Language Hour Tracker Login", "main")

    if authentication_status:
        with st.spinner(text="loading..."):
            entry_page(authenticator=authenticator, name=name, username=username)
            if check_permissions(name):
                admin_page(authenticator=authenticator, name=name, username=username)
        authenticator.logout("Logout", location="sidebar")
    elif not authentication_status:
        st.error('Username or password is incorrect')
    elif authentication_status == None:
        pass

login()
