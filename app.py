from io import BytesIO
from urllib.error import HTTPError
import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build, MediaFileUpload
from googleapiclient.http import MediaIoBaseDownload
from utils import initialize_session_state
from datetime import datetime
import os
import ui_elements as uie


st.set_page_config(page_title="Language Hour Entry", page_icon="🌐", layout="centered")

SERVICE_ACCOUNT = st.secrets['service_account']
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

class GoogleServices:
    def __init__(self, info, scopes):
        self.credentials = service_account.Credentials.from_service_account_info(info=info, scopes=scopes)
        self.sheets = build(serviceName="sheets", version="v4", credentials=self.credentials)
        self.drive = build(serviceName="drive", version="v3", credentials=self.credentials)
        self.session_variables = ['subs', 'entries', 'files', 'members', 'main', 'scores']
        initialize_session_state(self.session_variables)

    def get_folder_id(self, name):
        q = f'mimeType="application/vnd.google-apps.folder" and name="{name}"'
        file = self.drive.files().list(q=q, fields=f'files(id)').execute()
        return file['files'][0]['id']

    def get_files(self, name):
        try:
            folder_id = self.get_folder_id(name)
        except IndexError as e:
            print(e)
            return
        q = f'parents = "{folder_id}"'
        r = self.drive.files().list(q=q).execute()
        files = r.get('files')
        nextPageToken = r.get('nextPageToken')
        while nextPageToken:
            r = self.drive.files().list(q=q).execute()
            files.extend(r.get('files'))
        return files

    def upload_file(self, file, folder):
        '''upload file onto the google drive into the destination folder'''
        with open(f"temp/{file.name}", "wb") as f:
            f.write(file.getbuffer())
        file_metadata = {
                "name": f"{file.name}",
                "parents": [self.get_folder_id(folder)],
            }
        media = MediaFileUpload(f"temp/{file.name}", mimetype="*/*")
        self.drive.files().create(body=file_metadata, media_body=media, fields="id").execute()

    def update_password(self, index: int, sheet_name, values):
        body = {'values': values}
        try:
            r = self.sheets.spreadsheets().values().update(
                spreadsheetId=LHT_ID, range=f'{sheet_name}!C{index}', valueInputOption='USER_ENTERED', body=body,
            ).execute()
        except HTTPError as e:
            st.warning('error')
            return e

    def update_username(self, index, sheet_name, values):
        body = {'values': values}
        try:
            r = self.sheets.spreadsheets().values().update(
                spreadsheetId=LHT_ID, range=f'{sheet_name}!B{index}', valueInputOption='USER_ENTERED', body=body,
            ).execute()
        except HTTPError as e:
            st.warning('error')
            return e

    def get_data(self, columns, worksheet_id, sheet_name, range='A:D'):
        try:
            values = (self.sheets.spreadsheets().values().get(
                spreadsheetId=worksheet_id,
                range=f"{sheet_name}!{range}",
                ).execute()
            )
        except HTTPError as e:
            print(e)
            return
        df = pd.DataFrame(values['values'])
        df.columns = df.iloc[0]
        df = df[1:]
        return df.get(columns) if columns != None else df

    def write(self, data, worksheet_id, sheet_name, range='A:K'):
        self.sheets.spreadsheets().values().append(
        spreadsheetId=worksheet_id,
        range=f"{sheet_name}!{range}",
        body=dict(values=data),
        valueInputOption="USER_ENTERED",
    ).execute()


class Authenticator:
    def __init__(self, data):
        self.data = data
        self.session_variables = ['logged_in', 'user', 'admin', 'dev', 'sg', 'data']
        initialize_session_state(self.session_variables)

    def authenticate(self, username, password):
        data = self.data
        if data is not None:
            try:
                user = data.loc[data['Username'] == username]
            except:
                st.error('incorrect username or password :(')
            try:
                user = user.to_dict('records')[0]
            except:
                st.error('user does not exist')
                return
            if user['Password'] == password:
                user.pop('Password')
                st.session_state.user = user
                st.session_state.logged_in = True
            else:
                st.error('incorrect username or password')
        else:
            st.session_state.user = None
            st.session_state.logged_in = False

    def login(self, header='Login'):
        if not st.session_state.logged_in:
            with st.form(header):
                st.subheader(header)
                username = st.text_input('Username').lower()
                password = st.text_input('Password', type='password')
                login = st.form_submit_button(header)
                if login:
                    self.authenticate(username, password)

    def logout(self):
        for i, var in enumerate(self.session_variables):
            self.session_variables[i] = None
            st.session_state[var] = None


def get_all_monthly_hours():
    output = []
    this_month = datetime.now().date().month
    names = st.session_state.members['Name']
    for name in names:
        total_hours = 0
        data= None
        try:
            data = service.get_data(columns=None, worksheet_id=LHT_ID, sheet_name=name)
        except:
            continue
        if data is None:
            output.append([name, 0])
        else:
            for i, row in data.iterrows():
                date = row['Date']
                hours = row['Hours']
                if int(date[5:7]) == this_month:
                    total_hours += int(hours)
            output.append([name, total_hours])
    return output

