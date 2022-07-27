from io import BytesIO
from operator import contains
from urllib.error import HTTPError
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
import bcrypt


URL = 'https://docs.google.com/spreadsheets/d/'
DRIVE = 'https://drive.google.com/drive/u/6/folders/'
SERVICE_ACCOUNT = st.secrets['SERVICE_ACCOUNT']
FOLDER_ID = st.secrets['FOLDER_ID']
PASSWORD = st.secrets['PASSWORD']
MASTER_ID = st.secrets['MASTER_ID']
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.metadata",
]
INFO = 'Info'
MAIN = 'Main'
MEMBERS = 'Members'


st.set_page_config(page_title="Language Hour Entry", page_icon="🌐", layout="centered")
session_variables = ['selected_month', 'current_user', 'authenticated', 'current_group', 'req_count', 'members', 'config', 'req_count', 'debug', 'score_tracker', 'show_total_month_hours', 'total_month_all',]
initialize_session_state_variables(session_variables)
st.session_state.req_count = 0
        

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
                cache_discovery=False,
            )

    class Sheets:
        def __init__(self, credentials):
            self.sheets = build(
                serviceName='sheets',
                version='v4',
                credentials=credentials,
                cache_discovery=False,
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
                cache_discovery=False
            )

        def create_folder(self, folder_name, folder_id):
            metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [folder_id],
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

        def download_file(self, file_id):
            try:
                request = self.drive.files().get_media(fileId=file_id)
                file = BytesIO()
                download = MediaIoBaseDownload(file, request)
                done = False
                while done is False:
                    status, done = download.next_chunk()
            except HTTPError as e:
                print(e)
                file = None

            return file

        def upload_file(self, file, folder_name):
            with open(f"temp/{file.name}", "wb") as f:
                f.write(file.getbuffer())
            file_metadata = {
                    "name": f"{file.name}",
                    "parents": [self.get_folder_id(folder_name)],
                }
            media = MediaFileUpload(f"temp/{file.name}", mimetype="*/*")
            self.drive.files().create(body=file_metadata, media_body=media, fields="id").execute()

    def add_member(self, data, hour_id, score_id):
        try:
            self.drive.create_folder(data['Name'], FOLDER_ID)
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
                spreadsheetId=hour_id,
                valueInputOption='USER_ENTERED',
                range=f'{data["Name"]}!{cell_range}',
                body=body,
            ).execute()
            st.success('created tab')
        except Exception as e:
            print(e)
            st.warning('failed to create tab')
        try:
            data =[[data['Name'], data['Username'], PASSWORD, data['Flags']]]
            self.sheets.write_data(data, worksheet_id=hour_id, tab_name='Members', range='A:D')
            st.success('added member info')
        except Exception as e:
            print(e)
            st.warning('failed to add member info')
        try:
            data = []
            data.append(list(data.values())[:-1])
            data[0].pop(1)
            self.sheets.write_data(data, worksheet_id=score_id, tab_name='Main', range='A:K')
            st.success('added member scores')
        except Exception as e:
            print(e)
            st.warning('failed to add member scores')

    def remove_member(self, data, hour_id, score_id):
        worksheet_id = hour_id
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
        user_data = self.sheets.get_data(columns=None, worksheet_id=score_id, tab_name='Main')
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

    def update_member(self, field, name, index, values, hour_id):
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
                spreadsheetId=hour_id, range=f'{name}!{column}{index}', valueInputOption='USER_ENTERED', body=body,
            ).execute()
        except HTTPError as e:
            print(e)
            st.warning('error')
            return e

    def log(self, event, tab_name='Log', worksheet_id='', range='A:D'):
        try:
            self.sheets.write_data(
                [[str(date.today()),
                str(datetime.now().strftime("%H:%M:%S")),
                st.session_state.current_user['Username'],
                event]],
                tab_name=tab_name,
                worksheet_id=worksheet_id,
                range=range,
            )
        except Exception as e:
            print('[log error]', e)

    def update_entries(self, name, worksheet_id):
        st.session_state.current_user['Entries'] = self.sheets.get_data(columns=None, tab_name=name, worksheet_id=worksheet_id)

    def create_folders_bulk(self):
        count = 0
        names = st.session_state.members['Name']
        for name in names:
            try:
                _ = self.drive.get_folder_id(name)
            except Exception as e:
                print(e)
                self.drive.create_folder(name, st.session_state.config['GoogleDrive'])
                count += 1
        return count

    def create_tabs_bulk(self):
        count = 0
        names = st.session_state.members['Name']
        for name in names:
            try:
                self.sheets.get_data(columns=None, tab_name=name, worksheet_id=st.session_state.config['HourTracker'], range='A:D')
            except Exception as e:
                print(e)
                self.sheets.add_tab(name)
                cell_range = 'A1'
                values = (
                    ('Date', 'Hours', 'Modality', 'Description', 'Vocab'),
                )
                body = {
                    'majorDimension': 'ROWS',
                    'values': values,
                }
                self.sheets.spreadsheets().values().update(
                    spreadsheetId=st.session_state.config['HourTracker'],
                    valueInputOption='USER_ENTERED',
                    range=f'{name}!{cell_range}',
                    body=body,
                ).execute()
                count += 1
        return count


