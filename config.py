import streamlit as st

DB_USERNAME = st.secrets['DB_USERNAME']
DB_PASSWORD = st.secrets['DB_PASSWORD']
HOST = st.secrets['HOST']
PORT = st.secrets['PORT']
DB_NAME = st.secrets['DB_NAME']
SESSION_VARIABLES = [
    'db', # sql database session
    'authenticated', # user authentication status
    'logged_in', # current user login status
    'current_user', # current authenticated user
    'debug', # debug mode state
]
DICODES = ['AU', 'AP', 'AE', 'DG', 'AD', 'AV', 'PV', 'PG', 'PF',]
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