def calculate_hours_done_this_month(name):
    try:
        data = service.get_data(columns=['Date', 'Hours'], worksheet_id=LHT_ID, sheet_name=name)
    except Exception as e:
        print(e)
        return '?'
    if data is None:
        return 0
    this_month = datetime.now().date().month
    hours = sum([int(d[1]) for d in data.values if int(d[0][5:7]) == this_month])
    return hours

def calculate_hours_required(data):
    def to_value(score:str):
        total: float = 0.0
        if '+' in score:
            total =+ 0.5
            score = score.replace('+', '')
        total += float(score)
        return total

    def evaluate(score:float):
        value: int = 99
        match score:
            case '5.5': 
                value = 2,
            case '5.0': 
                value = 4,
            case '4.5': 
                value = 6,
            case '4.0': 
                value = 8,
            case _: 
                if score >= 6:
                    value = 0
                elif score < 4:
                    value = 12
        return value

    def highest(scores:list, k=2):
        if k > len(scores):
            raise ValueError
        values = sorted(scores, reverse=True)
        return values[:k]
    
    BAD = ['1+', '1', '0+', '0']
    GOOD = ['3', '3+', '4']

    if isinstance(data, pd.DataFrame):
        if data.empty:
            return

    if isinstance(data, dict):
        if not data:
            return

    if data['CLang'] in ['AD']:
        if data['MSA - Listening'] in GOOD and data['MSA - Reading'] in GOOD:
            return 0
        if data['MSA - Listening'] in BAD or data['MSA - Reading'] in BAD:
            return 12
        else:
            value = sum([to_value(data['MSA - Listening']), to_value(data['MSA - Reading'])])
            return evaluate(str(value))[0]

    if data['CLang'] in ['AP', 'DG']:
        if data['CL - Listening'] in GOOD and data['MSA - Reading'] in GOOD:
            return 0
        if data['CL - Listening'] in BAD or data['MSA - Reading'] in BAD:
            return 12
        if data['Dialects']:
            vals = [v.strip().split(' ')[1] for v in data['Dialects'].split(',')]
            vals.append(data['CL - Listening'])
            high = to_value((highest(vals, 1)[0]))
            value = sum([high, to_value(data['MSA - Reading'])])
            return evaluate(str(value))[0]
        else:
            value = sum([to_value(data['CL - Listening']), to_value(data['MSA - Reading'])])
            return evaluate(str(value))[0]
    else:
        return 99

def get_subs(supe):
    df = service.get_data(columns=['Name', 'Supervisor'], worksheet_id=LST_ID, sheet_name="Main", range="A:K")
    subs = df[df["Supervisor"] == supe]
    return subs

def check_flags() -> list:
    '''returns list of flags'''
    data = st.session_state.members
    flags = data.query(f'Name == "{st.session_state.user["Name"]}"')['Flags']
    flags = flags.tolist()[0]
    if flags != None:
        flags = flags.strip()
        flags = flags.split(',')
        if 'admin' in flags:
            st.session_state.admin = True
        if 'dev' in flags:
            st.session_state.dev = True
        if 'sg' in flags:
            st.session_state.sg = True
        return flags
    return []

def adminbar():
    st.sidebar.subheader('Admin')
    with st.sidebar:
        with st.expander('Add Member'):
            with st.form('Add Member'):
                data = st.session_state.main
                name = st.text_input(label="Name", placeholder="Last, First")
                username = st.text_input(label="Username", placeholder="jsmith")
                clang = st.selectbox(label="CLang", options=["AP", "AD", "DG",])
                iltp = st.selectbox(label="ILTP Status", options=['ILTP', 'RLTP', 'NONE'])
                slte = st.date_input(label="SLTE Date")
                dlpt = st.date_input(label="DLPT Date")
                cll = st.text_input(label="CL - Listening")
                msal = st.text_input(label="MSA - Listening")
                msar = st.text_input(label="MSA - Reading")
                dialects = st.text_input(label="Dialects", placeholder="only score of 2 or higher")
                mentor = st.text_input(label="Mentor")
                supe = st.selectbox(label="Supervisor", options=[x for x in st.session_state.members['Name'].tolist()])
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
        with st.expander('+'):
            st.write('meow')

def get_user_info_index(name):
    df = st.session_state.members
    index = df.loc[df['Name'] ==  name].index[0]
    return index + 1

def welcome():
    return '🦢 Silly Goose' if st.session_state.sg else st.session_state.user['Name']

