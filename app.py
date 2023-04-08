import streamlit as st
from utils import initialize_session_state_variables
from config import SESSION_VARIABLES
from db import create_db
from ui import navbar, sidebar

st.set_page_config(
    page_title="Language Training Management",
    page_icon="🌐",
    layout="wide"
)
initialize_session_state_variables(SESSION_VARIABLES)

if __name__ == '__main__':
    db = create_db()
    
    navbar(db)
    sidebar(db)
