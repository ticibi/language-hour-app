from io import BytesIO
from mimetypes import init
from operator import contains
from urllib.error import HTTPError
from click import option
import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build, MediaFileUpload
from googleapiclient.http import MediaIoBaseDownload
from utils import initialize_session_state_variables, to_excel
from datetime import datetime, date
import inspect
import calendar
import os

SERVICE_ACCOUNT = st.secrets['SERVICE_ACCOUNT']
LHT_ID = st.secrets['LHT_ID']
LST_ID = st.secrets['LST_ID']
FOLDER_ID = st.secrets['FOLDER_ID']
LST_URL = st.secrets['LST_URL']
LHT_URL = st.secrets['LHT_URL']
DRIVE_URL = st.secrets['DRIVE_URL']
PASSWORD = st.secrets['PASSWORD']
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.metadata",
]

st.set_page_config(page_title="Language Hour Entry", page_icon="🌐", layout="centered")
session_variables = ['req_count', 'debug', 'subs', 'entries', 'files', 'members', 'main', 'scores', 'show_total_month_hours', 'help_text', 'total_month_all', 'logged_in', 'user', 'admin', 'dev', 'sg', 'data']
initialize_session_state_variables(session_variables)
st.session_state.req_count = 0


def debug(text):
    if not st.session_state.debug:
        return
    st.write(text)
        

