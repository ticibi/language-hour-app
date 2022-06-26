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
from utils import initialize_session_state

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

initial_vars = ['authentication_status', 'logout', 'user']
initialize_session_state(initial_vars)

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

def add_member(data, flags):
    # create folder on the drive with the users name
    try:
        create_folder(data['Name'])
        st.sidebar.success("created folder")
    except:
        st.sidebar.error("could not create folder")
    # add user info to the Members sheet on LHT
    body = {
        "requests": [
            {
                "addSheet": {
                    "properties": {
                        "title": data['Name'],
                    }
                }
            }
        ]
    }
    # create a new tab with the users name
    try:
        response = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=USER_SHEET_ID,
            body=body
        ).execute()
        st.sidebar.success("created member sheet")
    except:
        st.sidebar.error("could not add member sheet")
    lht_data = [data['Name'], data['Username'], data['Password'], flags]
    #add_entry(worksheet=LHT, sheet="Members", data=lht_data, range="A:D")
    #add_entry(worksheet=LST, sheet="Main", data=data.values(), range="A:K")

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

def get_sheet_id(name):
    sheet_id = None
    spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=LHT).execute()
    for sheet in spreadsheet['sheets']:
        if sheet['properties']['title'] == name:
            sheet_id = sheet['properties']['sheetId']
    return sheet_id

def remove_member(name):
    sheet_id = get_sheet_id(name)
    body = {
        "requests": [
            {
                "deleteSheet": {
                    "sheetId": sheet_id,
                }
            }
        ]
    }
    try:
        response = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=LHT, body=body
        ).execute()
    except:
        st.error("could not remove member")
    data = get_data(column=None, sheet="Members", worksheet=LST)
    index = data.index[data["Name"] == name].tolist()[0]
    body = {
        "requests": [
            {
                "deleteDimension": {
                    "range": {
                        "sheetId": LST,
                        "dimension": "ROWS",
                        "startIndex": index,
                        "endIndex": index + 1,
                    }
                }
            }
        ]
    }
    try:
        response = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=LST, body=body
        ).execute()
    except:
        st.error("could not remove member")
    st.success("member removed!")

def my_files_sidebar(user):
    button_data = []
    buttons = []
    with st.expander(label="My Files"):
        files = get_files(user["Name"])
        if not files:
            st.write("No Files")
        for f in files:
            button_data.append(f)
            button = st.button(label=f["name"], key=f["id"])
            buttons.append(button)

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

def developer_sidebar(user):
    # input score tracker id
    # input hour tracker id
    # input drive folder id
    st.write(st.session_state)
    with st.sidebar:
        st.subheader("Developer Tools")
        with st.expander("Link Google Services"):
            st.text_input("1", key=f"add_input_1")
            st.text_input("2", key=f"add_input_2")
            st.text_input("3", key=f"add_input_3")

def entry_page(user):
    st.title("Language Hour Entry")
    with st.sidebar:
        st.header(f"Welcome {user['Name']}!")
        sidebars(user)

    form = st.form("entry", clear_on_submit=True)
    with form:
        cols = st.columns((2, 1, 1))
        name = cols[0].text_input("Name", value=user["Name"], placeholder="Last name", disabled=True)
        hours = cols[1].text_input(f"Hours - {sum_hours(name)} submitted")
        date = cols[2].date_input("Date")
        listening = cols[0].checkbox("Listening")
        reading = cols[0].checkbox("Reading")
        speaking = cols[0].checkbox("Speaking")
        cols = st.columns((2, 1))
        description = cols[0].text_area("Description", height=150, placeholder="describe what you did/understood/struggled with\nexample:\nlistened to lvl 2+ passages about politics in Lebanon etc...\nthen answered questions about it and scored 90%. etc")
        vocab = cols[1].text_area("Vocab", height=150, placeholder="list the vocab you learned or reviewed:\nبطيخ - watermelon\nاحتكار - monopoly")
        cols = st.columns(2)
        submit = cols[0].form_submit_button("Submit")
        if submit:
            modality = format_modality(listening=listening, reading=reading, speaking=speaking)
            add_entry(worksheet=LHT, sheet=name, data=[[str(date), float(hours), modality, description, ",".join(vocab.split())]])
            st.success(f"Thanks {name.split(',')[1]}! Your entry has been submitted")
            st.balloons()

        with st.expander("Show my Language Hour entries", expanded=True):
            data = get_data(column=None, sheet=user["Name"], worksheet=LHT)
            st.dataframe(data)

