from datetime import date
import calendar
import pytz

import streamlit as st
from streamlit_option_menu import option_menu

from auth import authenticate_user
from db import get_all_users, lowdown, test_db_connection, add_column, get_table, rundown, get_table_names, get_user_by, get_databases, connect_user_to_database, get_database_name, commit_or_rollback
from utils import header, download_database, divider, spacer, dot_dict, calculate_required_hours, filter_monthly_hours, calculate_total_hours, dot_dict, create_pdf, language_hour_history_to_string
from comps import submit_entry, download_file, download_to_excel, delete_row, display_entities, delete_entities
from models import DBConnect, LanguageHour, User, File, Score, Course, Message, Log
from config import MODALITIES, ADMIN_PASSWORD, ADMIN_USERNAME, CONTACT_MSG, DATATYPES
from load import load_user_models
from forms import edit_user, edit_course, edit_score, bar_graph, add_user, add_score, add_course, add_file, add_log, compose_message, upload_language_hours, add_database, add_dbconnect_user
from components.card import card
from extensions import db1, db1_engine
import calendar
from load import load_user_models
import pandas as pd
import datetime


def admin_access_warning(cols=st.columns):
    if access_warning(cols=cols):
        if not st.session_state.current_user.is_admin:
            msg2 = 'You are not authorized to access this tab.'
            cols[1].warning(msg2)
            return False
        return True

def access_warning(cols=None, sidebar=True):
    if not st.session_state.authenticated \
        or not st.session_state.current_user \
        or not st.session_state.logged_in:
        msg = 'You must log in to access this site.'
        if not cols:
            if sidebar:
                st.sidebar.warning(msg)
            else:
                st.warning(msg)
        else:
            cols[1].warning(msg)
        return False
    return True

def test_zone():
    columns = st.columns([1, 3, 1])
    if not admin_access_warning(columns):
        return
    
    data = st.session_state.current_user_data.LanguageHour
    #pie_chart(data)
    with st.expander('My Hours Graph', expanded=True):
        bar_graph(data)

def home():
    db = st.session_state.session
    columns = st.columns([1, 3, 1])

    if not access_warning(columns):
        return
    
    def display_language_hour_history():

        st.write(':blue[Select a month and year and download your 623A:]')
        # Create columns for the table
        cols = st.columns([1, 1, 1, 1])

        # Download the language hour history as an Excel file
        file = download_to_excel(db, LanguageHour, st.session_state.current_user.id)

        # Query the database for data
        history = st.session_state.current_user_data.LanguageHour
        scores = st.session_state.current_user_data.Score

        # Get the current month and year
        current_month = date.today().month
        current_year = date.today().year

        # Display input UI
        selected_month = cols[0].selectbox('Month', index=current_month, options=calendar.month_abbr)
        selected_year = cols[1].number_input('Year', value=current_year, min_value=2021, step=1)

        # Filter the language hour history for the current month
        month_history_filtered = filter_monthly_hours(history, list(calendar.month_abbr).index(selected_month), int(selected_year))
        hours_this_month = calculate_total_hours(month_history_filtered)

        # Fill in the PDF if there is enough data
        #if scores and hours_this_month and history_this_month:
        user = st.session_state.current_user
        record = language_hour_history_to_string(month_history_filtered)
        if not record:
            st.info('You have not submitted any hours during the selected month.')

        formatted_date = f'{selected_month}{selected_year}'
        if not scores:
            st.info(f'Your test scores cannot be found. {CONTACT_MSG}')
            return
        
        data_fields = {
            'Language': scores[0].langauge,
            'Member Name': f'{user.last_name.upper()} {user.first_name.upper()} {user.middle_initial.upper()}',
            'Hours': f'{hours_this_month} hrs',
            'Date': formatted_date,
            'Listening': scores[0].listening,
            'Reading': scores[0].reading,
            'Maintenance Record': record,
        }

        pdf = create_pdf(data_fields)
        spacer(cols[2], 2)
        filename = f'623A_{formatted_date.upper()}_{user.last_name.upper()}.pdf'
        if pdf is not None:
            cols[2].download_button(label='Download as 623A', data=pdf, file_name=filename, help='The selected month\'s language hours will be recorded on the 623A.')
        spacer(cols[3], 2)
        if file is not None:
            cols[3].download_button(label='Download as Excel', data=file, file_name='language_hours.xlsx', help='Microsoft Excel cannot open the excel file produced by this for some weird reason, but it can be opened with Google Sheets.')

    # Define a function to display the language hour history table
    def display_language_hours():
        upload_language_hours(db)

    # Define a function to display the entities in the LanguageHour table
    def display_language_hour_entities():
        display_entities(db, LanguageHour, user_id=st.session_state.current_user.id, exclude=['user_id'])

    columns = st.columns([1, 3, 1])
    with columns[1]:
        if st.session_state.current_user.is_admin:
            with st.expander('Monthly Rundown (admin)'):
                rundown(db)

            with st.expander('Search Users (admin)'):
                def highlight_row(row):
                    today = datetime.date.today()
                    delta = datetime.timedelta(days=60)
                    due_date = row.date + datetime.timedelta(days=365)
                    prior = due_date - delta
                    diff = due_date - today
                    if today >= prior:
                        st.write(f':orange[{row.dicode} DLPT coming due in **{diff.days}** days]')
                        return ['background-color: rgba(255, 227, 18, 0.2)'] * len(row)
                    return [''] * len(row) 

                users = get_all_users(db)
                cols = st.columns([1, 1, 1])
                username = cols[0].selectbox('Select a user:', options=[u.username for u in users])
                spacer(cols[1], 2)
                if cols[1].button('Search'):
                    user = get_user_by(db, 'username', username)
                    models = load_user_models(db, user.id)
                    keys = list(models.keys())
                    for i, model in enumerate(models.values()):
                        if keys[i] in ['Log', 'Message']: # don't really care about displaying these tables
                            continue
                        header(keys[i])
                        df = pd.DataFrame(model)
                        if not df.empty:
                            df = df.set_index('id')
                            if keys[i] == 'Score':
                                df = df.style.apply(highlight_row, axis=1)
                            st.dataframe(df)
                        else:
                            st.info(f'User does not have {keys[i]} data.')

        with st.expander('Language Hour History', expanded=True):
            display_language_hour_history()
            display_language_hour_entities()