class GServices:
    def __init__(self, account_info, scopes):
        self.credentials = service_account.Credentials.from_service_account_info(
            info=account_info,
            scopes=scopes,
        )
        self.mail = self.Mail(self.credentials)
        self.sheets = self.Sheets(self.credentials)
        self.drive = self.Drive(self.credentials)

    class Mail:
        def __init__(self, credentials):
            self.mail = build(
                serviceName='gmail',
                version='v1',
                credentials=credentials,
            )

    class Sheets:
        def __init__(self, credentials):
            self.sheets = build(
                serviceName='sheets',
                version='v4',
                credentials=credentials,
            )

        def add_tab(self, tab_name, worksheet_id):
            body = {
                'requests': [
                    {
                        'addSheet': {
                            'properties': {
                                'title': tab_name,
                            }
                        }
                    }
                ]
            }
            try:
                r = self.batch_update(body, worksheet_id)
                return True
            except HTTPError as e:
                print(e)
                return False

        def get_tab_id(self, tab_name, worksheet_id):
            sheet_id = None
            try:
                data = self.sheets.get(
                    spreadsheetId=worksheet_id,
                ).execute()
            except HTTPError as e:
                print(inspect.getframeinfo(inspect.currentframe())[2], e)
            for sheet in data['sheets']:
                if sheet['properties']['title'] == tab_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            return sheet_id

        def get_data(self, columns, tab_name, worksheet_id, range='A:K'):
            try:
                values = (self.sheets.spreadsheets().values().get(
                    spreadsheetId=worksheet_id,
                    range=f"{tab_name}!{range}",
                    ).execute()
                )
            except HTTPError as e:
                print(e)
                return
            df = pd.DataFrame(values['values'])
            df.columns = df.iloc[0]
            df = df[1:]
            st.session_state.req_count += 1
            return df.get(columns) if columns != None else df

        def write_data(self, data, tab_name, worksheet_id, range='A:K'):
            self.sheets.spreadsheets().values().append(
                spreadsheetId=worksheet_id,
                range=f"{tab_name}!{range}",
                body=dict(values=data),
                valueInputOption="USER_ENTERED",
            ).execute()

        def append_data(self, data, tab_name, worksheet_id, range='A:K'):
            pass

        def batch_update(self, body, worksheet_id):
            r = None
            try:
                r = self.sheets.spreadsheets().batchUpdate(
                    spreadsheetId=worksheet_id,
                    body=body,
                ).execute()
            except HTTPError as e:
                print(e)
            return r

    class Drive:
        def __init__(self, credentials):
            self.drive = build(
                serviceName='drive',
                version='v3',
                credentials=credentials,
            )

        def create_folder(self, folder_name):
            metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [FOLDER_ID],
            }
            folder = None
            try:
                folder = self.drive.files().create(
                    body=metadata,
                    fields='id',
                ).execute()
            except HTTPError as e:
                print(e)
            return folder

        def get_folder_id(self, folder_name):
            q = f'mimeType="application/vnd.google-apps.folder" and name="{folder_name}"'
            file = self.drive.files().list(q=q, fields=f'files(id)').execute()
            return file['files'][0]['id']

        def get_files(self, folder_name):
            try:
                folder_id = self.get_folder_id(folder_name)
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

        def download_file(self, file_name, file_id):
            r = self.drive.files.get_media(fileId=file_id)
            data = BytesIO()
            try:
                download = MediaIoBaseDownload(fd=data, request=r)
            except HTTPError as e:
                print(e)
            done = False
            while not done:
                status, done = download.next_chunk()
            data.seek(0)
            with open(os.path.join('./LanguageHourFiles', file_name), 'wb') as f:
                f.write(data.read())
                f.close()
            return data

        def upload_file(self, file, folder_name):
            with open(f"temp/{file.name}", "wb") as f:
                f.write(file.getbuffer())
            file_metadata = {
                    "name": f"{file.name}",
                    "parents": [self.get_folder_id(folder_name)],
                }
            media = MediaFileUpload(f"temp/{file.name}", mimetype="*/*")
            self.drive.files().create(body=file_metadata, media_body=media, fields="id").execute()

    def add_member(self, data):
        try:
            self.drive.create_folder(data['Name'])
            st.success('created folder')
        except Exception as e:
            print(e)
            st.warning('failed to create folder')
        try:
            self.sheets.add_tab(data['Name'])
            cell_range = 'A1'
            values = (
                ('Date', 'Hours', 'Modality', 'Description', 'Vocab'),
            )
            body = {
                'majorDimension': 'ROWS',
                'values': values,
            }
            self.sheets.spreadsheets().values().update(
                spreadsheetId=LHT_ID,
                valueInputOption='USER_ENTERED',
                range=f'{data["Name"]}!{cell_range}',
                body=body,
            ).execute()
            st.success('created sheet')
        except Exception as e:
            print(e)
            st.warning('failed to create sheet')
        try:
            data =[[data['Name'], data['Username'], PASSWORD, data['Flags']]]
            self.sheets.write_data(data, worksheet_id=LHT_ID, tab_name='Members', range='A:D')
            st.success('added member info')
        except Exception as e:
            print(e)
            st.warning('failed to add member info')
        try:
            data = []
            data.append(list(data.values())[:-1])
            data[0].pop(1)
            self.sheets.write_data(data, worksheet_id=LST_ID, tab_name='Main', range='A:K')
            st.success('added member scores')
        except Exception as e:
            print(e)
            st.warning('failed to add member scores')

    def remove_member(self, data):
        worksheet_id = LHT_ID
        sheet_id = self.get_sheet_id(data['Name'])
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
            r = self.sheets.spreadsheets().batchUpdate(
                spreadsheetId=worksheet_id, body=body
            ).execute()
        except HTTPError as e:
            print(__name__, e)
        user_data = self.sheets.get_data(columns=None, worksheet_id=LST_ID, tab_name='Main')
        index = user_data.index[user_data['Name'] == data['Name']].tolist()[0]
        body = {
            "requests": [
                {
                    "deleteDimension": {
                        "range": {
                            "sheetId": worksheet_id,
                            "dimension": "ROWS",
                            "startIndex": index,
                            "endIndex": index + 1,
                        }
                    }
                }
            ]
        }
        try:
            r = self.sheets.spreadsheets().batchUpdate(
                spreadsheetId=worksheet_id, body=body
            ).execute()
        except HTTPError as e:
            print(e)

    def update_member(self, field, name, index, values):
        column = ''
        match field:
            case 'name':
                column = 'A'
            case 'username':
                column = 'B'
            case 'password':
                column = 'C'
            case 'flags':
                column = 'D'
            case _:
                column = ''
        body = {'values': values}
        try:
            r = self.sheets.spreadsheets().values().update(
                spreadsheetId=LHT_ID, range=f'{name}!{column}{index}', valueInputOption='USER_ENTERED', body=body,
            ).execute()
        except HTTPError as e:
            print(e)
            st.warning('error')
            return e

    def log(self, event, tab_name='Log', worksheet_id=LHT_ID, range='A:D'):
        self.sheets.write_data(
            [[str(date.today()),
            str(datetime.now().strftime("%H:%M:%S")),
            st.session_state.user['Username'],
            event]],
            tab_name=tab_name,
            worksheet_id=worksheet_id,
            range=range,
        )


