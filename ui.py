from streamlit_option_menu import option_menu
import streamlit as st
from auth import authenticate_user, hash_password
from db import get_user, commit_or_rollback
from utils import dot_dict, get_user_monthly_hours, get_user_monthly_hours_required
from comps import download_file, download_to_excel, upload_pdf, delete_row, create_entity_form, display_entities, delete_entities, reset_entity_id, upload_language_hours
from models import LanguageHour, User, Group, File, Score, Course
from config import MODALITIES

global nav_bar

def home(db):
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
        upload_language_hours(db)

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
                    st.write(st.session_state)
            else:
                st.sidebar.warning('You must log in to access this site.')

def navbar(db):
    global nav_bar
    nav_bar = option_menu(
        'Language Training Management',
        ['Login','Home', 'Submit Hour', 'Admin'],
        icons=['key', 'house', 'send', 'tools'],
        default_index=0,
        orientation='horizontal',
        menu_icon='diamond',
    )
    match nav_bar:
        case 'Login':
            login(db)
        case 'Home':
            home(db)
        case 'Admin':
            admin(db)
        case 'Submit Hour':
            submit_hour(db)
        case default:
            pass

def submit_hour(db):
    columns = st.columns([1, 3, 1])
    if not st.session_state.authenticated:
        with columns[1]:
            st.warning('You must log in to access this site.')
            return
    if st.session_state.current_user:
        with columns[1]:
            # get user data
            total_hours = get_user_monthly_hours(db, st.session_state.current_user.id)
            req = get_user_monthly_hours_required(db, st.session_state.current_user.id)

            # create the submission form
            with st.form('submit_hours', clear_on_submit=True):
                cols = st.columns([1, 1])
                date = cols[0].date_input('Date')
                hours = cols[1].number_input(f'Hours ({total_hours}/{req} completed)', min_value=1, step=1)
                modalities = st.multiselect('Modalities', options=MODALITIES)
                description = st.text_area('Description')
                if st.form_submit_button('Submit'):
                    if description and modalities:
                        entry = LanguageHour(
                            date=date,
                            hours=int(hours),
                            description=description,
                            modalities=modalities,
                            user_id=st.session_state.current_user.id,
                        )
                        db.add(entry)
                        db.commit()
                        st.balloons()
                        st.success(f'{hours} language hours submitted!')
                    else:
                        st.warning('You must fill out every field.')

def login(db):
    columns = st.columns([1, 1, 1])
    ## display MyAccount view
    #if st.session_state.authenticated and st.session_state.logged_in:
    #    with columns[1]:
    #        container = st.empty()
    #        with container:
    #            if st.button('Logout'):
    #                #initialize_session_state_variables()
    #                container.empty()
    #                login(db)

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
                        user = get_user(db, username)
                        user_dict = dot_dict(user.to_dict())
                        if authenticate_user(user_dict, username, password, hashed_password):
                            container.empty()
                            st.success('Logged in!')
                    else:
                        st.warning('Please enter username and password.')
                        return


