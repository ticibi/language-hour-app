import streamlit as st

def initialize_session_state(vars):
    for var in vars:
        if var not in st.session_state:
            st.session_state[var] = None