class Authenticator:
    def __init__(self, data):
        self.data = data

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
        hours_done = 0
        data= None
        try:
            data = service.sheets.get_data(columns=['Date', 'Hours'], worksheet_id=LHT_ID, tab_name=name)
        except:
            continue
        if data is None:
            output.append([name, 0])
        else:
            for i, row in data.iterrows():
                date = row['Date']
                hours = row['Hours']
                if int(date[5:7]) == this_month:
                    hours_done += int(hours)

            user_data = st.session_state.main.loc[st.session_state.main['Name'] == name]
            output.append([name, hours_done, calculate_hours_required(user_data)])
    return output

def calculate_hours_done_this_month(name):
    try:
        data = service.sheets.get_data(columns=['Date', 'Hours'], worksheet_id=LHT_ID, tab_name=name)
    except Exception as e:
        print(e)
        return 0
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
        value: int = 0
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
            return 0

    if isinstance(data, dict):
        if not data:
            return 0

    if data['CLang'] == 'AD':
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
        if data['Dialects']:
            vals = [v.strip().split(' ')[1] for v in data['Dialects'].split(',')]
            vals.append(data['CL - Listening'])
            high = to_value((highest(vals, 1)[0]))
            value = sum([high, to_value(data['MSA - Reading'])])
            return evaluate(str(value))[0]
        else:
            if data['CL - Listening'] in BAD or data['MSA - Reading'] in BAD:
                return 12
            value = sum([to_value(data['CL - Listening']), to_value(data['MSA - Reading'])])
            return evaluate(str(value))[0]
    else:
        return 999

def get_subs(supe):
    df = service.sheets.get_data(columns=['Name', 'Supervisor'], worksheet_id=LST_ID, tab_name="Main", range="A:K")
    subs = df[df["Supervisor"] == supe]
    return subs

def check_flags():
    '''returns list of flags'''
    data = st.session_state.members
    flags = data.query(f'Name == "{st.session_state.user["Name"]}"')['Flags']
    flags = flags.tolist()[0]
    if flags != None:
        if contains(flags, 'admin'):
            st.session_state.admin = True
        if contains(flags, 'dev'):
            st.session_state.dev = True
            st.session_state.debug = True
        if contains(flags, 'sg'):
            st.session_state.sg = True
    return flags

def admin_main():
    if st.session_state.show_total_month_hours:
        with st.expander(f'Total Month Hours - {calendar.month_name[date.today().month]} {date.today().year}', expanded=True):
            with st.spinner('loading data...'):
                if st.session_state.total_month_all:
                    df = pd.DataFrame(st.session_state.total_month_all, columns=['Comments', 'Met', 'Name', 'Hours Done', 'Hours Required'])
                    st.table(df)
                else:
                    data = []
                    hrs_done = None
                    hrs_req = None
                    user_data = None
                    check = None
                    for name in st.session_state.members['Name']:
                        hrs_done = calculate_hours_done_this_month(name)
                        try:
                            user_data = st.session_state.main.loc[st.session_state.main['Name'] == name].to_dict('records')[0]
                            hrs_req = calculate_hours_required(user_data)
                        except:
                            pass
                        if float(hrs_done) >= float(hrs_req):
                            check = '✅'
                        else:
                            check = '❌'
                        data.append(['', check, name, hrs_done, hrs_req])
                    df = pd.DataFrame(data, columns=['Comments', 'Met', 'Name', 'Hours Done', 'Hours Required'])
                    st.table(df)
                    st.session_state.total_month_all = data

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
                    user_data = {
                        'Name': name,
                        'Username': username,
                        'CLang': clang,
                        'ILTP': iltp,
                        'SLTE': str(slte),
                        'DLPT': str(dlpt),
                        'CL - Listening': cll,
                        'MSA - Listening': msal,
                        'MSA - Reading': msar,
                        'Dialects': dialects if dialects else '',
                        'Mentor': mentor if mentor else '',
                        'Supervisor': supe,
                        'Flags': flags if flags else '',
                    }
                    try:
                        service.add_member(user_data)
                        service.log(f'added member {username}')
                    except Exception as e:
                        print(e)
                        st.error('failed to add member')


        with st.expander('Members'):
            options = list(st.session_state.members['Name'])
            options.append('')
            member = st.selectbox('Select a Member', options=options, index=len(options)-1)
            if member:
                data = service.sheets.get_data(columns=None, worksheet_id=LHT_ID, sheet_name=member)
                button = st.download_button(f'Download Entry History', data=to_excel(data))
                file_button = st.button('Download Files')
                if file_button:
                    pass
                remove_button = st.button('Remove Member')
                if remove_button:
                    confirm = st.button(f'Confirm Removal of "{member}"')
                    if confirm:
                        service.log(f'removed member {username}')

        with st.expander('More'):
            button = st.button('Show Total Month Hours')
            if button:
                st.session_state.show_total_month_hours = not st.session_state.show_total_month_hours

        st.write(f"[Language Score Tracker]({LST_URL})")
        st.write(f"[Language Hour Tracker]({LHT_URL})")
        st.write(f"[Google Drive]({DRIVE_URL})")

