import streamlit as st
from streamlit_option_menu import option_menu
from utils import initialize_session_state_variables, set_need_appearances_writer
from auth import authenticate_user, hash_password
from comps import download_to_excel, upload_pdf, delete_row, create_entity_form, display_entities, delete_entities, reset_entity_id, upload_language_hours
from models import User, Group, LanguageHour, Score, File
from config import SESSION_VARIABLES
from utils import dot_dict
from db import create_db, get_user, commit_or_rollback


st.set_page_config(page_title="Language Training Management", page_icon="🌐", layout="wide")
initialize_session_state_variables(SESSION_VARIABLES)


if __name__ == '__main__':
    db = create_db()


    class UI:
        def __init__(self):
            self.navbar = self.build_navbar()
            self.columns = st.columns([1, 3, 1])
            self.navbar_menu()

        def build_navbar(self):
            return option_menu(
                'Language Training Management',
                ['Login','Home', 'Submit Hour', 'Admin'],
                icons=['key', 'house', 'send', 'tools'],
                default_index=0,
                orientation='horizontal',
                menu_icon='diamond',
            )

        def navbar_menu(self):
            with st.sidebar:
                with st.expander('Session State', expanded=True):
                    if st.session_state.current_user:
                        if st.session_state.current_user.is_admin:
                            st.write('Admin')
                            st.write(st.session_state)
                        else:
                            st.write(st.session_state)

            if self.navbar == 'Home':
                self.home()
            elif self.navbar == 'Submit Hour':
                self.submit_hour()
            elif self.navbar == 'Login':
                self.login()
            elif self.navbar == 'Admin':
                self.admin()
            else:
                self.home()

            #match self.navbar:
            #    case 'Home':
            #        self.home()
            #    case 'Submit Hour':
            #        self.submit_hour()
            #    case 'Login':
            #        self.login()
            #    case 'Admin':
            #        self.admin()
            #    case default:
            #        pass

        def submit_hour(self):
            if not st.session_state.authenticated:
                with self.columns[1]:
                    st.warning('You must log in to access this site.')
                    return
            with self.columns[1]:
                create_entity_form(db, LanguageHour, exclude=['id', 'user_id'])
                with st.expander('History'):
                    file = download_to_excel(db, LanguageHour, st.session_state.current_user.id)
                    st.download_button(label='Download Excel', data=file, file_name='language_hours.xlsx')
                    display_entities(db, LanguageHour, exclude=['id', 'user_id'])

        def admin(self):
            if not st.session_state.authenticated or not st.session_state.current_user:
                with self.columns[1]:
                    st.warning('You must log in to access this site.')
                    return
            if not st.session_state.current_user.is_admin:
                with self.columns[1]:
                    st.warning('You are not authorized to access this tab.')
                    return
            with self.columns[1]:
                upload_language_hours(db)

                with st.expander('Groups'):
                    create_entity_form(db, Group)
                    display_entities(db, Group)

                with st.expander('Users'):
                    create_entity_form(db, User)
                    display_entities(db, User)

                with st.expander('Files'):
                    display_entities(db, File)
                    upload_pdf(db, st.session_state.current_user.id)

                with st.expander('Delete'):
                    delete_row(db)

                with st.expander('Database Management'):
                    if st.button("Save changes"):
                        commit_or_rollback(commit=True)

                    if st.button("Discard changes"):
                        commit_or_rollback(commit=False)

        def home(self):
            if not st.session_state.authenticated:
                with self.columns[1]:
                    st.warning('You must log in to access this site.')
                    return
            with self.columns[1]:
                    upload_pdf(db, st.session_state.current_user.id)

        def login(self):
            # display MyAccount view
            if st.session_state.authenticated:
                with self.columns[1]:
                    container = st.empty()
                    with container:


                        if st.button('Logout'):
                            st.session_state.authenticated = False
                            st.session_state.current_user = None
                            container.empty()
                            self.login()

            # display Login view
            if not st.session_state.authenticated:
                with self.columns[1]:
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
                                    self.submit_hour()
                            else:
                                st.warning('Please enter username and password.')
                                return

    ui = UI()

    ## member function
    #create_entity_form(db, LanguageHour)
    #display_entities(db, LanguageHour)
#
    #create_entity_form(db, Score)
    #display_entities(db, Score)
#
#
    ## admin functions
    #create_entity_form(db, Group)
    #display_entities(db, Group)
#
    #create_entity_form(db, User, exclude=['id', 'group_id'])
    #display_entities(db, User)
#
#
    ## developer functions
    #delete_row(db)

    #if st.session_state.authenticated:
    #    with st.spinner('loading application...'):
    #        if not st.session_state.loaded:
    #            loader = Loader(
    #                st.session_state.service,
    #                st.session_state.current_user,
    #                st.session_state.current_user['Group']
    #            )
    #            try:
    #                loader.load_data()
    #                st.session_state.loaded = True
    #            except:
    #                st.error('error')
    #    try:
    #        #pages.banner()
    #        pages.sidebar()
    #        pages.main_page()
    #    except Exception as e:
    #        pass
#
    #    if contains(st.session_state.current_user['Flags'], 'admin'):
    #        try:
    #            pages.admin_sidebar()
    #            pages.admin_page()
    #        except Exception as e:
    #            st.error('error')
#
    #    if contains(st.session_state.current_user['Flags'], 'dev'):
    #        try:
    #            pages.dev_sidebar()
    #            pages.dev_page()
    #        except Exception as e:
    #            st.error('error')
    #else:
    #    auth.login()