def database_management():
    db = st.session_state.session
    engine = st.session_state.engine
    with st.expander('Database Management'):
        header('Download data to Excel:')
        cols = st.columns([1, 1, 1])
        table = cols[0].selectbox('Select a table: ', options=get_table_names(engine))
        spacer(cols[1], 2)
        cols[1].download_button('Download', data=download_database(table, engine), file_name=f'{table}.xlsx', mime='application/vnd.ms-excel')

        divider()
        header('Master Database Users:')
        add_dbconnect_user(db1, engine)
 
        divider()
        header('Test Database Connectivity:')
        cols = st.columns([1, 1, 1])
        databases = [d.name for d in get_databases(db1)]
        cols[0].selectbox('Select database:', options=databases)
        spacer(cols[1], 2)
        if cols[1].button('Test Connection'):
            if test_db_connection(engine):
                st.info(f'Connection to {get_database_name(engine)} is good!')
            else:
                st.warning(f'Connection {get_database_name(engine)} was bad :()')
 
        divider()
        header('Delete data from table:')
        delete_row(db)
 
        divider()
        header('Delete data from table:')
        delete_entities(db)

        if st.session_state.current_user.is_dev:
            divider()
            header('Add new data field to to table:')
            cols = st.columns([1, 1, 1])
            tables = get_table_names(engine)
            table = cols[0].selectbox('Select a table', key='table_select', options=tables)
            column_name = cols[1].text_input('Field name')
            data_type = cols[2].selectbox('Datae type:', options=DATATYPES)
            cols[0].write(f':red[]')
            if cols[0].button('Add Column'):
                add_column(engine, table, column_name, data_type)

        divider()
        header('Database changes:')
        cols = st.columns([1, 1, 1])
        if cols[0].button("Save database changes"):
            commit_or_rollback(db, commit=True)
 
        if cols[1].button("Discard database changes"):
            commit_or_rollback(db, commit=False)

def admin():
    db = st.session_state.session
    engine = st.session_state.engine
    if engine:
        db_name = get_database_name(engine)
        st.sidebar.write(f'connected to: :blue[{db_name}]')

    columns = st.columns([1, 3, 1])
    if not admin_access_warning(columns):
        return

    with columns[1]:
        database_management()
        upload_language_hours(db)

        with st.expander('Users'):
            header('User table:')
            display_entities(db, User, exclude=['password_hash'])
            header('Add new user:')
            add_user(db)
            header('Edit existing user:')
            edit_user(db)

        with st.expander('Score'):
            header('Score table:')
            display_entities(db, Score)
            header('Add new score:')
            add_score(db)
            header('Edit existing score:')
            edit_score(db)
 
        with st.expander('Course'):
            header('Course table:')
            display_entities(db, Course)
            header('Add new course:')
            add_course(db)
 
        with st.expander('Files'):
            add_file(db)
            display_entities(db, File)
            divider()
            download_file(db)
 
        with st.expander('LanguageHours'):
            display_entities(db, LanguageHour)
 
        with st.expander('Messages'):
            display_entities(db, Message)
 
        with st.expander('Logs'):
            display_entities(db, Log)
 