class Pages:
    def __init__(self):
        self.user = st.session_state.current_user

    def welcome_message(self):
        return '🦢 Silly Goose' if contains(st.session_state.current_user['Flags'], 'sg') else st.session_state.current_user['Name']

    def history_expander(self):
        with st.expander('Show my Language Hour history'):
            try:
                service.update_entries(self.user['Name'], worksheet_id=st.session_state.config['HourTracker'])
                st.table(self.user['Entries'])
            except Exception as e:
                print('[error]', e)

    def mytroops_expander(self):
        st.subheader('My Troops')
        for sub in self.user['Subs'].keys():
            with st.expander(sub):
                hrs_done = calculate_hours_done_this_month(sub)
                hrs_req = calculate_hours_required(self.user['Subs'][sub]['Scores'])
                color = 'green' if hrs_done >= hrs_req else 'red'
                st.markdown(f'<p style="color:{color}">{hrs_done}/{hrs_req} hrs</p>', unsafe_allow_html=True)
                scores = self.user['Subs'][sub]['Scores']
                del scores['Name']
                st.dataframe(pd.DataFrame(scores, index=[0]))
                st.dataframe(self.user['Subs'][sub]['Entries'])

    def entry_form(self):
        with st.form('Entry'):
            name = ''
            st.subheader('Language Hour Entry')
            cols = st.columns((2, 1))
            if contains(st.session_state.current_user['Flags'], 'admin'):
                options = list(st.session_state.members['Name'])
                index = options.index(self.user['Name'])
                name = cols[0].selectbox("Name", options=options, index=index)
            else:
                options = list(self.user['Subs'].keys())
                options.append(self.user['Name'])
                name = cols[0].selectbox("Name", options=options, index=len(options)-1)
            date = cols[1].date_input("Date")
            cols = st.columns((2, 1))
            mods = cols[0].multiselect("Activity", options=['Listening', 'Reading', 'Speaking', 'Transcription', 'Vocab', 'SLTE', 'DLPT', 'ILTP upload', '623A upload'])
            hours_done = calculate_hours_done_this_month(self.user['Name'])
            hours_req = calculate_hours_required(self.user['Scores'])
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
                        worksheet_id=st.session_state.config['HourTracker'],
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
                    st.session_state.entries = service.sheets.get_data(columns=None, worksheet_id=st.session_state.config['HourTracker'], tab_name=self.user['Name'])
                    service.log(f'submit {hours} hrs', worksheet_id=st.session_state.config['HourTracker'])
                except Exception as e:
                    st.error('could not submit entry :(')
                    raise e

    def main_page(self):
        self.entry_form()
        self.history_expander()
        self.mytroops_expander()

    def sidebar(self):
        def update_score():
            service.log(f'updated scores', worksheet_id=st.session_state.config['HourTracker'])

        def scores():
            with st.expander('[beta] My Scores'):
                cols = st.columns((1, 1, 1))
                listening = cols[0].text_input('CLang: Listening', value=self.user['Scores']['CL - Listening'])
                listening2 = cols[1].text_input('MSA: Listening', value=self.user['Scores']['MSA - Listening'])
                reading = cols[2].text_input('MSA: Reading', value=self.user['Scores']['MSA - Reading'])

        def account():
            with st.expander('[beta] My Account'):
                st.text_input('Name', value=self.user['Name'], disabled=True)
                username = st.text_input('Username', value=self.user['Username'])
                password = st.text_input('Password', placeholder='enter a new password')
                button = st.button('Save')
                if button:
                    index = get_user_info_index(self.user['Name'])
                    try:
                        if username != '':
                            service.update_member(field='username', name='Members', index=index, values=[[username]])
                            service.log(f'updated username to {username}')
                            del username
                        if password != '':
                            service.update_member(field='password', name='Members', index=index, values=[[password]])
                            service.log(f'updated password')
                            del password
                        st.info('info updated')
                    except Exception as e:
                        st.warning('failed to update')
                        print(e)

        def upload():
            with st.expander('Upload/Download Files'):
                try:
                    st.download_button('📥 Download myLanguageHours', data=to_excel(self.user['Entries']))
                except:
                    pass
                file = st.file_uploader('Upload 623A or ILTP', type=['pdf', 'txt', 'docx'])
                st.write('NOTE FOR 623A ENTRIES: be sure to submit an entry annotating "623 upload" with the number of hours after uploading the pdf')
                if file:
                    with st.spinner('uploading...'):
                        try:
                            service.drive.upload_file(file, folder_name=self.user['Name'])
                            st.sidebar.success('file uploaded')
                            service.log(f'uploaded {file.type} file named "{file.name}"')
                        except Exception as e:
                            st.sidebar.error('could not upload file :(')
                            raise e
                    os.remove(f"temp/{file.name}")

        def subs():
            with st.expander('My Troops', expanded=True):
                if self.user['Subs'] is None:
                    return
                for sub in self.user['Subs'].keys():
                    cols = st.columns((5, 2))
                    cols[0].markdown(sub)
                    hrs_done = calculate_hours_done_this_month(sub)
                    hrs_req = calculate_hours_required(self.user['Subs'][sub]['Scores'])
                    color = 'green' if hrs_done >= hrs_req else 'red'
                    cols[1].markdown(f'<p style="color:{color}">{hrs_done}/{hrs_req} hrs</p>', unsafe_allow_html=True)

        def files():
            with st.expander('My Files'):
                files = self.user['Files']
                if not files:
                    st.write('No files')
                    return
                for file in files:
                    try:
                        if st.download_button(file['name'], data=service.drive.download_file(file['id']), file_name=file['name']):
                            self.user['Files'] = service.drive.get_files(self.user['Name'])
                    except Exception as e:
                        print(e)
     
        def program_info():
            with st.expander('[beta] Program Info'):
                st.markdown('''
                    *program info goes here
                ''')

        def settings():
            def _check_reminder():
                if not st.session_state.current_user['Reminder']:
                    return False
                return True if st.session_state.current_user['Reminder'] else False

            def _check_report():
                if not st.session_state.current_user['Report']:
                    return False
                return True if st.session_state.current_user['Report'] else False

            with st.expander('[beta] Preferences'):
                st.session_state.current_user['Reminder'] = 'x' if st.checkbox('Receive e-mail reminders', value=_check_reminder()) else ''
                st.session_state.current_user['Report'] = 'x' if st.checkbox('Receive monthly reports', value=_check_report()) else ''
                st.text_input(
                    'Enter email',
                    value=st.session_state.current_user['Email'] if st.session_state.current_user['Email'] else '',
                    placeholder='Enter email',
                    type='password',
                )

        with st.sidebar:
            st.subheader(f'Welcome {self.welcome_message()}!')
            if 'admin' in st.session_state.current_user['Flags']: account()
            if 'admin' in st.session_state.current_user['Flags']: scores()
            subs()
            upload()
            files()
            if 'admin' in st.session_state.current_user['Flags']: settings() 
            if 'admin' in st.session_state.current_user['Flags']: program_info()

    def admin_page(self):
        if st.session_state.show_total_month_hours:
            with st.expander(f'Monthly Hours Rundown - {st.session_state.selected_month}', expanded=True):
                with st.spinner('calculating who done messed up...'):
                    data = []
                    for name in st.session_state.members['Name']:
                        try:
                            user_data = st.session_state.score_tracker.loc[st.session_state.score_tracker['Name'] == name].to_dict('records')[0]
                            hrs_req = calculate_hours_required(user_data)
                        except Exception as e:
                            print(e)
                            hrs_req = 0
                        try:
                            month = list(calendar.month_name).index(st.session_state.selected_month)
                            hrs_done = calculate_hours_done_this_month(name, month)
                        except Exception as e:
                            print(e)
                            hrs_done = 0
                        check = {
                            True: '✅',
                            False: '❌',
                        }
                        data.append(['', check[float(hrs_done) >= float(hrs_req)], name, hrs_done, hrs_req])
                    df = pd.DataFrame(data, columns=['Comments', 'Met', 'Name', 'Hours Done', 'Hours Required'])
                    st.table(df)
                    st.session_state.total_month_all = data

    def admin_sidebar(self):
        def add_member():
            with st.expander('Add Member'):
                with st.form('Add Member'):
                    data = st.session_state.score_tracker
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

        def member_actions():
            with st.expander('Member Actions'):
                options = list(st.session_state.members['Name'])
                options.append('')
                member = st.selectbox('Select a Member', options=options, index=len(options)-1)
                if member:
                    data = service.sheets.get_data(columns=None, tab_name=member, worksheet_id=st.session_state.config['HourTracker'])
                    button = st.download_button(f'Download Entry History', data=to_excel(data))
                    file_button = st.button('Download Files')
                    if file_button:
                        pass
                    remove_button = st.button('Remove Member')
                    if remove_button:
                        confirm = st.button(f'Confirm Removal of "{member}"')
                        if confirm:
                            service.log(f'removed member {member}', worksheet_id=st.session_state.config['HourTracker'])

        def admin_actions():
                with st.expander('Admin Actions'):
                    if st.button('Create Folders', help="create folders for all members if it doesn't exist"):
                        try:
                            count = service.create_folders_bulk()
                            st.sidebar.success(f"created {count} folders")
                            service.log(f'created {count} folders', worksheet_id=st.session_state.config['HourTracker'])
                        except HTTPError as e:
                            print(e)
                    if st.button('Create Tabs', help="create tabs for all members if it doesn't exist"):
                        try:
                            count = service.create_tabs_bulk()
                            st.sidebar.success(f"created {count} tabs")
                            service.log(f'created {count} tabs', worksheet_id=st.session_state.config['HourTracker'])
                        except HTTPError as e:
                            print(e)

        def rundown():
            with st.expander('Monthly Rundown'):
                month = st.selectbox("Select Month", options=calendar.month_name)# [i + 1 for i in range(12)])
                st.session_state.selected_month = month
                if st.button(f'Show {month} Hours Rundown'):
                    st.session_state.show_total_month_hours = not st.session_state.show_total_month_hours
                #if st.button('Show upcoming DLPTs'):
                #    pass
                #if st.button('Show upcoming SLTEs'):
                #    pass

        with st.sidebar:
            st.sidebar.subheader('Admin')
            add_member()
            member_actions()
            admin_actions()
            rundown()

            with st.expander('Tracker Links'):
                st.write(f"[Master Tracker]({URL+MASTER_ID})")
                st.write(f"[Score Tracker]({URL+st.session_state.config['ScoreTracker']})")
                st.write(f"[Hour Tracker]({URL+st.session_state.config['HourTracker']})")
                st.write(f"[Google Drive]({DRIVE+st.session_state.config['GoogleDrive']})")

    def dev_page(self):
        st.subheader('Dev Tools')
        with st.expander('[Developer Debug]'):
            st.write(st.session_state)

    def dev_sidebar(self):
        def toggle_debug():
            st.session_state.debug = not st.session_state.debug

        st.sidebar.subheader('[Developer Debug]')
        with st.sidebar:
            with st.expander('+', expanded=True):
                st.write(f'Request Count: {st.session_state.req_count}')
                st.checkbox('Show Debug', value=st.session_state.debug, on_change=toggle_debug())


