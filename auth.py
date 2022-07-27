import bcrypt
import streamlit as st
from config import MEMBERS, MASTER_ID


class Authenticator:
    def __init__(self, service):
        self.service = service

    def hash_password(self, password):
        salt = bcrypt.gensalt()
        hashed_pw = bcrypt.hashpw(bytes(password, 'utf-8'), salt)
        return hashed_pw

    def authenticate(self, username, password):
        try:
            data = self.service.sheets.get_data(columns=None, tab_name=MEMBERS, worksheet_id=MASTER_ID, range='A:I')
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
