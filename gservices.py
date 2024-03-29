from datetime import date, datetime
from io import BytesIO
from urllib.error import HTTPError
import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build, MediaFileUpload
from googleapiclient.http import MediaIoBaseDownload
import inspect
import config


class GServices:
    '''google services connection to gmail, gsheets, and google drive'''
    def __init__(self, account_info, scopes):
        self.credentials = service_account.Credentials.from_service_account_info(
            info=account_info,
            scopes=scopes,
        )
        self.mail = self.Mail(self.credentials)
        self.sheets = self.Sheets(self.credentials)
        self.drive = self.Drive(self.credentials)
        self.bulk_utils = self.BulkUtils()
        self.members = self.Members()


    class Mail:
        '''functions to interact with gmail'''
        def __init__(self, credentials):
            self.mail = build(
                serviceName='gmail',
                version='v1',
                credentials=credentials,
                cache_discovery=False,
            )


    class Sheets:
        '''functions to interact with the google sheet'''
        def __init__(self, credentials):
            self.sheets = build(
                serviceName='sheets',
                version='v4',
                credentials=credentials,
                cache_discovery=False,
            )

        def add_tab(self, tab_name, hour_tracker):
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
                r = self.batch_update(body, hour_tracker)
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
                valueInputOption='USER_ENTERED',
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

        def update_values(self, values:list, tab_name, worksheet_id, range):
            values = [values]
            body = {
                'values': values,
            }
            request = self.sheets.spreadsheets().values().update(
                spreadsheetId=worksheet_id,
                range=range,
                valueInputOption='USER_ENTERED',
                body=body,
            ).execute()


    class Drive:
        '''functions to interact with the google drive'''
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


    def create_tab(self, user_name, hour_tracker):
        try:
            self.sheets.add_tab(user_name, hour_tracker)
            cell_range = 'A1'
            values = (
                ('Date', 'Hours', 'Modality', 'Description', 'Vocab'),
            )
            body = {
                'majorDimension': 'ROWS',
                'values': values,
            }
            self.sheets.spreadsheets().values().update(
                spreadsheetId=hour_tracker,
                valueInputOption='USER_ENTERED',
                range=f'{user_name}!{cell_range}',
                body=body,
            ).execute()
            st.success('created tab')
        except Exception as e:
            print(e)
            st.warning('failed to create tab')

    def add_score(self, scores):
        try:
            data = []
            data.append(list(data.values())[:-1])
            data[0].pop(1)
            self.sheets.write_data(data, worksheet_id=scores, tab_name='Main', range='A:K')
            st.success('added member scores')
        except Exception as e:
            print(e)
            st.warning('failed to add member scores')

    def create_folder(self, user_name):
        try:
            self.drive.create_folder(user_name, config.FOLDER_ID)
            st.success('Created folder.')
        except Exception as e:
            print(e)
            st.warning('Failed to create folder.')

    def add_info(self, hour_tracker):
        try:
            data =[[data['Name'], data['Username'], config.PASSWORD, data['Flags']]]
            self.sheets.write_data(data, worksheet_id=hour_tracker, tab_name='Members', range='A:D')
            st.success('added member info')
        except Exception as e:
            print(e)
            st.warning('failed to add member info')

    def add_member(self, user, hour_tracker, score_tracker):
        self.create_folder(user)
        self.create_tab(user, hour_tracker)
        self.add_score(score_tracker)
        self.add_info(hour_tracker)
        
    def delete_sheet(self, user, hour_tracker):
        worksheet_id = hour_tracker
        sheet_id = self.get_sheet_id(user['Name'])
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

    def delete_info(self, user, hour_tracker, score_tracker):
        user_data = self.sheets.get_data(columns=None, worksheet_id=score_tracker, tab_name='Main')
        index = user_data.index[user_data['Name'] == user['Name']].tolist()[0]
        body = {
            "requests": [
                {
                    "deleteDimension": {
                        "range": {
                            "sheetId": hour_tracker,
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
                spreadsheetId=hour_tracker, body=body
            ).execute()
        except HTTPError as e:
            print(e)

    def remove_member(self, user, hour_tracker, score_tracker):
        self.delete_sheet(user, hour_tracker)
        self.delete_info(user, hour_tracker, score_tracker)

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
                spreadsheetId=hour_id,
                range=f'{name}!{column}{index}',
                valueInputOption='USER_ENTERED',
                body=body,
            ).execute()
        except HTTPError as e:
            print(e)
            st.warning('error')
            return e

    def log(self, event, tab_name='Log', worksheet_id='', range='A:D'):
        '''creates an entry in the event log ("Log" tab of the hour tracker)'''
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
            print('could not create log', e)

    def update_entries(self, name, worksheet_id):
        data = self.sheets.get_data(columns=None, tab_name=name, worksheet_id=worksheet_id)
        st.session_state.current_user['Entries'] = data

    def create_folders_bulk(self):
        '''tries to create a folder for each member in the group if a folder does not already exist'''
        count = 0
        names = st.session_state.members['Name']
        for name in names:
            self.create_folder(name)
            count += 1
        return count

    def create_tabs_bulk(self):
        '''tries to create a tab for each member in the group if a tab does not already exist'''
        count = 0
        names = st.session_state.members['Name']
        for name in names:
            self.create_tab(name, st.session_state.config['HourTracker'])
            count += 1
        return count


    class BulkUtils:
        '''functions to update data in bulk'''
        def __init__(self):
            pass

        def create_folders(self):
            pass

        def create_tabs(self):
            pass

        def log(self, event_description, tab_name='Log', worksheet_id='', range='A:D'):
            pass


    class Members:
        '''The Member class contains function for adding, removing, and updating member info'''
        def __init__(self):
            pass

        def add(self, member_data, hour_tracker_id, score_tracker_id):
            '''adds member to master, drive, hour tracker, and score tracker'''
            pass

        def remove(self, member_data, hour_tracker_id, score_tracker_id):
            '''removes member from score tracker, hour tracker, drive, and master'''
            pass
        
        def update(self, field, member_name, index, values, hour_tracker_id):
            pass

