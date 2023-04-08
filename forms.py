import streamlit as st
from sqlalchemy import exists
from db import session, get_user_id
from models import User, Group, LanguageHour, Course, File, Score


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

            # Check if the username already exists in the database
            with session(db) as db:
                user_exists = db.query(exists().where(User.username==username)).scalar()
                if user_exists:
                    st.warning('A user with that username already exists.')
                    return

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

def add_group(db):
    # Declare the form
    with st.form('add_group'):
        st.write('Add Group')

        # Create input fields
        name = st.text_input('Name')
        if st.form_submit_button('Submit'):

            # Check if the group already exists in the database
            with session(db) as db:
                group_exists = db.query(exists().where(Group.name==name)).scalar()
                if group_exists:
                    st.warning('A group with that name already exists.')
                    return

            # Create the user database model
            group = Group(
                name=name,
            )
            
            # Commit it to the database
            with session(db) as db:
                db.add(group)
                st.success(f'Added Group!')

def add_score(db):
    # Declare the form
    with st.form('add_score'):
        st.write('Add Score')

        # Create input fields
        username = st.text_input('Name')
        language = st.text_input('Language', value='Arabic')
        dicode = st.text_input('Dicode', value='AP')
        listening = st.text_input('Listening Score')
        reading = st.text_input('Reading Score')
        speaking = st.text_input('Speaking score')
        date = st.date_input('Date')
        if st.form_submit_button('Submit'):

            user_id = get_user_id(db, username)
            # Create the user database model
            score = Score(
                user_id=user_id,
                language=language,
                dicode=dicode,
                listening=listening,
                reading=reading,
                speaking=speaking,
                date=date,
            )
            
            # Commit it to the database
            with session(db) as db:
                db.add(score)
                st.success(f'Added Score!')