class Authenticator:
    def __init__(self):
        pass

    def hash_password(self, password):
        salt = bcrypt.gensalt()
        hashed_pw = bcrypt.hashpw(bytes(password, 'utf-8'), salt)
        return hashed_pw

    def authenticate(self, username, password):
        try:
            data = service.sheets.get_data(columns=None, tab_name=MEMBERS, worksheet_id=MASTER_ID, range='A:I')
            user_data = data.query(f'Username == "{username}"').to_dict('records')[0]
            st.session_state.members = data.query(f'Group == "{user_data["Group"]}"').drop(columns=['Password'], axis=1)
        except Exception as e:
            st.error('could not retrieve user data')
            print(e)
            return

        hashed_pw = self.hash_password(password)
        
        if bcrypt.checkpw(bytes(user_data['Password'], 'utf-8'), hashed_pw):
            user_data.pop('Password')
            st.session_state.current_user = user_data
            st.session_state.authenticated = True
        else:
            st.error('incorrect username or password')
            st.session_state.authenticated = False

    def login(self, header='Login'):
        if not st.session_state.authenticated:
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


def check_due_date(scores: dict) -> tuple:
    '''return dlpt due and slte due'''
    str_format = '%m/%d/%Y'
    year = 31536000.0
    month = 2628000.0
    try:
        dlpt_last = datetime.strptime(scores['DLPT Date'], str_format).timestamp()
    except:
        dlpt_last = None
    try:
        slte_last = datetime.strptime(scores['SLTE Date'], str_format).timestamp()
    except:
        slte_last = None
    if scores['CLang'] in ['AD']:
        if scores['MSA - Listening'] == '3' and ['MSA - Reading'] == '3':
            dltp_due = dlpt_last + (year * 2) if slte_last is not None else dlpt_last
            slte_due = slte_last + (year * 2) if slte_last is not None else slte_last
        else:
            dltp_due = dlpt_last + year if slte_last is not None else dlpt_last
            slte_due = slte_last + (year + (month * 6)) if slte_last is not None else slte_last
    elif scores['CLang'] in ['AP', 'DG']:
        if scores['CL - Listening'] == '3' and ['MSA - Reading'] == '3':
            dltp_due = dlpt_last + (year * 2) if slte_last is not None else dlpt_last
            slte_due = slte_last + (year * 2) if slte_last is not None else slte_last
        else:
            dltp_due = dlpt_last + year if slte_last is not None else dlpt_last
            slte_due = slte_last + (year + (month * 6)) if slte_last is not None else slte_last
    output = (str(datetime.fromtimestamp(dltp_due))[:10], str(datetime.fromtimestamp(slte_due))[:10])
    return output
 