def devbar():
    def _change():
        st.session_state.debug = not st.session_state.debug

    st.sidebar.subheader('Dev')
    with st.sidebar:
        with st.expander('+'):
            st.write(f'Request Count: {st.session_state.req_count}')
            st.checkbox('Show Debug', value=st.session_state.debug, on_change=_change())
            debug(st.session_state.debug)
            drive_id = st.text_input('Drive ID')
            sheet_id = st.text_input('Sheet ID')
            default_pass = st.text_input('Default Password')

def get_user_info_index(name):
    df = st.session_state.members
    index = df.loc[df['Name'] ==  name].index[0]
    return index + 1

def welcome():
    return '🦢 Silly Goose' if st.session_state.sg else st.session_state.user['Name']

def sidebar():
    def show_dataframe(name):
        data = service.sheets.get_data(columns=None, worksheet_id=LHT_ID, tab_name=name, range='A:D')
        if data.empty:
            st.warning('no entries found')
            return
        st.table(data)

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
                        service.update_member(field='username', name='Members', index=index, values=[[username]])
                        service.log(f'updated username to {username}')
                        del username
                    if password != '':
                        service.update_member(field='password', name='Members', index=index, values=[[password]])
                        service.log(f'changed their password')
                        del password
                    st.info('info updated')
                except Exception as e:
                    st.warning('failed to update')
                    print(e)

    def upload():
        with st.expander('Upload/Download Files'):
            try:
                st.download_button('📥 Download myLanguageHours', data=to_excel(st.session_state.entries))
            except:
                pass
            file = st.file_uploader('Upload 623A or ILTP', type=['pdf', 'txt', 'docx'])
            st.write('NOTE FOR 623A ENTRIES: be sure to submit an entry annotating "623 upload" with the number of hours after uploading the pdf')
            if file:
                with st.spinner('uploading...'):
                    try:
                        service.drive.upload_file(file, folder_name=st.session_state.user['Name'])
                        st.sidebar.success('file uploaded')
                        service.log(f'uploaded {file.type} file named "{file.name}"')
                    except Exception as e:
                        st.sidebar.error('could not upload file :(')
                        raise e
                os.remove(f"temp/{file.name}")

    def subs():
        with st.expander('My Troops'):
            subs = st.session_state.subs
            if len(subs) > 0:
                st.write(f'Showing {calendar.month_name[date.today().month]} {date.today().year} Hours')
            for sub in subs.to_dict('records'):
                sub_data = service.sheets.get_data(columns=None, worksheet_id=LST_ID, tab_name='Main', range='A:K')
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
                                #uie.display_file(file['name'])
                            os.remove(f"temp/{file['name']}")

    def help():
        with st.expander('Help'):
            print(list(st.session_state.help_text))

    def settings():
        def _check_reminder():
            if not st.session_state.user['Reminder']:
                return False
            return True if st.session_state.user['Reminder'] else False

        def _check_report():
            if not st.session_state.user['Report']:
                return False
            return True if st.session_state.user['Report'] else False

        with st.expander('Preferences'):
            st.session_state.user['Reminder'] = 'x' if st.checkbox('Receive e-mail reminders', value=_check_reminder()) else ''
            st.session_state.user['Report'] = 'x' if st.checkbox('Receive monthly reports', value=_check_report()) else ''
            st.text_input(
                'Enter email',
                value=st.session_state.user['Email'] if st.session_state.user['Email'] else '',
                placeholder='Enter email',
                type='password',
            )
            debug((st.session_state.user['Reminder'], st.session_state.user['Report']))
            

    with st.sidebar:
        st.subheader(f'Welcome {welcome()}!')
        if st.session_state.debug: info()
        subs()
        upload()
        if st.session_state.debug: files()
        if st.session_state.debug: settings() 
        if st.session_state.debug: help()         

