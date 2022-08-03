import streamlit as st
from operator import contains
from page import Pages, DevPage

st.set_page_config(page_title="Language Hour Entry", page_icon="🦖", layout="centered")

def main():
    if 'authenticated' not in st.session_state or \
    not st.session_state.authenticated:
        st.info('You are not logged in')
        return
    if not contains(st.session_state.current_user['Flags'], 'dev'):
        st.warning('You do not have dev permissions')
        return
    page = Pages()
    page.welcome_message()
    dev = DevPage()
    dev.dev_page()
    dev.dev_sidebar()

main()