def calculate_hours_done_this_month(name, month=datetime.now().date().month):
    try:
        data = service.sheets.get_data(columns=['Date', 'Hours'], worksheet_id=st.session_state.config['HourTracker'], tab_name=name)
    except Exception as e:
        print(e)
        return 0
    if data is None:
        return 0
    hours = sum([int(d[1]) for d in data.values if int(d[0][5:7]) == month])
    return hours

def calculate_hours_required(data):
    if data is None:
        return 0
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
                if float(score) >= 6:
                    value = 0
                elif float(score) < 4:
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

def load_subs():
    st.session_state.current_user['Subs'] = {}
    worksheet = st.session_state.config['HourTracker']
    name = st.session_state.current_user['Name']
    subs = st.session_state.members.query(f'Supervisor == "{name}"')['Name'].tolist()
    for sub in subs:
        st.session_state.current_user['Subs'].update({sub: {'Scores': None, 'Entries': None}})
        scores = st.session_state.score_tracker.query(f'Name == "{sub}"').to_dict('records')[0]
        st.session_state.current_user['Subs'][sub]['Scores'] = scores
        st.session_state.current_user['Subs'][sub]['Entries'] = service.sheets.get_data(columns=None, tab_name=sub, worksheet_id=worksheet)

def get_user_info_index(name):
    df = st.session_state.members
    index = df.loc[df['Name'] ==  name].index[0]
    return index + 1