def sidebar():
    if not st.session_state.session:
        return
    
    db = st.session_state.session
    if not access_warning():
        return

    with st.sidebar:
        st.markdown(f'Welcome {st.session_state.current_user.first_name} 👋')
        st.subheader('Message Center')

        # Display message center
        with st.expander('Compose Message 📝'):
            compose_message(db, st.session_state.current_user.id)

        to_messages = []
        from_messages =  []

        if st.session_state.current_user_data.Message:
            for message in st.session_state.current_user_data.Message:
                if message.sender_id == st.session_state.current_user.id:
                    to_messages.append(message)
                elif message.recipient_id == st.session_state.current_user.id:
                    from_messages.append(message)

        with st.expander('My Messages 📬', expanded=True):
            if from_messages:
                st.write(f':blue[You have recieved {len(to_messages)} messages.]')
                for message in from_messages:
                    timestamp = message.timestamp.astimezone(pytz.timezone('US/Eastern')).strftime('%m-%d-%Y')
                    sender = get_user_by(db, 'id', message.sender_id)
                    if sender is not None:
                        card(
                            title=f'from: {sender.username} on {timestamp}',
                            text=message.content,
                        )
            else:
                st.write('You have not received any messages.')

        with st.expander('Sent Messages 📩'):
            if to_messages:
                st.write(f':blue[You have sent {len(to_messages)} messages.]')
                for message in to_messages:
                    timestamp = message.timestamp.astimezone(pytz.timezone('US/Eastern')).strftime('%m-%d-%Y')
                    recipient = get_user_by(db, 'id', message.recipient_id)
                    if recipient is not None:
                        card(
                            title=f'to: {recipient.username} on {timestamp}',
                            text=message.content,
                        )
            else:
                st.write('You have not sent any messages.')

    # Display session state variables
    with st.sidebar.expander('Session State', expanded=True):
        if st.session_state.current_user:
            if st.session_state.current_user.is_dev:
                st.write('(Dev)')
                if st.session_state.engine:
                    pool = st.session_state.engine.pool.status()
                    st.write(f':blue[{pool}]')
                st.write(st.session_state)

def navbar():
    nav_bar = option_menu(
        'Language Training Management',
        ['Login','Home', 'Submit Hour', 'Admin'], # 'TESTZONE'],
        icons=['key', 'house', 'send', 'tools'], # 'activity'],
        default_index=0,
        orientation='horizontal',
        menu_icon='diamond',
    )

    if nav_bar == 'Login':
        login()
    elif nav_bar == 'Home':
        home()
    elif nav_bar == 'Admin':
        admin()
    elif nav_bar == 'TESTZONE':
        test_zone()
    elif nav_bar == 'Submit Hour':
        submit_hour()
    else:
        home()

def submit_hour():
    db = st.session_state.session

    columns = st.columns([1, 3, 1])
    if not access_warning(columns):
        return
    
    if st.session_state.current_user:
        with columns[1]:
            
            # get data from session state
            month = date.today().month
            year = date.today().year

            history_this_month = filter_monthly_hours(st.session_state.current_user_data.LanguageHour, month, year)
            hours_this_month = calculate_total_hours(history_this_month)
            scores = st.session_state.current_user_data.Score
            if scores:
                hours_required = calculate_required_hours(scores[0])
            else:
                hours_required = 'X'
                st.info(f'Could not determine required hours because your test scores could not be found. {CONTACT_MSG}')

            # create the submission form
            with st.form('submit_hours', clear_on_submit=True):
                cols = st.columns([1, 1])
                _date = cols[0].date_input('Date')
                hours = cols[1].number_input(f'Hours ({hours_this_month}/{hours_required} completed)', min_value=1, step=1)
                modalities = st.multiselect('Modalities', options=MODALITIES)
                description = st.text_area('Description')
                if st.form_submit_button('Submit', type='primary'):
                    if description and modalities:
                        entry = LanguageHour(
                            date=_date,
                            hours=int(hours),
                            description=description,
                            modalities=modalities,
                            user_id=st.session_state.current_user.id,
                        )
                        submit_entry(db, entry)
                        st.balloons()
                        st.success(f'{hours} language hours submitted!')
                        add_log(db, st.session_state.current_user.id, f'user_id:{st.session_state.current_user.id} logged in.')
                    else:
                        st.warning('You must fill out every field.')

def global_admin():
    # Display global admin page
    with st.expander('Global Admin', expanded=True):
        add_database(db1)
        add_dbconnect_user(db1, db1_engine)
        delete_entities(db1)
        users = get_table(db1, DBConnect)
        st.table(users)

def login():
    db = st.session_state.session if st.session_state.session else db1
    columns = st.columns([1, 1, 1])
    # Display Login view
    if not st.session_state.authenticated:
        with columns[1]:
            container = st.empty()
            with container:
                form = st.form('login_form')
                form.subheader('Login')
                username = form.text_input('Username')
                password = form.text_input("Password", type="password")
                if form.form_submit_button('Login'):
                    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                        # Display global admin page
                        global_admin()
                        return    
                    
                    elif username and password:
                        db = connect_user_to_database(username)
                        if not db:
                            st.warning('User not found.')
                            return

                        user = get_user_by(db, 'username', username)
                        if not user:
                            st.warning('Could not find user.')
                            return
                        
                        if authenticate_user(user, username, password, user.password_hash):
                            with st.spinner('Loading...'):
                                user_data = load_user_models(db, st.session_state.current_user.id)
                                st.session_state.current_user_data = user_data
                            container.empty()
                            st.success('Logged in!')
                            #add_log(_db, st.session_state.current_user.id, f'{username} logged in.')
                    else:
                        st.warning('Invalid username or password. Return to Login page.')
                        return

