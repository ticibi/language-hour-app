import streamlit as st
from page import Pages

st.set_page_config(page_title="Language Hour Entry", page_icon="🌐", layout="centered")

def main():
    if 'authenticated' not in st.session_state or \
    not st.session_state.authenticated:
        st.info('You are not logged in')
        return
    page = Pages()
    page.welcome_message()
    page.account()
    page.scores()

main()
