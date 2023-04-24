import streamlit as st
from sqlalchemy import exists
from db import get_score_by_id, check_username_exists, get_table, get_database_name, get_all_users, upload_bulk_excel, get_databases, session, get_user_by
from models import DBConnect, User, Course, File, Score, Log, Message, Database
from utils import spacer, read_excel
from datetime import datetime
import pytz
from extensions import db1
import matplotlib.pyplot as plt
import pandas as pd
from config import BG_COLOR_DARK, BG_COLOR_LIGHT, DICODES
import calendar
from config import HOST, PORT, DB_PASSWORD, DB_USERNAME
from auth import hash_password


def add_dbconnect_user(db, engine):
    cols = st.columns([1, 1, 1])

    databases = [d.name for d in get_databases(db)]
    databases.insert(0, 'db_1')
    users = get_table(db1, DBConnect)

    username = cols[0].text_input('Username:')
    db_name = cols[1].selectbox('Assigned database:', index=databases.index(get_database_name(engine)),options=databases)
    db_id = databases.index(db_name)

    spacer(cols[2], 2)
    if cols[2].button('Add user'):
        user_exists = db.query(exists().where(DBConnect.username==username)).scalar()
        if user_exists:
            st.warning('Username already exists.')
            return
        with session(db) as db:
            user = DBConnect(
                username=username,
                db_id=db_id,
            )
            db.add(user)
            st.success('User added to ')

    #cols = st.columns([2])
    #cols2 = st.columns([1, 2])
    #slider = cols2[0].slider('page', min_value=1, max_value=len(users)-1, step=1)
    #p_df = paginate_dataframe(users, 10, slider)
    df = pd.DataFrame(users).set_index('id')
    st.dataframe(df)
    #if st.button('Clear database'):
    #    with session(db) as db:
    #        db.query(DBConnect).delete()
    #        #reset_autoincrement(db1_engine, DBConnect.__tablename__)
    #        st.info('Deleted all DBConnect users.')    

def add_database(db):
    # Declare form
    with st.form('add_database'):
        st.write('Create database')

        # Create input fields
        name = st.text_input('Database name')
        if st.form_submit_button('Submit'):
            with session(db) as db:
                db_exists = db.query(exists().where(Database.name==name)).scalar()
                if db_exists:
                    st.warning('A database with that name already exists.')
                    return
                
                # Create the database model
                database = Database(
                    name=name,
                    host=HOST,
                    port=PORT,
                    username=DB_USERNAME,
                    password=DB_PASSWORD,
                )

                try:
                    db.add(database)
                    st.success('Database added successfully!')
                except:
                    st.warning('Failed to add database to database.')

def add_user(db, title='Add User'):
    # Declare the form
    #st.info('Make sure to add username to master database in Database Management')
    with st.form('add_user', clear_on_submit=True):

        # Create input fields
        first_name = st.text_input('First name')
        middle_initial = st.text_input('Middle initial')
        last_name = st.text_input('Last name')
        username = st.text_input('Username', placeholder='fmlast')
        password = st.text_input('Password', type='password')
        email = st.text_input('Email (optional)')
        if title == 'Initial User:':
            is_admin = st.checkbox('is Admin?', value=True)
            is_dev = st.checkbox('is Dev?', value=True)
        else:
            is_admin = st.checkbox('is Admin?')
            is_dev = st.checkbox('is Dev?')
        if st.form_submit_button('Submit'):

            # Create the database model
            user = User(
                first_name=first_name,
                middle_initial=middle_initial,
                last_name=last_name,
                username=username,
                password_hash=hash_password(password),
                email=email,
                is_admin=bool(is_admin),
                is_dev=bool(is_dev),
            )

            databases = [d.name for d in get_databases(db1)]
            databases.insert(0, 'db_1')
            db_name = get_database_name(st.session_state.engine)
            db_id = databases.index(db_name)

            dbc_user = DBConnect(
                username=username,
                db_id=db_id,
            )

            # Check if the username already exists in the databases
            with session(db) as _db:
                if check_username_exists(_db, username):
                    st.warning('A user with that username already exists.')
                    return
                try:
                    _db.add(user)
                    st.success('User added successfully!')
                except:
                    st.warning('Failed to add user.')
                
            with session(db1) as _db1:
                if check_username_exists(_db1, username):
                    return
                try:                
                    _db1.add(dbc_user)
                    st.info(f'User linked to {db_name}!')
                except:
                    st.warning(f'Failed to add user to {db_name}.')
            
