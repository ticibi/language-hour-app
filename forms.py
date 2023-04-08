import streamlit as st
from models import User
from db import session


def add_user(db):
    # Declare the form
    with st.form('add_user'):
        st.write('Add User')

        # Create input fields
        name = st.text_input('Name', placeholder='First M Last')
        username = st.text_input('Username', placeholder='fmlast')
        password = st.text_input('Password', type='password')
        email = st.text_input('Email (optional)')
        is_admin = st.checkbox('Admin')
        group_id = st.number_input('Group ID',min_value=15, step=1)
        if st.form_submit_button('Submit'):

            # Create the user database model
            user = User(
                name=name,
                username=username,
                password_hash=password,
                email=email,
                is_admin=bool(is_admin),
                group_id=int(group_id),
            )
            
            # Commit it to the database
            with session(db) as db:
                db.add(user)
                st.success(f'Added User!')

