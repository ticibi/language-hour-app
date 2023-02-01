import streamlit as st
import config
from gservices import GServices


class Loader:
    def __init__(self, service, user, group):
        self.service: GServices = service
        self.user = user
        self.group = group

    def load_data(self):
        self.load_config()
        self.load_trackers()
        self.load_scores(self.user['Name'])
        self.load_files()
        self.load_entries()
        self.load_subordinates()

    def load_trackers(self):
        try:
            tracker = st.session_state.config['ScoreTracker']
            score_tracker = self.service.sheets.get_data(
                columns=None,
                tab_name=config.MAIN,
                worksheet_id=tracker,
                range='A:J'
            )
            st.session_state.score_tracker = score_tracker
        except Exception as e:
            print('could not load trackers', e)
            st.session_state.score_tracker = None

    def load_config(self):
        '''load user configuration'''
        try:
            data = self.service.sheets.get_data(
                columns=None,
                tab_name=config.INFO,
                worksheet_id=config.MASTER_ID,
            )
            st.session_state.config = data.query(
                f'Group == "{self.group}"'
            ).to_dict('records')[0]
        except Exception as e:
            print('could not load config:', e)
            st.session_state.config = None

    def load_subordinates(self):
        self.user['Subs'] = {}
        try:
            subs = st.session_state.members.query(
                f'Supervisor == "{self.user["Name"]}"'
            )['Name'].tolist()
            for sub in subs:
                self.user['Subs'].update({
                    sub: {
                        'Scores': None,
                        'Entries': None,
                    }
                })
                scores = st.session_state.score_tracker.query(
                    f'Name == "{sub}"'
                ).to_dict('records')[0]
                self.user['Subs'][sub]['Scores'] = scores
                entries = self.service.sheets.get_data(
                    columns=None,
                    tab_name=sub,
                    worksheet_id=st.session_state.config['HourTracker'],
                )
                self.user['Subs'][sub]['Entries'] = entries
        except Exception as e:
            print('could not load subordinates:', e)

    def load_entries(self):
        try:
            tracker = st.session_state.config['HourTracker']
            st.session_state.current_user['Entries'] = self.service.sheets.get_data(
                columns=None,
                tab_name=self.user['Name'],
                worksheet_id=tracker,
            )
        except Exception as e:
            print('could not load entries:', e)
            st.session_state.current_user['Entries'] = None

    def load_files(self):
        try:
            st.session_state.current_user['Files'] = self.service.drive.get_files(
                self.user['Name']
            )
        except Exception as e:
            print('could not load files:', e)
            st.session_state.current_user['Files'] = None

    def load_scores(self, name):
        try:
            user_scores = st.session_state.score_tracker.query(
                f'Name == "{name}"'
            ).to_dict('records')[0]
            user_scores.pop('Name')
            st.session_state.current_user['Scores'] = user_scores
        except Exception as e:
            print('could not load scores:', e)
            st.session_state.current_user['Scores'] = None