def load():
    name = st.session_state.current_user['Name']
    group = st.session_state.current_user['Group']
    st.session_state.current_group = group

    try:
        data = service.sheets.get_data(columns=None, tab_name=INFO, worksheet_id=MASTER_ID)
        st.session_state.config = data.query(f'Group == "{group}"').to_dict('records')[0]
    except:
        st.session_state.config = None

    try:
        score_tracker = st.session_state.config['ScoreTracker']
        all_scores = service.sheets.get_data(columns=None, tab_name=MAIN, worksheet_id=score_tracker, range='A:J')
        st.session_state.score_tracker = all_scores
    except:
        st.session_state.score_tracker = None

    try:
        user_scores = st.session_state.score_tracker.query(f'Name == "{name}"').to_dict('records')[0]
        user_scores.pop('Name')
        st.session_state.current_user['Scores'] = user_scores
    except:
        st.session_state.current_user['Scores'] = None

    try:
        worksheet = st.session_state.config['HourTracker']
        st.session_state.current_user['Entries'] = service.sheets.get_data(columns=None, tab_name=name, worksheet_id=worksheet)
    except:
        st.session_state.current_user['Entries'] = None

    try:
        st.session_state.current_user['Files'] = service.drive.get_files(name)
    except:
        st.session_state.current_user['Files'] = None
    
    try:
        load_subs()
    except Exception as e:
        print(e)
        st.session_state.current_user['Subs'] = {}


if __name__ == '__main__':
    service = GServices(SERVICE_ACCOUNT, SCOPES)
    auth = Authenticator()
    pages = Pages()

    if st.session_state.authenticated:
        with st.spinner('loading...'):
            load()
        try:
            pages.sidebar()
            pages.main_page()
        except Exception as e:
            st.error('could not load page')
            print(e)

        if contains(st.session_state.current_user['Flags'], 'admin'):
            try:
                pages.admin_sidebar()
                pages.admin_page()
            except Exception as e:
                st.error('could not load page')
                print(e)

        if contains(st.session_state.current_user['Flags'], 'dev'):
            try:
                pages.dev_sidebar()
                pages.dev_page()
            except Exception as e:
                st.error('could not load page')
                print(e)
    else:
        auth.login()