def edit_user(db):
    # Get the user model
    users = [d.username for d in get_all_users(db)]
    username = st.selectbox('Username', options=users)
    user = get_user_by(db, 'username', username)

    # Create input fields with user
    first_name = st.text_input('First name', value=user.first_name)
    middle_initial = st.text_input('Middle initial', value=user.middle_initial)
    last_name = st.text_input('Last name', value=user.last_name)
    # password = st.text_input('Password', value=user.password_hash, type='password')
    email = st.text_input('Email (optional)', value=user.email)
    is_admin = st.checkbox('is Admin?', value=bool(user.is_admin))
    is_dev = st.checkbox('is Dev?', value=bool(user.is_dev))

    if st.button('Save', key='save_edit_user'):
        with session(db) as _db:
            user = db.query(User).get(user.id)
            if user is None:
                st.warning('User data not found.')
            if user.first_name != first_name:
                user.first_name = first_name
            if user.middle_initial != middle_initial:
                user.middle_initial = middle_initial
            if user.last_name != last_name:
                user.last_name = last_name
            if user.email != email:
                user.email = email
            if bool(user.is_admin) != bool(is_admin):
                user.is_admin = bool(is_admin)
            if bool(user.is_dev) != bool(is_dev):
                user.is_dev = bool(is_dev)
            st.info('Updated user info.')
            _db.commit()
            _db.close()

