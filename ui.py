from streamlit_option_menu import option_menu
import streamlit as st
from auth import authenticate_user, hash_password
from db import get_user, commit_or_rollback
from utils import calculate_required_hours, filter_monthly_hours, calculate_total_hours, dot_dict, get_user_monthly_hours, create_pdf, language_hour_history_to_string
from comps import submit_entry, download_file, download_to_excel, upload_pdf, delete_row, create_entity_form, display_entities, delete_entities, reset_entity_id, upload_language_hours
from models import LanguageHour, User, Group, File, Score, Course
from config import MODALITIES
from datetime import date
import calendar
from load import load_user_models

def home(db):
    scores = None
    hours = None
    history = None
    columns = st.columns([1, 3, 1])
    if not st.session_state.authenticated:
        with columns[1]:
            st.warning('You must log in to access this site.')
            return
    with columns[1]:
        #upload_pdf(db, st.session_state.current_user.id)
        upload_language_hours(db, st.session_state.current_user.id)
        # show language hour history table
        with st.expander('Language Hour History', expanded=True):
            cols = st.columns([1, 1, 2])
            file = download_to_excel(db, LanguageHour, st.session_state.current_user.id)
            cols[0].download_button(label='Download History (Excel)', data=file, file_name='language_hours.xlsx')

            # query database for data
            hours = get_user_monthly_hours(db, st.session_state.current_user.id)
            scores = st.session_state.current_user_data.Score[0]
            history = st.session_state.current_user_data.LanguageHour


            month = date.today().month
            year = date.today().year

            history_this_month = filter_monthly_hours(st.session_state.current_user_data.LanguageHour, month, year)
  
            # fill in the pdf
            if scores and hours and history_this_month:
                name = st.session_state.current_user.name.split(' ')
                record = language_hour_history_to_string(history_this_month)
                formatted_date = f'{calendar.month_abbr[date.today().month]}-{date.today().year}'
                data_fields = {
                    'Language': scores.langauge,
                    'Member Name': f'{name[2].upper()} {name[0].upper()} {name[1].upper()}',
                    'Hours Studied': hours,
                    'Date': formatted_date,
                    'Listening': scores.listening,
                    'Reading': scores.reading,
                    'Maintenance Record': record,
                }
                pdf = create_pdf(data_fields)
                cols[1].download_button(label='Create 623A', data=pdf, file_name=f'623A_{formatted_date.upper()}_{name[2].upper()}.pdf')
            display_entities(db, LanguageHour, user_id=st.session_state.current_user.id, exclude=['id', 'user_id'])

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
        user_id = st.number_input('User ID', value=st.session_state.current_user.id, step=1)
        upload_language_hours(db, user_id)

        with st.expander('Groups'):
            create_entity_form(db, Group)
            display_entities(db, Group)

        with st.expander('Users'):
            create_entity_form(db, User)
            display_entities(db, User)

        with st.expander('Score'):
            create_entity_form(db, Score)
            display_entities(db, Score)

        with st.expander('Course'):
            create_entity_form(db, Course)
            display_entities(db, Course)

        with st.expander('Files'):
            display_entities(db, File)
            upload_pdf(db, st.session_state.current_user.id)
            download_file(db)

        with st.expander('Database Management'):
            delete_row(db)

            st.write('Database changes:')
            cols = st.columns([1, 1, 1])    
            if cols[0].button("Save changes"):
                commit_or_rollback(db, commit=True)

            if cols[1].button("Discard changes"):
                commit_or_rollback(db, commit=False)

def sidebar(db):
    with st.sidebar:
        with st.expander('Session State', expanded=True):
            if st.session_state.current_user:
                if st.session_state.current_user.is_admin:
                    st.write('(Admin)')
                    st.write(st.session_state)
                else:
                    st.write('')
            else:
                st.sidebar.warning('You must log in to access this site.')

def navbar(db):
    nav_bar = option_menu(
        'Language Training Management',
        ['Login','Home', 'Submit Hour', 'Admin'],
        icons=['key', 'house', 'send', 'tools'],
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
                if st.form_submit_button('Submit'):
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
                    else:
                        st.warning('You must fill out every field.')

def login(db):
    columns = st.columns([1, 1, 1])
    # display Login view
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
                        if not st.session_state.current_user:
                            user = get_user(db, username)
                            user_dict = dot_dict(user.to_dict())
                            if authenticate_user(user_dict, username, password, hashed_password):
                                with st.spinner('Loading...'):
                                    user_data = load_user_models(db, st.session_state.current_user.id)
                                    st.session_state.current_user_data = user_data
                                container.empty()
                                st.success('Logged in!')
                    else:
                        st.warning('Please enter username and password.')
                        return