def admin_sidebar(user):
    def add_member_expander():
        with st.expander(label="Add Member"):
            with st.form(key="add_member"):
                lst_data = get_data(column="Name", sheet="Main", worksheet=LST, range="A:K")
                name = st.text_input(label="Name", placeholder="Last, First")
                username = st.text_input(label="Username", placeholder="jsmith")
                clang = st.selectbox(label="CLang", options=["AP", "AD", "DG",])
                iltp = st.text_input(label="ILTP Status", placeholder="ILTP or RLTP")
                slte = st.date_input(label="SLTE Date")
                dlpt = st.date_input(label="DLPT Date")
                cll = st.text_input(label="CL - Listening")
                msal = st.text_input(label="MSA - Listening")
                msar = st.text_input(label="MSA - Reading")
                dialects = st.text_input(label="Dialects", placeholder="with only score of 2 or higher")
                mentor = st.text_input(label="Mentor")
                supe = st.selectbox(label="Supervisor", options=lst_data)
                flags = st.text_input(label="Flags")
                if st.form_submit_button(label="Add Member"):
                    data = {
                        "Name":name,
                        "Username":username,
                        "Password":PASSWORD,
                        "CLang":clang,
                        "ILTP":iltp,
                        "SLTE Date":str(slte),
                        "DLPT Date":str(dlpt),
                        "CL - Listening":cll,
                        "MSA - Listening":msal,
                        "MSA - Reading":msar,
                        "Dialects":dialects,
                        "Mentor":mentor,
                        "Supervisor":supe,
                    }
                    add_member(data, flags)

    def remove_member_expander():
        with st.expander(label="Remove Member"):
            with st.form(key="remove_member"):
                lst_data = get_data(column="Name", sheet="Main", worksheet=LST, range="A:K")
                lht_data = get_data(column="Name", sheet="Members", worksheet=LHT, range="A:D")
                st.selectbox(label="Name", options=lst_data)
                st.form_submit_button(label="Remove Member")

    def update_info_expander():
        with st.expander(label="Update Information"):
            with st.form(key="update_member"):
                lst_data = get_data(column="Name", sheet="Main", worksheet=LST, range="A:K")
                st.selectbox(label="Name", options=lst_data)
                st.form_submit_button(label="Update Info")

    with st.sidebar:
        st.header("Admin Tools")
        add_member_expander()
        remove_member_expander()
        update_info_expander()
        st.write(f"[Language Score Tracker]({LST_URL})")
        st.write(f"[Language Hour Tracker]({LHT_URL})")
        st.write(f"[Google Drive]({DRIVE_URL})")

def check_perms(user) -> bool:
    df = get_data(column=None, sheet="Members", worksheet=LHT)
    output = df.query(f"Name == '{user['Name']}'")["Flags"]
    return True if list(output)[0] is not None else False

def authenticate(username, password) -> bool:
        users = get_data(column=None, sheet="Members", worksheet=LHT)
        user = users.loc[users["Username"] == username]
        if user.empty:
            st.session_state.authentication_status = False
            return False
        if password == user["Password"].values:
            user_data = user.to_dict("records")[0]
            st.session_state.user = user_data
            st.session_state.authentication_status = True
            return True
        else:
            st.session_state.authentication_status = False
            return False

def login(form_name) -> tuple:
    if not st.session_state.authentication_status:
        if st.session_state.authentication_status != True:
            login_form = st.form('Login')
            login_form.subheader(form_name)
            username = login_form.text_input(label="Username").lower()
            password = login_form.text_input(label="Password", type="password")
            if login_form.form_submit_button("Login"):
                authenticate(username, password)
                
    return st.session_state.authentication_status, st.session_state.user

def logout() -> None:
    st.session_state.logout= True
    st.session_state.authentication_status = None
    st.session_state.user = None

username = "tbresee"
users = get_data(column=None, sheet="Members", worksheet=LHT)
user = users.loc[users["Username"] == username]
user_data = user.to_dict("records")[0]
st.session_state.user = user_data
entry_page(user_data)
#admin_sidebar(user_data)
#developer_sidebar(user_data)

