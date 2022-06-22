import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from utils import initialize_session_state


SERVICE_INFO = st.secrets['service_account']
LHT_ID = st.secrets['LHT_ID']
LST_ID = st.secrets['LST_ID']
FOLDER_ID = st.secrets['FOLDER_ID']
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.metadata",
]

session_vars = ['logged_in', 'user']
initialize_session_state(session_vars)

st.set_page_config(page_title="Language Hour Entry", page_icon="🌐", layout="centered")
credentials = service_account.Credentials.from_service_account_info(info=SERVICE_INFO, scopes=SCOPES)
sheets_service = build(serviceName="sheets", version="v4", credentials=credentials)
drive_service = build(serviceName="drive", version="v3", credentials=credentials)

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

def check_flags(username):
    pass

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
            return False
    
        user = user.to_dict('records')[0]
        if user['Password'] == password:
            user.pop('Password')
            st.success('logged in successfully!')
            st.session_state.user = user
            st.session_state.logged_in = True
            return True
        else:
            st.error('incorrect username or password')
            return False
    else:
        st.session_state.user = None
        st.session_state.logged_in = False
        return False

def login():
    if not st.session_state.logged_in:
        with st.form('Login'):
            st.subheader('Login')
            username = st.text_input('Username').lower()
            password = st.text_input('Password', type='password')
            login = st.form_submit_button('Login')
            if login:
                status = authenticate(username, password)


def sidebar():
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

def main_page():
    with st.form('Entry'):
        st.subheader('Language Hour Entry')
        user = st.session_state.user
        cols = st.columns((2, 1))
        cols[0].text_input("Name", value=user['Name'], placeholder="Last, First", disabled=True)
        date = cols[1].date_input("Date")
        cols = st.columns((2, 1))
        mods = cols[0].multiselect("Activity", options=['Listening', 'Reading', 'Speaking', 'Vocab'])
        hours = cols[1].text_input(f"Hours - XX submitted")
        cols = st.columns((2, 1))
        desc = cols[0].text_area("Description", height=150, placeholder='be detailed!')
        vocab = cols[1].text_area("Vocab", height=150, placeholder='list vocab you learned/reviewed')
        cols = st.columns(2)
        if cols[0].form_submit_button("Submit"):
            if not hours.isdigit():
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
        data = get_data(column=None, worksheet_id=LHT_ID, sheet_name=user['Name'])
        st.dataframe(data, width=680)

if st.session_state.logged_in:
    with st.spinner('loading...'):
        main_page()
        sidebar()
else:
    login()