def sidebar():
    def show_dataframe(name):
        data = service.get_data(columns=None, worksheet_id=LHT_ID, sheet_name=name, range='A:D')
        if data.empty:
            st.warning('no entries found')
            return
        st.dataframe(data, width=300)

    def tooltip(data):
        output = f'CL: {data["CL - Listening"]} MSA: {data["MSA - Listening"]}/{data["MSA - Reading"]} (click to view entries)'
        return output

    def info():
        with st.expander('My Info'):
            st.text_input('Name', value=st.session_state.user['Name'], disabled=True)
            username = st.text_input('Username', value=st.session_state.user['Username'])
            password = st.text_input('Password', placeholder='enter a new password')
            button = st.button('Save')
            if button:
                index = get_user_info_index(st.session_state.user['Name'])
                try:
                    if username != '':
                        service.update_username(index, sheet_name='Members', values=[[username]])
                        del username
                    if password != '':
                        service.update_password(index, sheet_name='Members', values=[[password]])
                        del password
                    st.info('info updated')
                except Exception as e:
                    st.warning('failed to update')
                    print(e)

    def upload():
        with st.expander('Upload/Download Files'):
            file = st.file_uploader('Upload 623A or ILTP', type=['pdf', 'txt', 'docx'])
            st.write('note: be sure to submit an entry annotating a 623 upload with the number of hours')
            if file:
                with st.spinner('uploading...'):
                    try:
                        service.upload_file(file, folder=st.session_state.user['Name'])
                        st.sidebar.success('file uploaded')
                    except Exception as e:
                        st.sidebar.error('could not upload file :(')
                        raise e
                os.remove(f"temp/{file.name}")

    def subs():
        with st.expander('My Troops'):
                subs = st.session_state.subs
                for sub in subs.to_dict('records'):
                    sub_data = service.get_data(columns=None, worksheet_id=LST_ID, sheet_name='Main', range='A:K')
                    sub_data = sub_data.loc[sub_data['Name'] == sub['Name']].to_dict('records')[0]
                    cols = st.columns((5, 2))
                    if cols[0].button(sub['Name'], help=tooltip(sub_data)):
                        show_dataframe(sub['Name'])
                    hrs_done = calculate_hours_done_this_month(sub['Name'])
                    hrs_req = calculate_hours_required(sub_data)
                    color = 'green' if hrs_done >= hrs_req else 'red'
                    cols[1].markdown(f'<p style="color:{color}">{hrs_done}/{hrs_req} hrs</p>', unsafe_allow_html=True)

    def files():
            with st.expander('My Files'):
                files = st.session_state.files
                if not files:
                    st.sidebar.warning('no files')
                else:
                    for file in files:
                        if st.button(file['name'], key=file['id']):
                            try:
                                r = service.drive.files().get_media(fileId=file['id'])
                                file_bytes = BytesIO()
                                download = MediaIoBaseDownload(file_bytes, r)
                                done = False
                                while done is False:
                                    status, done = download.next_chunk()
                                    st.progress(value=status.progress())
                            except HTTPError as e:
                                print(e)
                                file_bytes = None
                                st.warning('failed to load file')
    #
                            with open(f"temp/{file['name']}", "wb") as f:
                                f.write(file_bytes.getbuffer())
                                uie.display_file(file['name'])
                            os.remove(f"temp/{file['name']}")

    with st.sidebar:
        st.subheader(f'Welcome {welcome()}!')
        #info()
        upload()
        subs()
        #files()             

def main_page():
    with st.form('Entry'):
        st.subheader('Language Hour Entry')
        user = st.session_state.user
        scores = st.session_state.scores
        cols = st.columns((2, 1))
        cols[0].text_input("Name", value=user['Name'], placeholder="Last, First", disabled=True)
        date = cols[1].date_input("Date")
        cols = st.columns((2, 1))
        mods = cols[0].multiselect("Activity", options=['Listening', 'Reading', 'Speaking', 'Vocab', 'SLTE'])
        hours_done = calculate_hours_done_this_month(user['Name'])
        hours_req = calculate_hours_required(scores)
        hours = cols[1].text_input(f"Hours - {hours_done}/{hours_req} hrs completed")
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
                service.write(
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
            data = service.get_data(columns=None, worksheet_id=LHT_ID, sheet_name=user['Name'])
            st.dataframe(data, width=680)
        except:
            st.warning('could not load history')

def preload_data():
    try:
        st.session_state.subs = get_subs(st.session_state.user['Name'])
        st.session_state.files = service.get_files(name=st.session_state.user['Name'])
        st.session_state.members = service.get_data(columns=None, worksheet_id=LHT_ID, sheet_name='Members', range='A:D')
        df = service.get_data(columns=None, worksheet_id=LST_ID, sheet_name='Main', range='A:K')
        st.session_state.scores = df.loc[df['Name'] == st.session_state.user['Name']]
        st.session_state.scores = st.session_state.scores.to_dict('records')[0]
        return True
    except IndexError as e:
        print(e)
        return False

service = GoogleServices(SERVICE_ACCOUNT, SCOPES)
data = service.get_data(columns=None, worksheet_id=LHT_ID, sheet_name='Members')
authenticator = Authenticator(data=data)

if st.session_state.logged_in:
    with st.spinner('loading...'):
        preload_data()
        check_flags()
        main_page()
        sidebar()
        if st.session_state.admin:
            adminbar()
        if st.session_state.dev:
            devbar()
else:
    authenticator.login()
