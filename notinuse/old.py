import os
from io import BytesIO
from time import time
import pandas as pd
import streamlit as st
import streamlit_authenticator as stauth
from google.oauth2 import service_account
from googleapiclient.discovery import build, MediaFileUpload
from googleapiclient.http import MediaIoBaseDownload
from datetime import datetime


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


def create_folder(name):
    file_metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [FOLDER_ID],
    }
    folder = drive_service.files().create(body=file_metadata, fields="id").execute()
    return folder

def add_member(name, username, password, flags) -> None:
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

def format_modality(*args, **kwargs) -> str:
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

def get_folder_id(folder_name) -> str:
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'"
    file = drive_service.files().list(q=query, fields="files(id)").execute()
    return file["files"][0]["id"]

def upload_file(file, folder_name) -> None:
    with open(f"temp/{file.name}", "wb") as f:
        f.write(file.getbuffer())
    file_metadata = {
            "name": f"{file.name}",
            "parents": [get_folder_id(folder_name)],
        }
    media = MediaFileUpload(f"temp/{file.name}", mimetype="*/*")
    drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()

def get_files(folder_name):
    folder_id = get_folder_id(folder_name)
    query = f"parents = '{folder_id}'"
    response = drive_service.files().list(q=query).execute()
    files = response.get("files")
    nextPageToken = response.get("nextPageToken")
    while nextPageToken:
        response = drive_service.files().list(q=query).execute()
        files.extend(response.get("files"))
    return files