#status, user = login("Language Hour Login")
#if status: #st.session_state.authentication_status:
#    with st.spinner(text="loading..."):
#        entry_page(user)
#        if check_perms(user):
#            admin_sidebar(user)
#            developer_sidebar(user)
#elif status == False: #st.session_state.authentication_status == False:
#    st.error("incorrect username or password")
#elif status == None: #st.session_state.authentication_status == None:
#    st.info('enter your username and password')


#users = get_data(column=None, sheet="Members", worksheet=LHT)
#hashed_passwords = stauth.Hasher(users["Password"].tolist()).generate()
#authenticator = stauth.Authenticate(users["Name"].tolist(), users["Username"].tolist(), hashed_passwords, "lht_cookie", "lht", cookie_expiry_days=30)
#name, authentication_status, username = authenticator.login("Language Hour Tracker Login", "main")
#user = authenticate_user(username, PASSWORD)
#
#if authentication_status:
#    with st.spinner(text="loading..."):
#        entry_page(user)
#        if is_admin(user):
#            admin_sidebar(user)
#    authenticator.logout("Logout", location="sidebar")
#elif authentication_status == False:
#    st.error('Username or password is incorrect')
#elif authentication_status == None:
#    pass
#

def get_files(name):
    folder_id = get_folder_id(name)
    query = f"parents = '{folder_id}'"
    response = drive_service.files().list(q=query).execute()
    files = response.get("files")
    nextPageToken = response.get("nextPageToken")
    while nextPageToken:
        response = drive_service.files().list(q=query).execute()
        files.extend(response.get("files"))
    return files

def get_folder_id(name) -> str:
    query = f"mimeType='application/vnd.google-apps.folder' and name='{name}'"
    file = drive_service.files().list(q=query, fields="files({})").execute()
    return file["files"][0]["id"]

def upload_file(file, folder):
    '''upload file onto the google drive into the destination folder'''
    with open(f"temp/{file.name}", "wb") as f:
        f.write(file.getbuffer())
    file_metadata = {
            "name": f"{file.name}",
            "parents": [get_folder_id(folder)],
        }
    media = MediaFileUpload(f"temp/{file.name}", mimetype="*/*")
    drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()

def add_entry(worksheet_id, sheet_name, data:list, range="A:K"):
    service.sheets.spreadsheets().values().append(
        spreadsheetId=worksheet_id,
        range=f"{sheet_name}!{range}",
        body=dict(values=data),
        valueInputOption="USER_ENTERED",
    ).execute()

def get_data(column, worksheet_id, sheet_name, range="A:K"):
    try:
        values = (service.sheets.spreadsheets().values().get(
            spreadsheetId=worksheet_id,
            range=f"{sheet_name}!{range}",
            ).execute()
        )
        df = pd.DataFrame(values["values"])
        df.columns = df.iloc[0]
        df = df[1:]
    except Exception as e:
        print(e)
        return None
    return df[column].tolist() if column is not None else df

def test_get_data(columns, worksheet_id, sheet_name, range='A:D'):
    values = (service.sheets.spreadsheets().values().get(
        spreadsheetId=worksheet_id,
        range=f"{sheet_name}!{range}",
        ).execute()
    )
    df = pd.DataFrame(values['values'])
    df.columns = df.iloc[0]
    df = df[1:]
    return df.get(columns)

x = test_get_data(columns=['Name', 'Username'], worksheet_id=LHT_ID, sheet_name='Members', range='A:D')

def calculate_hours_required(name):
    # check for dialect scores
    def check(score:str):
        s = score
        output = 0.0
        if '+' in score:
            output += 0.5
            s = s.replace('+', '')
        output += float(s)
        return output

    table = {
        '5.5': 2,
        '5.0': 4,
        '4.5': 6,
        '4.0': 8,
    }
    data = st.session_state.main
    if data is None:
        return 0
    try:
        data = data.query(f'Name == "{name}"')[['CLang', 'CL - Listening', 'MSA - Listening', 'MSA - Reading']].values.tolist()[0]
    except:
        return 0
    total = 0.0
    match data[0]:
        case 'AD':
            total = sum([check(data[2]), check(data[3])])
        case _:
            total = sum([check(data[1]), check(data[3])])
    if total < 4:
        return 12
    elif total >= 6:
        return 0
    else:
        return table[str(total)]

















