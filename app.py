from tabnanny import check
from types import NoneType
import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from utils import initialize_session_state
from datetime import datetime


SERVICE_INFO = st.secrets['service_account']
LHT_ID = st.secrets['LHT_ID']
LST_ID = st.secrets['LST_ID']
FOLDER_ID = st.secrets['FOLDER_ID']
LST_URL = st.secrets['LST_URL']
LHT_URL = st.secrets['LHT_URL']
DRIVE_URL = st.secrets['DRIVE_URL']
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.metadata",
]

session_vars = ['logged_in', 'user', 'admin', 'dev']
initialize_session_state(session_vars)

st.set_page_config(page_title="Language Hour Entry", page_icon="🌐", layout="centered")
credentials = service_account.Credentials.from_service_account_info(info=SERVICE_INFO, scopes=SCOPES)
sheets_service = build(serviceName="sheets", version="v4", credentials=credentials)
drive_service = build(serviceName="drive", version="v3", credentials=credentials)

def get_folder_id(folder_name) -> str:
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'"
    file = drive_service.files().list(q=query, fields="files(id)").execute()
    return file["files"][0]["id"]

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

def calculate_hours_done_this_month(name):
    data = get_data(column=None, worksheet_id=LHT_ID, sheet_name=name)
    this_month = datetime.now().date().month
    data = data[['Date', 'Hours']]
    hours = sum([int(d[1]) for d in data.values if int(d[0][5:7]) == this_month])
    return hours

def get_subs(name) -> list:
    df = get_data(column=None, sheet_name="Main", worksheet_id=LST_ID, range="A:K")
    subs = df[["Name", "Supervisor"]].loc[df["Supervisor"] == name]
    return subs.to_dict('records')

def add_entry(worksheet_id, sheet_name, data:list, range="A:K"):
    sheets_service.spreadsheets().values().append(
        spreadsheetId=worksheet_id,
        range=f"{sheet_name}!{range}",
        body=dict(values=data),
        valueInputOption="USER_ENTERED",
    ).execute()

def get_data(column, worksheet_id, sheet_name, range="A:K"):
    values = (sheets_service.spreadsheets().values().get(
        spreadsheetId=worksheet_id,
        range=f"{sheet_name}!{range}",
        ).execute()
    )
    df = pd.DataFrame(values["values"])
    df.columns = df.iloc[0]
    df = df[1:]
    return df[column].tolist() if column is not None else df

def check_flags():
    data = get_data(column=None, worksheet_id=LHT_ID, sheet_name='Members')
    flags = data.query(f'Name == "{st.session_state.user["Name"]}"')['Flags']
    flags = flags.tolist()[0]
    if flags != None:
        flags = flags.strip()
        flags = flags.split(',')
        return flags
    return None

def authenticate(username, password) -> bool:
    data = None
    try:
        data = get_data(column=None, worksheet_id=LHT_ID, sheet_name='Members')
    except Exception as e:
        raise e

    if data is not None:
        try:
            user = data.loc[data['Username'] == username]
        except:
            st.error('incorrect username or password :(')
    
        user = user.to_dict('records')[0]
        if user['Password'] == password:
            user.pop('Password')
            st.session_state.user = user
            st.session_state.logged_in = True
        else:
            st.error('incorrect username or password')
    else:
        st.session_state.user = None
        st.session_state.logged_in = False

def logout():
    for state in st.session_state:
        st.session_state[state] = None

def login():
    if not st.session_state.logged_in:
        with st.form('Language Hour Login'):
            st.subheader('Login')
            username = st.text_input('Username').lower()
            password = st.text_input('Password', type='password')
            login = st.form_submit_button('Login')
            if login:
                authenticate(username, password)

def adminbar():
    st.sidebar.subheader('Admin')
    with st.sidebar:
        with st.expander('Add Member'):
            with st.form('Add Member'):
                data = get_data(column=None, worksheet_id=LST_ID, sheet_name='Main')
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
                supe = st.selectbox(label="Supervisor", options=[])
                flags = st.multiselect(label="Flags", options=['admin', 'dev'])
                submit = st.form_submit_button('Add Member')
                if submit:
                    pass

        st.write(f"[Language Score Tracker]({LST_URL})")
        st.write(f"[Language Hour Tracker]({LHT_URL})")
        st.write(f"[Google Drive]({DRIVE_URL})")

def devbar():
    st.sidebar.subheader('Developer')
    with st.sidebar:
        with st.expander(''):
            st.write('meow')

def sidebar():
    def show_dataframe(name):
        data = get_data(column=None, worksheet_id=LHT_ID, sheet_name=name)
        st.dataframe(data, width=300)

    with st.sidebar:
        st.subheader(f'Welcome {st.session_state.user["Name"]}!')
        with st.expander('Upload/Download Files'):
            if st.file_uploader('Upload 623A or ILTP', type=['pdf', 'txt', 'docx']):
                with st.spinner('uploading...'):
                    try:
                        pass
                    except Exception as e:
                        st.sidebar.error('could not upload file :(')
                        raise e

        with st.expander('My Troops'):
            subs = get_subs(st.session_state.user['Name'])
            for s in subs:
                cols = st.columns((4, 1))
                if cols[0].button(s['Name'], help='click to show history'):
                    show_dataframe(s['Name'])
                cols[1].write(f'{calculate_hours_done_this_month(s["Name"])} hrs')
        
        #with st.expander('My Files'):
        #    files = get_files(st.session_state.user['Name'])
        #    st.write('coming SOON™')
        #    return
        #    if not files:
        #        st.sidebar.warning('no files')
        #    for f in files:
        #        if st.button(f['name'], key=f['id']):
        #            uie.display_file(f['name'])

def main_page():
    with st.form('Entry'):
        st.subheader('Language Hour Entry')
        user = st.session_state.user
        cols = st.columns((2, 1))
        cols[0].text_input("Name", value=user['Name'], placeholder="Last, First", disabled=True)
        date = cols[1].date_input("Date")
        cols = st.columns((2, 1))
        mods = cols[0].multiselect("Activity", options=['Listening', 'Reading', 'Speaking', 'Vocab'])
        hours = cols[1].text_input(f"Hours - {calculate_hours_done_this_month(user['Name'])} hrs completed")
        cols = st.columns((2, 1))
        desc = cols[0].text_area("Description", height=150, placeholder='be detailed!')
        vocab = cols[1].text_area("Vocab", height=150, placeholder='list vocab you learned/reviewed')
        cols = st.columns(2)
        if cols[0].form_submit_button("Submit"):
            if not hours.isdigit() or hours <=0:
                st.warning('you need study for more than 0 hours...')
                return
            if not desc:
                st.warning('you need to describe what you studied...')
                return
            try:
                add_entry(
                    worksheet_id=LHT_ID,
                    sheet_name=user['Name'],
                    data=[[
                        str(date),
                        float(hours),
                        ",".join(mods),
                        desc,
                        ",".join(vocab.split())
                        ]]
                    )
                st.success('entry submitted!')
                st.balloons()
            except Exception as e:
                st.error('could not submit entry :(')
                raise e

    with st.expander('Show my Language Hour history'):
        try:
            data = get_data(column=None, worksheet_id=LHT_ID, sheet_name=user['Name'])
            st.dataframe(data, width=680)
        except:
            st.warning('could not load history')

if st.session_state.logged_in:
    with st.spinner('loading...'):
        main_page()
        sidebar()
        flags = check_flags()
        if flags is not None:
            if 'admin' in flags:
                adminbar()
            if 'dev' in flags:
                devbar()
else:
    login()