def download_file(file_id, file_name):
    request = drive_service.files().get_media(fileId=file_id)
    bytes_data = BytesIO()
    downloader = MediaIoBaseDownload(fd=bytes_data, request=request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    bytes_data.seek(0)
    with open(os.path.join("./LanguageHourFiles", file_name), "wb") as f:
        f.write(bytes_data.read())
        f.close()

def get_subs(name) -> list:
    df = get_data(column=None, sheet="Main", worksheet=LST, range="A:K")
    subs = df[["Name", "Supervisor"]].loc[df["Supervisor"] == name]
    return list(subs["Name"])

def calculate_hours_required(name):
    data = get_data(column="Hours", sheet=name, worksheet=LHT)

def calculate_hours_done(name):
    df = get_data(column=None, sheet=name, worksheet=LHT)
    this_month = datetime.now().date().month
    data = df[["Date", "Hours"]]
    hours = sum([int(d[1]) for d in data.values if int(d[0][5:7]) == this_month])
    return hours

def get_vocab(name):
    data = get_data(column="Vocab", sheet=name, worksheet=LHT)
    return data



def my_files_sidebar(user):
    button_data = []
    with st.expander(label="My Files"):
        files = get_files(user["Name"])
        if not files:
            st.write("No Files")
        for f in files:
            button_data.append(f)
            st.button(label=f["name"], key=f["id"])

def my_subs_sidebar(user):
    with st.expander(label="My Troops"):
        subs = get_subs(user["Name"])
        for s in subs:
            cols = st.columns(2)
            cols[0].button(label=s)
            cols[1].write(f"{calculate_hours_done(s)} hrs")

def file_download_sidebar(user):
    with st.expander(label="Download/Upload Files"):
        data = get_data(column=None, sheet=user["Name"], worksheet=LHT)
        st.download_button(label="📥 Download My Language Hours", data=to_excel(data), file_name="myLanguageHours.xlsx")
        vocab = pd.DataFrame(get_vocab(user["Name"]))
        st.download_button(label="Download My Vocab", data=to_excel(vocab), file_name="myVocab.xlsx")
        uploaded_file = st.file_uploader(label="Upload a 623A entry or ILTP", type=["pdf", "txt", "docx"])
        if uploaded_file:
            with st.spinner(text="uploading file..."):
                try:
                    upload_file(file=uploaded_file, folder_name=user["Name"])
                    st.sidebar.success("File uploaded successfully!")
                except:
                    st.sidebar.error("File upload failed")
            os.remove(f"temp/{uploaded_file.name}")

def my_account_sidebar(user):
    st.title("My Account")
    with st.expander(label="Update Account Info"):
        st.text_input(label="Name", value=user["Name"], disabled=True)
        st.text_input(label="Username", value=user["Username"])
        st.text_input(label="Password", value=user["Password"], type="password")
        if st.button(label="Save"):
            pass

def sidebars(user):
    my_account_sidebar(user)
    file_download_sidebar(user)
    my_files_sidebar(user)
    my_subs_sidebar(user)

def entry_page(user):
    st.title("Language Hour Entry")
    with st.sidebar:
        st.header(f"Welcome {user['Name']}")
        sidebars(user)

    with st.form(key="user_form"):
        cols = st.columns((2, 1, 1))
        name = cols[0].text_input(label="Name", value=user["Name"], placeholder="Last name", disabled=True)
        hours = cols[1].text_input(label=f"Hours - {sum_hours(name)} submitted")
        date = cols[2].date_input(label="Date")
        listening = cols[0].checkbox(label="Listening")
        reading = cols[0].checkbox(label="Reading")
        speaking = cols[0].checkbox(label="Speaking")
        cols = st.columns((2, 1))
        description = cols[0].text_area(label="Description", height=150, placeholder="describe what you did/understood/struggled with\nexample:\nlistened to lvl 2+ passages about politics in Lebanon etc...\nthen answered questions about it and scored 90%. etc")
        vocab = cols[1].text_area(label="Vocab", height=150, placeholder="list the vocab you learned or reviewed:\nبطيخ - watermelon\nاحتكار - monopoly")
        cols = st.columns(2)
        if cols[0].form_submit_button("Submit"):
            modality = format_modality(listening=listening, reading=reading, speaking=speaking)
            add_entry(worksheet=LHT, sheet=name, data=[[str(date), float(hours), modality, description, ",".join(vocab.split())]])
            st.success(f"Thanks {name.split(',')[1]}! Your entry has been submitted")
            st.balloons()

    expander = st.expander("Show my Language Hour entries")
    data = get_data(column=None, sheet=user["Name"], worksheet=LHT)
    with expander:
        st.dataframe(data)

def admin_sidebar(user):
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

        with st.expander(label="Update Information"):
            with st.form(key="update_member"):
                lst_data = get_data(column="Name", sheet="Main", worksheet=LST, range="A:K")
                lht_data = get_data(column="Name", sheet="Members", worksheet=LHT, range="A:D")
                st.selectbox(label="Name", options=lst_data)
                st.form_submit_button(label="Update Info")

        st.write(f"[Language Score Tracker]({LST_URL})")
        st.write(f"[Language Hour Tracker]({LHT_URL})")
        st.write(f"[Google Drive]({DRIVE_URL})")

def is_admin(user) -> bool:
    df = get_data(column=None, sheet="Members", worksheet=LHT)
    output = df.query(f"Name == '{user['Name']}'")["Flags"]
    return True if list(output)[0] is not None else False

def authenticate_user(username, password):
        users = get_data(column=None, sheet="Members", worksheet=LHT)
        user = users.loc[users["Username"] == username]
        if user.empty:
            return
        if password == user["Password"].values:
            return user.to_dict("records")[0]
        return

def login():
    #status = False
    #if st.session_state['authentication_status'] != True:
    #    container = st.empty()
    #    with container.container():
    #        login_form = st.form("Login")
    #        login_form.subheader("Login")
    #        username = login_form.text_input(label="Username")
    #        st.session_state["username"] = username
    #        password = login_form.text_input(label="Password", type="password")
    #        if login_form.form_submit_button("Login"):
    #            status, user = authenticate_user(username, password)
    #if status:
    #    container.empty()
    #    with st.spinner(text="loading..."):
    #        entry_page(user)
    #        if is_admin(user):
    #            admin_sidebar(user)
    #if status == False or not status:
    #    st.error("Could not login. Check username and password.")

    #status = False
    #st.subheader("Language Hour Login")
    #username = st.text_input(label="Username")
    #password = st.text_input(label="Password", type="password")
    #if st.button("Login"):
    #    status, user = authenticate_user(username, password)
    #
    #if status:
    #    entry_page(user)
    #    if is_admin(user):
    #        admin_sidebar(user)

    users = get_data(column=None, sheet="Members", worksheet=LHT)
    hashed_passwords = stauth.Hasher(users["Password"].tolist()).generate()
    authenticator = stauth.Authenticate(users["Name"].tolist(), users["Username"].tolist(), hashed_passwords, "lht_cookie", "lht", cookie_expiry_days=30)
    name, authentication_status, username = authenticator.login("Language Hour Tracker Login", "main")
    user = authenticate_user(username, PASSWORD)

    if authentication_status:
        with st.spinner(text="loading..."):
            entry_page(user)
            if is_admin(user):
                admin_sidebar(user)
        authenticator.logout("Logout", location="sidebar")
    elif authentication_status == False:
        st.error('Username or password is incorrect')
    elif authentication_status == None:
        pass

login()