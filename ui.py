from datetime import date
import calendar
import pytz

import streamlit as st
from streamlit_option_menu import option_menu

from auth import authenticate_user, hash_password
from db import get_user, commit_or_rollback
from utils import dot_dict, calculate_required_hours, filter_monthly_hours, calculate_total_hours, dot_dict, create_pdf, language_hour_history_to_string
from comps import submit_entry, download_file, download_to_excel, delete_row, display_entities, delete_entities
from models import LanguageHour, User, Group, File, Score, Course, Message, Log
from config import MODALITIES
from load import load_user_models
from forms import pie_chart, bar_graph, add_user, add_group, add_score, add_course, add_file, add_log, compose_message, upload_language_hours
from components.card import card


def test_zone(db):
    if not st.session_state.current_user.is_admin:
        st.warning('You are not authorzied to access the test zone.')
        return
    
    data = st.session_state.current_user_data.LanguageHour
    #pie_chart(data)
    with st.expander('My Hours Graph', expanded=True):
        bar_graph(data)

def home(db):
    columns = st.columns([1, 3, 1])
    if not st.session_state.authenticated:
        with columns[1]:
            st.warning('You must log in to access this site.')
            return
        
    def display_language_hour_history():
        # Create columns for the table
        cols = st.columns([1, 1, 2])

        # Download the language hour history as an Excel file
        file = download_to_excel(db, LanguageHour, st.session_state.current_user.id)
        cols[0].download_button(label='Download Excel', data=file, file_name='language_hours.xlsx')

        # Query the database for data
        history = st.session_state.current_user_data.LanguageHour
        scores = st.session_state.current_user_data.Score[0]

        # Get the current month and year
        month = date.today().month
        year = date.today().year

        # Filter the language hour history for the current month
        history_this_month = filter_monthly_hours(history, month, year)
        hours_this_month = calculate_total_hours(history_this_month)

        # Fill in the PDF if there is enough data
        #if scores and hours_this_month and history_this_month:
        name = st.session_state.current_user.name.split(' ')
        record = language_hour_history_to_string(history_this_month)
        if not record:
            st.info('You have not submitted any hours yet this month.')
        formatted_date = f'{calendar.month_abbr[date.today().month]}-{date.today().year}'
        data_fields = {
            'Language': scores.langauge,
            'Member Name': f'{name[2].upper()} {name[0].upper()} {name[1].upper()}',
            'Hours Studied': hours_this_month,
            'Date': formatted_date,
            'Listening': scores.listening,
            'Reading': scores.reading,
            'Maintenance Record': record,
        }
        pdf = create_pdf(data_fields)
        cols[1].download_button(label='Create 623A', data=pdf, file_name=f'623A_{formatted_date.upper()}_{name[2].upper()}.pdf')

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
        display_language_hours()
        with st.expander('Language Hour History', expanded=True):
            display_language_hour_history()
            display_language_hour_entities()

def admin(db):
    columns = st.columns([1, 3, 1])
    if not st.session_state.authenticated or not st.session_state.current_user:
        with columns[1]:
            st.warning('You must log in to access this site.')
            return
    if not st.session_state.current_user.is_admin:
        with columns[1]:
            st.warning('You are not authorized to access this tab.')
            return
    with columns[1]:
        upload_language_hours(db)

        with st.expander('Groups'):
            add_group(db)
            display_entities(db, Group)

        with st.expander('Users'):
            add_user(db)
            display_entities(db, User)

        with st.expander('Score'):
            add_score(db)
            display_entities(db, Score)

        with st.expander('Course'):
            add_course(db)
            display_entities(db, Course)

        with st.expander('Files'):
            add_file(db)
            display_entities(db, File)
            download_file(db)

        with st.expander('LanguageHours'):
            display_entities(db, LanguageHour)

        with st.expander('Messages'):
            display_entities(db, Message)

        with st.expander('Logs'):
            display_entities(db, Log)

        with st.expander('Database Management'):
            delete_row(db)
            delete_entities(db)

            st.write('Database changes:')
            cols = st.columns([1, 1, 1])    
            if cols[0].button("Save changes"):
                commit_or_rollback(db, commit=True)

            if cols[1].button("Discard changes"):
                commit_or_rollback(db, commit=False)

def sidebar(db):
    if not st.session_state.logged_in:
        st.sidebar.warning('You must log in to access this feature.')
        return
    with st.sidebar:
        st.subheader('Message Center')
        # Display message center
        with st.expander('Compose Message 📝'):
            try:
                compose_message(db, st.session_state.current_user.id)
                add_log(db, st.session_state.current_user.id, 'sent a message')
            except:
                return

        with st.expander('My Messages 📬', expanded=True):
            if st.session_state.current_user_data.Message:
                for message in st.session_state.current_user_data.Message:
                    sender = get_user(db, message.sender_id)
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
        with st.expander('Session State'):
            if st.session_state.current_user:
                if st.session_state.current_user.is_admin:
                    st.write('(Admin)')
                    st.write(st.session_state)

def navbar(db):
    nav_bar = option_menu(
        'Language Training Management',
        ['Login','Home', 'Submit Hour', 'Admin', 'TESTZONE'],
        icons=['key', 'house', 'send', 'tools', 'activity'],
        default_index=0,
        orientation='horizontal',
        menu_icon='diamond',
    )

    if nav_bar == 'Login':
        login(db)
    elif nav_bar == 'Home':
        home(db)
    elif nav_bar == 'Admin':
        admin(db)
    elif nav_bar == 'TESTZONE':
        test_zone(db)
    elif nav_bar == 'Submit Hour':
        submit_hour(db)
    else:
        home(db)

    #match nav_bar:
    #    case 'Login':
    #        login(db)
    #    case 'Home':
    #        home(db)
    #    case 'Admin':
    #        admin(db)
    #    case 'Submit Hour':
    #        submit_hour(db)
    #    case default:
    #        pass

def submit_hour(db):
    columns = st.columns([1, 3, 1])
    if not st.session_state.authenticated:
        with columns[1]:
            st.warning('You must log in to access this site.')
            return
    if st.session_state.current_user:
        with columns[1]:
            
            # get data from session state
            month = date.today().month
            year = date.today().year

            history_this_month = filter_monthly_hours(st.session_state.current_user_data.LanguageHour, month, year)
            hours_this_month = calculate_total_hours(history_this_month)
            hours_required = calculate_required_hours(st.session_state.current_user_data.Score[0])

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

def login(db):
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
                    if username and password:
                        hashed_password = hash_password(password)
                        user = get_user(db, username)
                        user = db.query(User).filter_by(username=username).first()
                        user_dict = dot_dict(user.to_dict())
                        if authenticate_user(user_dict, username, password, hashed_password):
                            with st.spinner('Loading...'):
                                user_data = load_user_models(db, st.session_state.current_user.id)
                                st.session_state.current_user_data = user_data
                            container.empty()
                            st.success('Logged in!')
                            add_log(db, st.session_state.current_user.id, f'{username} logged in.')
                    else:
                        st.warning('Please enter username and password.')
                        return

