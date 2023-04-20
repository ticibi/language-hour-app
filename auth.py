import bcrypt
import streamlit as st

def hash_password(password):
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt)

def validate_password(password, hash_password):
    try:
        if bcrypt.checkpw(
            password.encode('utf-8'),
            hash_password.encode('utf-8')
        ):
            return True
    except ValueError as e:
        print('error:', e)
        return False

def authenticate_user(user_dict, username, password, hashed_password):
    if not user_dict:
         return False
    if user_dict.username == username:
        if validate_password(password, hashed_password):
            st.session_state.authenticated = True
            add_authenticated_user_to_session_state(user_dict)
            st.success('Logged in!')
            print('logged in')
            return True
    st.warning('Invalid username or password. Return to Login page.')
    st.session_state.authenticated = False
    st.session_state.current_user = None
    return False

def add_authenticated_user_to_session_state(user_dict):
     del user_dict['password_hash']
     st.session_state.current_user = user_dict
     st.session_state.logged_in = True
     print('added authenticated user to session state')

