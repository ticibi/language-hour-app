from datetime import date
import calendar
import pytz

import streamlit as st
from streamlit_option_menu import option_menu

from auth import authenticate_user
from db import get_table_names, get_user_by_id, get_databases, connect_user_to_database, get_database_name, get_user_by_username, commit_or_rollback
from utils import download_database, divider, spacer, dot_dict, calculate_required_hours, filter_monthly_hours, calculate_total_hours, dot_dict, create_pdf, language_hour_history_to_string
from comps import submit_entry, download_file, download_to_excel, delete_row, display_entities, delete_entities
from models import LanguageHour, User, File, Score, Course, Message, Log, MODELS
from config import MODALITIES, ADMIN_PASSWORD, ADMIN_USERNAME, CONTACT_MSG
from load import load_user_models
from forms import bar_graph, add_user, add_score, add_course, add_file, add_log, compose_message, upload_language_hours, add_database, add_dbconnect_user
from components.card import card
from extensions import db1
import calendar


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
        cols = st.columns([1, 1, 2])

        # Download the language hour history as an Excel file
        file = download_to_excel(db, LanguageHour, st.session_state.current_user.id)
        if file:
            cols[0].download_button(label='Download Excel', data=file, file_name='language_hours.xlsx')

        # Query the database for data
        history = st.session_state.current_user_data.LanguageHour
        scores = st.session_state.current_user_data.Score

        # Get the current month and year
        current_month = date.today().month
        current_year = date.today().year

        selected_month = cols[0].selectbox('Month', index=current_month, options=calendar.month_abbr)
        selected_year = cols[1].number_input('Year', value=current_year, min_value=2021, step=1)

        # Filter the language hour history for the current month
        month_history = filter_monthly_hours(history, list(calendar.month_abbr).index(selected_month), int(selected_year))
        hours_this_month = calculate_total_hours(month_history)

        # Fill in the PDF if there is enough data
        #if scores and hours_this_month and history_this_month:
        user = st.session_state.current_user
        record = language_hour_history_to_string(month_history)
        if not record:
            st.info('You have not submitted any hours during the selected month.')

        formatted_date = f'{selected_month}{selected_year}'
        if not scores:
            st.info(f'Your test scores cannot be found. {CONTACT_MSG}')
            return
        
        data_fields = {
            'Language': scores[0].langauge,
            'Member Name': f'{user.last_name.upper()} {user.first_name.upper()} {user.middle_initial.upper()}',
            'Hours Studied': hours_this_month,
            'Date': formatted_date,
            'Listening': scores[0].listening,
            'Reading': scores[0].reading,
            'Maintenance Record': record,
        }

        pdf = create_pdf(data_fields)
        spacer(cols[2], 2)
        filename = f'623A_{formatted_date.upper()}_{user.last_name.upper()}.pdf'
        cols[2].download_button(label='Download', data=pdf, file_name=filename)

    # Define a function to display the language hour history table
    def display_language_hours():
        upload_language_hours(db)

    # Define a function to display the entities in the LanguageHour table
    def display_language_hour_entities():
        display_entities(db, LanguageHour, user_id=st.session_state.current_user.id, exclude=['user_id'])

    columns = st.columns([1, 3, 1])
    with columns[1]:
        # if user is admin, display their respective group's users with scores
        # button to calculate the monthly language hours rundown
        #display_language_hours()
        if st.session_state.current_user.is_admin:
            with st.expander('Monthly Rundown'):
                pass

        with st.expander('Language Hour History', expanded=True):
            display_language_hour_history()
            display_language_hour_entities()

def database_management():
    db = st.session_state.session
    engine = st.session_state.engine
    with st.expander('Database Management'):
        st.write('Download database to excel:')
        cols = st.columns([1, 1, 1])
        table = cols[0].selectbox('Select a table: ', options=get_table_names(engine))
        spacer(cols[1], 2)
        cols[1].download_button('Download', data=download_database(table, engine), file_name=f'{table}.xlsx', mime='application/vnd.ms-excel')

        divider()
        add_dbconnect_user(db1)

        cols = st.columns([2, 1])
        databases = [d.name for d in get_databases(db1)]
        cols[0].selectbox('Select database connection:', options=databases)
        spacer(cols[1], len=2)
        if cols[1].button('Select'):
            pass

        divider()
        delete_row(db)

        divider()
        delete_entities(db)

        divider()
        st.write('Database changes:')   
        cols = st.columns([1, 1, 1])
        if cols[0].button("Save changes"):
            commit_or_rollback(db, commit=True)

        if cols[1].button("Discard changes"):
            commit_or_rollback(db, commit=False)

def admin():
    db = st.session_state.session
    if st.session_state.engine:
        db_name = get_database_name(st.session_state.engine)
        st.sidebar.write(f'connected to: :blue[{db_name}]')

    columns = st.columns([1, 3, 1])
    if not admin_access_warning(columns):
        return

    with columns[1]:
        upload_language_hours(db)

        with st.expander('Users'):
            add_user(db)
            display_entities(db, User, exclude=['password_hash'])

        with st.expander('Score'):
            add_score(db)
            display_entities(db, Score)

        with st.expander('Course'):
            add_course(db)
            display_entities(db, Course)

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

        database_management()

def sidebar():
    if not st.session_state.session:
        return
    
    db = st.session_state.session

    if not access_warning():
        return

    with st.sidebar:
        st.subheader('Message Center')
        # Display message center
        with st.expander('Compose Message 📝'):
            compose_message(db, st.session_state.current_user.id)   

        with st.expander('My Messages 📬', expanded=True):
            if st.session_state.current_user_data.Message:
                for message in st.session_state.current_user_data.Message:
                    sender = get_user_by_id(db, message.sender_id)
                    if sender:
                        sender = dot_dict(sender)
                        timestamp = message.timestamp.astimezone(pytz.timezone('US/Eastern')).strftime('%m-%d-%Y')
                        card(
                            title=f'from: {sender.username} on {timestamp}',
                            text=message.content,
                        )
            else:
                st.write('You have no messages.')

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
        ['Login','Home', 'Submit Hour', 'Admin', 'TESTZONE'],
        icons=['key', 'house', 'send', 'tools', 'activity'],
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

def login():
    db = st.session_state.session
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
                        # Add databases
                        # Add dbconnect users
                        pass
                    
                    elif username and password:
                        db = connect_user_to_database(username)
                        if not db:
                            st.warning('User not found.')
                            return

                        user = get_user_by_username(db, username)
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

