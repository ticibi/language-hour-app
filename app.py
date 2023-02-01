from operator import contains
import streamlit as st
from utils import initialize_session_state_variables
from pages import Pages
from auth import Authenticator
from gservices import GServices
from loader import Loader
import config


st.set_page_config(page_title="Language Hour Entry", page_icon="🌐", layout="wide")
session_variables = config.SESSION_VARS
initialize_session_state_variables(session_variables)
st.session_state.req_count = 0

if __name__ == '__main__':
    service = GServices(config.SERVICE_ACCOUNT, config.SCOPES)
    st.session_state.service = service
    auth = Authenticator(service)
    pages = Pages()

    if st.session_state.authenticated:
        with st.spinner('loading application...'):
            if not st.session_state.loaded:
                loader = Loader(
                    st.session_state.service,
                    st.session_state.current_user,
                    st.session_state.current_user['Group']
                )
                try:
                    loader.load_data()
                    st.session_state.loaded = True
                except:
                    st.error('error')
        try:
            #pages.banner()
            pages.sidebar()
            pages.main_page()
        except Exception as e:
            pass

        if contains(st.session_state.current_user['Flags'], 'admin'):
            try:
                pages.admin_sidebar()
                pages.admin_page()
            except Exception as e:
                st.error('error')

        if contains(st.session_state.current_user['Flags'], 'dev'):
            try:
                pages.dev_sidebar()
                pages.dev_page()
            except Exception as e:
                st.error('error')
    else:
        auth.login()