def add_score(db):
    # Declare the form
    with st.form('add_score'):
        #username = st.text_input('Username', value=st.session_state.current_user.username)
        users = [u.username for u in get_all_users(db)]
        cols = st.columns([1, 1])
        username = cols[0].selectbox('Username', options=users)
        date = cols[1].date_input('Test Date')
        cols = st.columns([1, 1])
        language = cols[0].text_input('Language', value='Arabic')
        dicode = cols[1].selectbox('Dicode', index=0, options=DICODES)
        cl = st.checkbox('Control Language')
        cols = st.columns([1, 1, 1])
        listening = cols[0].text_input('Listening Score')
        reading = cols[1].text_input('Reading Score')
        speaking = cols[2].text_input('Speaking score')
        if st.form_submit_button('Submit'):

            user = get_user_by(db, 'username', username)
            if not user:
                st.warning('User not found.')
                return

            # Create the database model
            score = Score(
                user_id=user.id,
                langauge=language,
                dicode=dicode,
                CL=bool(cl),
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

def edit_score(db):
    # Load score data
    cols = st.columns([1, 1, 1])
    score_id = cols[0].number_input('Enter score row ID for data to populate:', step=1)
    score = get_score_by_id(db, score_id)
    if not score:
        st.info('Score data not found.')
        return
    cols = st.columns([1, 1, 1])
    username = cols[0].text_input('Username', value=get_user_by(db, 'id', score.user_id).username, disabled=True)
    date = cols[1].date_input('Test Date', value=score.date)
    cols = st.columns([1, 1, 1])
    language = cols[0].text_input('Language', value=score.langauge)
    dicode = cols[1].selectbox('Dicode', index=0, options=DICODES)
    spacer(cols[2], 2)
    cl = cols[2].checkbox('is this the user\'s Control Language?', value=bool(score.CL) if score.CL else False)
    cols = st.columns([1, 1, 1])
    listening = cols[0].text_input('Listening Score', value=score.listening)
    reading = cols[1].text_input('Reading Score', value=score.reading)
    speaking = cols[2].text_input('Speaking score', value=score.speaking)
    if st.button('Save changes', key='save_edit_score'):
        with session(db) as _db:
            score = db.query(Score).get(score_id)
            if score is None:
                st.warning('Score data not found.')
                return
            if score.date != date:
                score.date = date
            if score.langauge != language:
                score.langauge = language
            if score.dicode != dicode:
                score.dicode = dicode
            if bool(score.CL) != bool(cl):
                score.CL = bool(cl)
            if score.listening != listening:
                score.listening = listening
            if score.reading != reading:
                score.reading = reading
            if score.speaking != speaking:
                score.speaking = speaking
            st.info('Updated score info.')
            _db.commit()
            _db.close()
            
def add_course(db):
    # Declare the form
    with st.form('add_course'):
        # Create input fields
        username = st.selectbox('Username', options=[x.username for x in get_all_users(db)])
        course_name = st.text_input('Course Name')
        course_code = st.text_input('Course Code')
        course_length = st.number_input('Course Length (hours)', step=1)
        start_date = st.date_input('Start Date')
        end_date = st.date_input('End Date')
        if st.form_submit_button('Submit'):

            user_id = get_user_by(db, 'username', username)
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

def edit_course(db):
    pass

def add_log(db, user_id, message):
    now = datetime.now(pytz.timezone("America/New_York"))
    log = Log(
        user_id=user_id,
        message=message,
        timestamp=now,
    )
    with session(db) as db:
        db.add(log)

def add_file(db):
    # Create the file upload form
    file = st.file_uploader('Choose a file', type=['txt', 'pdf', 'png', 'jpg', 'jpeg'])

    if file is not None:
        # Get the file contents
        file_contents = file.read()

        # Add the file record to the database
        new_file = File(
            user_id=st.session_state.current_user.id,
            name=file.name,
            content=file_contents,
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

        users = get_all_users(db)
        names = [f'{x.last_name}, {x.first_name} ({x.username})' for x in users]
        usernames = [x.username for x in users]
        
        # Create input fields
        recipient = st.selectbox('Recipient', index=0, options=names)
        content = st.text_area('Message Content', max_chars=250)
        if st.form_submit_button('Send'):
            if not recipient:
                st.warning('You must specify a recipient.')
                return
            if not content:
                st.warning('Message cannot not be blank.')

            # Check if recipient is valid and get recipient ID
            recipient_index = names.index(recipient)
            user = get_user_by(db, 'username', usernames[recipient_index])
            if not user:
                st.warning('Could not find recipient.')
                return

            # Create the database model
            message = Message(
                sender_id=user_id,
                recipient_id=user.id,
                read=False,
                archived=False,
                content=content,
                timestamp=datetime.utcnow(),
            )

            # Commit it to the database
            with session(db) as db:
                try:
                    db.add(message)
                    st.success(f'Message sent to {usernames[recipient_index]}')
                except:
                    st.warning('Failed to send message.')
        
def upload_language_hours(db):
    if not st.session_state.current_user:
        return
    with st.expander('Upload language hours'):
        file = st.file_uploader(':green[Upload an excel file here to populate history. **Make sure the file is removed from the uploader after submitting.**]', type=['xlsx'], help='Make sure to click the X to remove the file from the uploader once the file has been uploaded to prevent duplicates.')
        cols = st.columns([1, 1, 1])
        user_id = cols[0].number_input('Enter ID of user the data will be added to:', value=st.session_state.current_user.id, step=1)
        spacer(cols[1], 2)
        is_bulk = cols[1].checkbox('Bulk upload?', help='This will go through each tab in the provided excel or google sheet and add the corresponding language hour entry to the user. Tab names should be formatted "Lastname, Firstname". If a user cannot be found, it will skip over them and continue. Make sure that all users with an excel tab are added to the database before bulk uploading.')
        if file:
            if is_bulk:
                upload_bulk_excel(db, file)
            else:
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


