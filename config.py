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
INFO = 'Info'
MAIN = 'Main'
MEMBERS = 'Members'
DICODES = ['AU', 'AP', 'AE', 'DG', 'AD', 'AV', 'PV', 'PG', 'PF']
CLANG_L = 'CLang L'
CLANG_R = 'CLang R'
DLTP_DATE = 'DLPT Date'
SLTE_DATE = 'SLTE Date'
SLTE_RANGE = {
    str(3): 24,
    str(2): 18,
    str(1): 12,
}
ACTIVITIES = ['Listening', 'Reading', 'Speaking', 'Transcription', 'Vocab', 'SLTE', 'DLPT', 'ILTP upload', '623A upload']
