import streamlit as st
from sqlalchemy import exists
from db import session, get_user
from models import User, Group, LanguageHour, Course, File, Score, Log, Message
from utils import read_excel, dot_dict
from datetime import datetime
import pytz
import matplotlib.pyplot as plt
import pandas as pd
from config import BG_COLOR_DARK, BG_COLOR_LIGHT
import calendar

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

            # Create the database model
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
                try:
                    db.add(user)
                    st.success(f'User added successfully.')
                except:
                    st.warning('Failed to add user.')

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

            # Create the database model
            group = Group(
                name=name,
            )
            
            # Commit it to the database
            with session(db) as db:
                try:
                    db.add(group)
                    st.success(f'Group created successfully.')
                except:
                    st.warning('Failed to create group.')

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

            user_id = get_user(db, username)
            # Create the database model
            score = Score(
                user_id=username,
                langauge=language,
                dicode=dicode,
                listening=listening,
                reading=reading,
                speaking=speaking,
                date=date,
            )
            
            # Commit it to the database
            with session(db) as db:
                try:
                    db.add(score)
                    st.success(f'Score added successfully.')
                except:
                    st.warning('Failed to add score.')

def add_course(db):
    # Declare the form
    with st.form('add_course'):
        st.write('Add Course')

        # Create input fields
        username = st.text_input('Name')
        course_name = st.text_input('Course Name')
        course_code = st.text_input('Course Code')
        course_length = st.number_input('Course Length (hours)', step=1)
        start_date = st.date_input('Start Date')
        end_date = st.date_input('End Date')
        if st.form_submit_button('Submit'):

            user_id = get_user(db, username)
            # Create the database model
            course = Course(
                user_id=user_id,
                name=course_name,
                code=course_code,
                length=course_length,
                start_date=start_date,
                end_date=end_date,
            )
            
            # Commit it to the database
            with session(db) as db:
                try:
                    db.add(course)
                    st.success(f'Course added successfully.')
                except:
                    st.warning('Failed to add course.')

def add_log(db, user_id, message):
    now = datetime.now(pytz.timezone("America/New_York"))
    log = Log(
        user_id=user_id,
        message=message,
        date=now,
    )
    with session(db) as db:
        db.add(log)

def add_file(db):
    # Create the file upload form
    st.write('Upload a file')
    file = st.file_uploader('Choose a file', type=['txt', 'pdf', 'png', 'jpg', 'jpeg'])

    if file is not None:
        # Get the file contents
        file_contents = file.read()

        # Add the file record to the database
        new_file = File(
            user_id=st.session_state.current_user.id,
            name=file.name,
            file=file_contents,
        )
        
        # Add the file record to the database
        with session(db) as db:
            try:
                session.add(new_file)
                st.success('File uploaded successfully.')
            except:
                st.warning('Failed to upload file.')

def compose_message(db, user_id):
    # Declare the form
    with st.form('compose_message', clear_on_submit=True):

        # Create input fields
        recipient = st.text_input('Recipient Username')
        content = st.text_area('Message Content', max_chars=250)
        if st.form_submit_button('Send'):
            if not recipient:
                st.warning('You must specify a recipient.')
                return
            if not content:
                st.warning('Message cannot not be blank.')

            # Check if recipient is valid and get recipient ID
            user = dot_dict(get_user(db, recipient))
            if not user:
                st.warning('Could not find recipient.')
                return

            # Create the database model
            message = Message(
                sender_id=user_id,
                recipient_id=user.id,
                content=content,
                timestamp=datetime.utcnow(),
            )

            # Commit it to the database
            with session(db) as db:
                try:
                    db.add(message)
                    st.success('Message sent successfully.')
                except:
                    st.warning('Failed to send message.')
        
def upload_language_hours(db):
    with st.expander('Language Hour Upload'):
        file = st.file_uploader(':green[Upload an excel file here to populate history]', type=['xlsx'])
        cols = st.columns([1, 3])
        user_id = cols[0].number_input('User ID', value=st.session_state.current_user.id, step=1)
        if file:
            language_hours = read_excel(file, user_id)
            with session(db) as db:
                for x in language_hours:
                    db.add(x)
                st.success('Language Hours uploaded to database. Click the "X" to remove the file from uploader.')

def pie_chart(data):
    # Create a pie chart of the modalities and hours
    modalities = [d.modalities.split(' ') for d in data]
    hours = [d.hours for d in data]

    fig1, ax1 = plt.subplots()
    ax1.pie(hours, labels=modalities, autopct="%1.1f%%", startangle=90)
    ax1.axis("equal")
    st.pyplot(fig1)

def bar_graph(data):
    # Create a bar graph of the month and hours
    current_year = datetime.today().year
    months = []
    hours = []
    for d in data:
        if d.date.year == current_year:
            months.append(calendar.month_abbr[d.date.month])
            hours.append(d.hours)

    fig2, ax2 = plt.subplots(figsize=(6, 3))
    ax2.bar(months, hours, color=['dodgerblue'])
    ax2.set_ylabel("Hours", color='white')
    ax2.set_xticks(range(1, len(months)))

    # Adjust the colors
    ax2.set_facecolor(BG_COLOR_LIGHT)
    fig2.set_facecolor(BG_COLOR_DARK)
    ax2.tick_params(axis='both', colors='white')

    st.pyplot(fig2)


