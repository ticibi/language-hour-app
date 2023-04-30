import streamlit as st

DB_USERNAME = st.secrets['DB_USERNAME']
DB_PASSWORD = st.secrets['DB_PASSWORD']
ADMIN_USERNAME = st.secrets['ADMIN_USERNAME']
ADMIN_PASSWORD = st.secrets['ADMIN_PASSWORD']
CONNECTOR = st.secrets['CONNECTOR']
HOST = st.secrets['HOST']
PORT = st.secrets['PORT']
DB1 = st.secrets['DB_1']
SILLYGOOSE = st.secrets['SILLYGOOSE']

SESSION_VARIABLES = [
    'db', # sql database session
    'engine', # sql database engine
    'session', # sql user session
    'authenticated', # user authentication status
    'logged_in', # current user login status
    'current_user', # current authenticated user
    'debug', # debug mode state
    'rain',
]
DICODES = ['AP', 'AU', 'AE', 'DG', 'AD', 'AV', 'PV', 'PG', 'PF',]
MODALITIES = [
    'Listening',
    'Reading',
    'Speaking',
    'Transcription',
    'Translation',
    'Vocabulary',
    'Mentoring',
    'Training Session',
    'Class',
    'Test',
]
LOTTIE_URL = 'https://lottiefiles.com/41769-hello-welcome'

BG_COLOR_DARK = '#0E1117'
BG_COLOR_LIGHT = '#262730'

CONTACT_MSG = 'Please contact an LTM to update your profile.'

DATATYPES = [
    'STRING',
    'INTEGER',
    'BOOLEAN',
    'DATE', 
    'DATETIME',
    'LARGEBINARY'
]
