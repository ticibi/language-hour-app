import streamlit as st
from utils import initialize_session_state_variables
from config import SESSION_VARIABLES
from db import get_database_name
from ui import navbar, sidebar
from extensions import db1_engine, create_session
from models import DBConnect
from forms import add_dbconnect_user


st.set_page_config(
    page_title="Language Training Management",
    page_icon="🌐",
    layout="wide"
)
initialize_session_state_variables(SESSION_VARIABLES)


if __name__ == '__main__':

    # Connect to the 'master' database to get the connection information for the appropriate database
    db1 = create_session(db1_engine)
    db_name = get_database_name(db1_engine)
    st.sidebar.write(f'connected to :blue[{db_name}]')  

    # Prompt to add a user if there are none in the database
    if db1.query(DBConnect).count() < 1:
        add_dbconnect_user(db1)

    navbar()
    sidebar()