def main_page():
    with st.form('Entry'):
        name = ''
        st.subheader('Language Hour Entry')
        user = st.session_state.user
        scores = st.session_state.scores
        subs = st.session_state.subs
        cols = st.columns((2, 1))
        if st.session_state.admin:
            options = list(st.session_state.members['Name'])
            index = options.index(user['Name'])
            name = cols[0].selectbox("Name", options=options, index=index)
        else:
            options = list(subs['Name'])
            options.append(user['Name'])
            name = cols[0].selectbox("Name", options=options, index=len(options)-1)
        date = cols[1].date_input("Date")
        cols = st.columns((2, 1))
        mods = cols[0].multiselect("Activity", options=['Listening', 'Reading', 'Speaking', 'Transcription', 'Vocab', 'SLTE', 'DLPT', 'ILTP upload', '623A upload'])
        hours_done = calculate_hours_done_this_month(user['Name'])
        hours_req = calculate_hours_required(scores)
        hours = cols[1].text_input(f"Hours - {hours_done}/{hours_req} hrs completed")
        cols = st.columns((2, 1))
        desc = cols[0].text_area("Description", height=150, placeholder='be detailed!')
        vocab = cols[1].text_area("Vocab", height=150, placeholder='list vocab you learned/reviewed')
        cols = st.columns(2)
        if cols[0].form_submit_button("Submit"):
            if contains(hours, 'test'):
                hours = 0
            elif not hours.isdigit():
                st.warning('you need study for more than 0 hours...')
                return
            if not desc:
                st.warning('you need to describe what you studied...')
                return
            try:
                service.sheets.write_data(
                    worksheet_id=LHT_ID,
                    tab_name=name,
                    data=[[
                        str(date),
                        float(hours),
                        ' '.join(mods),
                        desc,
                        ' '.join(vocab.split() if vocab else '')
                        ]]
                    )
                st.success('entry submitted!')
                st.balloons()
                st.session_state.entries = service.sheets.get_data(columns=None, worksheet_id=LHT_ID, tab_name=st.session_state.user['Name'])
                service.log(f'submit {hours} hrs')
            except Exception as e:
                st.error('could not submit entry :(')
                raise e

    with st.expander('Show my Language Hour history'):
        try:
            st.table(st.session_state.entries)
        except:
            st.warning('could not load history')

def load_data():
    try:
        st.session_state.help_text = service.sheets.get_data(columns=None, tab_name='Help', worksheet_id=LHT_ID, range='A:B')
        st.session_state.main = service.sheets.get_data(columns=None, tab_name='Main', worksheet_id=LST_ID, range='A:K')
        st.session_state.subs = get_subs(st.session_state.user['Name'])
        st.session_state.files = service.drive.get_files(folder_name=st.session_state.user['Name'])
        st.session_state.members = service.sheets.get_data(columns=None, tab_name='Members', worksheet_id=LHT_ID, range='A:D')
        df = service.sheets.get_data(columns=None, tab_name='Main', worksheet_id=LST_ID, range='A:K')
        st.session_state.scores = df.loc[df['Name'] == st.session_state.user['Name']]
        st.session_state.scores = st.session_state.scores.to_dict('records')[0]
        st.session_state.entries = service.sheets.get_data(columns=None, worksheet_id=LHT_ID, tab_name=st.session_state.user['Name'])
        st.session_state.debug = False
        return True
    except IndexError as e:
        print(e)
        return False

service = GServices(SERVICE_ACCOUNT, SCOPES)
data = service.sheets.get_data(columns=None, worksheet_id=LHT_ID, tab_name='Members')
auth = Authenticator(data=data)

if st.session_state.logged_in:
    load_data()
    check_flags()
    main_page()
    sidebar()
    if st.session_state.admin:
        adminbar()
        admin_main()
    if st.session_state.dev:
        devbar()
else:
    auth.login()


