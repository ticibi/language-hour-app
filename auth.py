import bcrypt
import streamlit as st


def hash_password(password):
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt)

def validate_password(password, hash_password):
    return bcrypt.checkpw(
        password.encode('utf-8'),
        hash_password.decode().encode('utf-8')
    )

def authenticate_user(user, username, password, hashed_password):
    if not user:
        return False
    if user.username == username and validate_password(password, hashed_password):
        st.session_state.authenticated = True
        st.session_state.current_user = user
        st.success('Logged in!')
        return True
    st.warning('Invalid username or password.')
    st.session_state.authenticated = False
    st.session_state.current_user = None
    return False

