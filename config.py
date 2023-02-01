import streamlit as st


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
SESSION_VARS = [
    'service', # google services variable
    'loaded', 
    'selected_month', # month selection for rundown
    'current_user', # user accessing the site
    'authenticated', # has user successfully logged into the site
    'current_group', # group string
    'req_count', # number of requests to google services
    'members', # list of all members of the group
    'config', # user config
    'debug', # debug mode toggle
    'score_tracker',
    'show_total_month_hours',
    'total_month_all', # all members monthly hours, displayed in the rundown
]
INFO = 'Info'
MAIN = 'Main'
MEMBERS = 'Members'
DICODES = ['AU', 'AP', 'AE', 'DG', 'AD', 'AV', 'PV', 'PG', 'PF',]
CLANG_L = 'CLang L'
CLANG_R = 'CLang R'
DLTP_DATE = 'DLPT Date'
SLTE_DATE = 'SLTE Date'
SLTE_RANGE = {
    '3': 24,
    '2': 18,
    '1': 12,
}
ACTIVITIES = [
    'Listening',
    'Reading',
    'Speaking',
    'Transcription',
    'Mentoring',
    'Vocab',
    'SLTE',
    'DLPT',
    'ILTP upload',
    '623A upload',
]
