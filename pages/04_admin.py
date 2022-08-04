import streamlit as st
from operator import contains
from page import Pages, AdminPage

st.set_page_config(page_title="Language Hour Entry", page_icon="🦖", layout="centered")

def main():
    if 'authenticated' not in st.session_state or \
    not st.session_state.authenticated:
        st.info('You are not logged in')
        return
    if not contains(st.session_state.current_user['Flags'], 'admin'):
        st.warning('You do not have admin permissions')
        return
    
    page = Pages(icon='🦖')
    page.welcome_message()
    admin = AdminPage(icon='🦖')
    admin.rundown()
    admin.add_member()
    admin.member_actions()
    admin.admin_actions()
    admin.links()

main()
