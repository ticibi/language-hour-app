from operator import contains
import streamlit as st
from utils import initialize_session_state_variables
from pages import Pages
from auth import Authenticator
from gservices import GServices
import config


st.set_page_config(page_title="Language Hour Entry", page_icon="🌐", layout="centered")
session_variables = ['selected_month', 'current_user', 'authenticated', 'current_group', 'req_count', 'members', 'config', 'req_count', 'debug', 'score_tracker', 'show_total_month_hours', 'total_month_all',]
initialize_session_state_variables(session_variables)
st.session_state.req_count = 0
        
 
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

def load():
    name = st.session_state.current_user['Name']
    group = st.session_state.current_user['Group']
    st.session_state.current_group = group

    try:
        data = service.sheets.get_data(columns=None, tab_name=config.INFO, worksheet_id=config.MASTER_ID)
        st.session_state.config = data.query(f'Group == "{group}"').to_dict('records')[0]
    except:
        st.session_state.config = None

    try:
        score_tracker = st.session_state.config['ScoreTracker']
        all_scores = service.sheets.get_data(columns=None, tab_name=config.MAIN, worksheet_id=score_tracker, range='A:J')
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
    service = GServices(config.SERVICE_ACCOUNT, config.SCOPES)
    auth = Authenticator(service)
    pages = Pages(service)

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
