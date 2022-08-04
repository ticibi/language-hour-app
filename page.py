from operator import contains
import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
from urllib.error import HTTPError
import os
from utils import calculate_hours_done_this_month, to_date, calculate_hours_required, to_excel, check_due_dates
import config


class Page:
    def __init__(self, icon=None):
        self.icon = icon
        self.service = st.session_state.service
        self.user = st.session_state.current_user


class Pages(Page):
    def __init__(self, icon=None):
        super().__init__(icon)

    def welcome_message(self, location='main'):
        '''welcome message displayed at the top of the sidebar'''
        msg = ''
        if contains(self.user['Flags'], 'sg'): msg = '🦢 Silly Goose 🥜 Boi'
        elif contains(self.user['Flags'], 'mmm'): msg = '😋 Mmmmm~!!!'
        elif contains(self.user['Flags'], 'max'): msg = '🐶 Oom Max' 
        else: msg = self.user['Name']
        if location == 'sidebar':
            st.sidebar.subheader(f'Welcome {msg}!')
        elif location == 'main':
            st.subheader(f'Welcome {msg}!')

    def history_expander(self):
        '''expander for table displaying entry history'''
        if self.user['Entries'].size < 1:
            return
        with st.expander('Show My Language Hour History'):
            try:
                self.service.update_entries(self.user['Name'], worksheet_id=st.session_state.config['HourTracker'])
                st.dataframe(self.user['Entries'].iloc[::-1])
            except Exception as e:
                print('[error]', e)

    def mytroops_expander(self):
        '''expander for table display sub data'''
        if not self.user['Subs']:
            return
        
        st.subheader('My Troops')
        for sub in self.user['Subs'].keys():
            with st.expander(sub):
                hrs_done = calculate_hours_done_this_month(self.service, name=sub)
                hrs_req = calculate_hours_required(self.user['Subs'][sub]['Scores'])
                color = 'green' if hrs_done >= hrs_req else 'red'
                st.markdown(f'<p style="color:{color}">{hrs_done}/{hrs_req} hrs</p>', unsafe_allow_html=True)
        
                '''DLPT and SLTE due date banner thing'''
                today = datetime.today().timestamp()
                due_dates = check_due_dates(self.user['Subs'][sub]['Scores'])
                one_month = 2628000.0
                one_week = 604800.0
                one_day = 86400.0

                def format_duedate(date: float) -> str:
                    if date == -1:
                        return 'N/A'
                    else:
                        return str(int((date-today)//one_day))

                # DLPT due date banner
                if today <= due_dates[0] - one_week * 2 and today >= due_dates[0] - one_month * 3:
                    dlpt_color = 'gold'
                elif today <= due_dates[0] and today > due_dates[0] - one_week * 2:
                    dlpt_color = 'red'
                else:
                   dlpt_color = 'green'

                # SLTE due date banner
                if today >= due_dates[1] - one_month and today <= due_dates[1] - one_month * 3:
                    slte_color = 'gold'
                elif today <= due_dates[1] and today > due_dates[1] - one_month:
                    slte_color = 'red'
                else:
                    slte_color = 'green'

                dlpt_duedate = to_date(due_dates[0])
                slte_duedate = to_date(due_dates[1])

                st.markdown(
                    f'<p style="color:{dlpt_color}">DLPT due {dlpt_duedate}, in {format_duedate(due_dates[0])} days</p>',
                    unsafe_allow_html=True
                )
                st.markdown(
                    f'<p style="color:{slte_color}">SLTE due {slte_duedate}, in {format_duedate(due_dates[1])} days</p>',
                    unsafe_allow_html=True
                )

                scores = self.user['Subs'][sub]['Scores']
                del scores['Name']
                st.dataframe(pd.DataFrame(scores, index=[0]))
                st.dataframe(self.user['Subs'][sub]['Entries'])

    def entry_form(self):
        '''hour entry form'''
        with st.form('Entry'):
            name = ''
            st.subheader('Language Hour Entry')
            cols = st.columns((2, 1))
            if contains(self.user['Flags'], 'admin'):
                options = list(st.session_state.members['Name'])
                index = options.index(self.user['Name'])
                name = cols[0].selectbox("Name", options=options, index=index)
            else:
                options = list(self.user['Subs'].keys())
                options.append(self.user['Name'])
                name = cols[0].selectbox("Name", options=options, index=len(options)-1)
            date = cols[1].date_input("Date")
            cols = st.columns((2, 1))
            mods = cols[0].multiselect("Activity", options=config.ACTIVITIES)
            hours_done = calculate_hours_done_this_month(self.service, name=self.user['Name'])
            hours_req = calculate_hours_required(self.user['Scores'])
            hours = cols[1].text_input(f"Hours - {hours_done}/{hours_req} hrs completed")
            cols = st.columns((2, 1))
            desc = cols[0].text_area("Description", height=150, placeholder='Be detailed!')
            vocab = cols[1].text_area("Vocab", height=150, placeholder='List vocab you learned/reviewed')
            cols = st.columns(2)
            if cols[0].form_submit_button("Submit"):
                if contains(hours, 'test'):
                    hours = 0
                elif not hours.isdigit():
                    st.warning('You need study for more than 0 hours...')
                    return
                if not desc:
                    st.warning('You need to describe what you studied...')
                    return
                try:
                    self.service.sheets.write_data(
                        worksheet_id=st.session_state.config['HourTracker'],
                        tab_name=name,
                        data=[[
                            str(date),
                            float(hours),
                            ' '.join(mods),
                            desc,
                            ' '.join(vocab.split() if vocab else '')
                            ]]
                        )
                    st.success('Entry submitted!')
                    st.balloons()
                    st.session_state.entries = self.service.sheets.get_data(
                        columns=None,
                        worksheet_id=st.session_state.config['HourTracker'],
                        tab_name=self.user['Name']
                    )
                    self.service.log(f'Submit {hours} hrs', worksheet_id=st.session_state.config['HourTracker'])
                except Exception as e:
                    st.error('Could not submit entry :(')
                    raise e

    def banner(self):
        '''notification banner displayed at the top of the page'''
        today = datetime.today().timestamp()
        due_dates = check_due_dates(self.user['Scores'])
        one_month = 2628000.0
        one_week = 604800.0
        one_day = 86400.0

        def format_duedate(date: float) -> int:
            return int((date-today)//one_day)

        # DLPT due date banner
        if today <= due_dates[0] - one_week * 2 and today >= due_dates[0] - one_month * 3:
            st.sidebar.warning(f'Your DLPT is due in {format_duedate(due_dates[0])} days')
        elif today <= due_dates[0] and today > due_dates[0] - one_week * 2:
            st.sidebar.error(f'GOOD-BYE FLPB :( Your DLPT is due in {format_duedate(due_dates[0])} days')
        else:
            st.sidebar.info(f'Your DLPT is due in {format_duedate(due_dates[0])} days')

        # SLTE due date banner
        if today >= due_dates[1] - one_month and today <= due_dates[1] - one_month * 3:
            st.sidebar.warning(f'You are due for a SLTE in {format_duedate(due_dates[1])} days')
        elif today <= due_dates[1] and today > due_dates[1] - one_month:
            st.sidebar.error(f'GOOD-BYE FLPB :(. Your SLTE is due in {format_duedate(due_dates[1])} days')
        else:
            st.sidebar.info(f'You are due for a SLTE in {format_duedate(due_dates[1])} days')

    def scores(self):
        cols = st.columns((1, 1))
        listening = cols[0].text_input(f'{self.user["Scores"]["CLang"]} Listening', value=self.user['Scores'][config.CLANG_L])
        reading = cols[1].text_input(f'{self.user["Scores"]["CLang"]} Reading', value=self.user['Scores'][config.CLANG_R])
        save = st.button('Update my scores')
        if save:
            self.user['Scores'][config.CLANG_L] = listening
            self.user['Scores'][config.CLANG_R] = reading

    def account(self):
        st.text_input('Name', value=self.user['Name'], disabled=True)
        username = st.text_input('Username', value=self.user['Username'])
        password = st.text_input('Password', placeholder='Enter a new password')
        save = st.button('Update my login info')
        if save:
            self.user['Username'] = username

    def subs(self):
        with st.expander('My Troops', expanded=True):
            if self.user['Subs'] is None:
                return
            for sub in self.user['Subs'].keys():
                cols = st.columns((5, 2))
                cols[0].markdown(sub)
                hrs_done = calculate_hours_done_this_month(self.service, name=sub)
                hrs_req = calculate_hours_required(self.user['Subs'][sub]['Scores'])
                color = 'green' if hrs_done >= hrs_req else 'red'
                cols[1].markdown(f'<p style="color:{color}">{hrs_done}/{hrs_req} hrs</p>', unsafe_allow_html=True)

    def upload_file(self):
        file = st.file_uploader('Upload 623A or ILTP', type=['pdf', 'txt', 'docx'])
        if file:
            with st.spinner('Uploading...'):
                try:
                    self.service.drive.upload_file(file, folder_name=self.user['Name'])
                    st.sidebar.success('File uploaded')
                    self.service.log(f'Uploaded {file.type} file named "{file.name}"')
                except Exception as e:
                    st.sidebar.error('Could not upload file :(')
                    raise e
            os.remove(f"temp/{file.name}")

    def download_file(self):
            if self.user['Entries'].size > 0:
                st.download_button('📥 Download Entry History (excel)', data=to_excel(self.user['Entries']), file_name='EntryHistory.xlsx')
                st.write('Stored Files:')
                files = self.user['Files']
            if not files:
                st.write('No files')
                return
            for file in files:
                try:
                    if st.download_button(file['name'], data=self.service.drive.download_file(file['id']), file_name=file['name']):
                        self.user['Files'] = self.service.drive.get_files(self.user['Name'])
                except Exception as e:
                    print(e)
     
    def program_info(self):
        with st.expander('[beta] Program Info'):
            st.markdown('''
                *program info goes here
            ''')

    def settings(self):
        def _check_reminder():
            return True if st.session_state.current_user['Reminder'] else False

        def _check_report():
            return True if st.session_state.current_user['Report'] else False

        def _get_email():
            return st.session_state.current_user['Email'] if st.session_state.current_user['Email'] else ''

        with st.expander('[this doesnt work] Preferences'):
            st.session_state.current_user['Reminder'] = 'x' if st.checkbox('Receive e-mail reminders', value=_check_reminder()) else ''
            st.session_state.current_user['Report'] = 'x' if st.checkbox('Receive monthly reports', value=_check_report()) else ''
            st.text_input(
                'Enter email',
                value=_get_email(),
                placeholder='Enter email',
                type='password',
            )


class AdminPage(Page):
    def __init__(self, icon):
        super().__init__(icon)

    def rundown(self):
        with st.expander('Monthly Hours Rundown'):
            month = st.selectbox("Select Month", options=calendar.month_name)# [i + 1 for i in range(12)])
            if st.button(f'Show Hours Rundown'):
                    st.session_state.show_total_month_hours = not st.session_state.show_total_month_hours
            if st.session_state.show_total_month_hours:
                st.session_state.selected_month = month
                with st.spinner('Calculating who done messed up...'):
                    data = []
                    if st.session_state.rundown_data is None:
                        for name in st.session_state.members['Name']:
                            try:
                                user_data = st.session_state.score_tracker.loc[st.session_state.score_tracker['Name'] == name].to_dict('records')[0]
                                hrs_req = calculate_hours_required(user_data)
                            except Exception as e:
                                print(e)
                                hrs_req = 0
                            try:
                                month = list(calendar.month_name).index(st.session_state.selected_month)
                                hrs_done = calculate_hours_done_this_month(self.service, name=name, month=month)
                            except Exception as e:
                                print(e)
                                hrs_done = 0
                            check = {
                                True: '✅',
                                False: '❌',
                            }
                            COLS = ['Comments', 'Met', 'Name', 'Hours Done', 'Hours Required']
                            data.append(['', check[float(hrs_done) >= float(hrs_req)], name, hrs_done, hrs_req])
                        df = pd.DataFrame(data, columns=COLS)
                        st.session_state.rundown_data = df
                    else:
                        df = st.session_state.rundown_data
                    st.table(df)
                    st.session_state.total_month_all = data

    def add_member(self):
        with st.expander('Add Member'):
            with st.form('Add Member'):
                name = st.text_input(label="Name", placeholder="Last, First")
                username = st.text_input(label="Username", placeholder="jsmith")
                clang = st.selectbox(label="CLang", options=config.DICODES)
                iltp = st.selectbox(label="ILTP Status", options=['ILTP', 'RLTP', 'NONE'])
                slte = st.date_input(label="SLTE Date")
                dlpt = st.date_input(label="DLPT Date")
                clangl = st.text_input(label=config.CLANG_L)
                clangr = st.text_input(label=config.CLANG_R)
                dialects = st.text_input(label="Dialects", placeholder="Only score of 2 or higher")
                mentor = st.text_input(label="Mentor")
                supe = st.selectbox(label="Supervisor", options=[x for x in st.session_state.members['Name'].tolist()])
                flags = st.multiselect(label="Flags", options=['admin', 'dev'])
                submit = st.form_submit_button('Add Member')
                if submit:
                    user_data = {
                        'Name': name,
                        'Username': username,
                        'CLang': clang,
                        'ILTP': iltp,
                        'SLTE': str(slte),
                        'DLPT': str(dlpt),
                        config.CLANG_L: clangl,
                        config.CLANG_R: clangr,
                        'Dialects': dialects if dialects else '',
                        'Mentor': mentor if mentor else '',
                        'Supervisor': supe,
                        'Flags': ' '.join(flags) if flags else '',
                    }
                    try:
                        self.service.add_member(user_data)
                        self.service.log(f'Added member {username}')
                    except Exception as e:
                        print(e)
                        st.error('Failed to add member')

    def member_actions(self):
        with st.expander('Member Actions'):
            options = list(st.session_state.members['Name'])
            options.append('')
            member = st.selectbox('Select a Member', options=options, index=len(options)-1)
            if member:
                data = self.service.sheets.get_data(columns=None, tab_name=member, worksheet_id=st.session_state.config['HourTracker'])
                button = st.download_button(f'Download Entry History', data=to_excel(data))
                file_button = st.button('Download Files')
                if file_button:
                    pass
                remove_button = st.button('Remove Member')
                if remove_button:
                    confirm = st.button(f'Confirm Removal of "{member}"')
                    if confirm:
                        self.service.log(f'Removed member {member}', worksheet_id=st.session_state.config['HourTracker'])

    def admin_actions(self):
        with st.sidebar:
            with st.expander('Admin Actions', expanded=True):
                if st.button('Create Folders', help="Create folders for all members if it doesn't exist"):
                    try:
                        count = self.service.create_folders_bulk()
                        st.sidebar.success(f"Created {count} folders")
                        self.service.log(f'Created {count} folders', worksheet_id=st.session_state.config['HourTracker'])
                    except HTTPError as e:
                        print(e)
                if st.button('Create Tabs', help="Create tabs for all members if it doesn't exist"):
                    try:
                        count = self.service.create_tabs_bulk()
                        st.sidebar.success(f"Created {count} tabs")
                        self.service.log(f'Created {count} tabs', worksheet_id=st.session_state.config['HourTracker'])
                    except HTTPError as e:
                        print(e)

    def links(self):
        with st.sidebar:
            with st.expander('Tracker Links', expanded=True):
                st.write(f"[Master Tracker]({config.URL + config.MASTER_ID})")
                st.write(f"[Score Tracker]({config.URL+st.session_state.config['ScoreTracker']})")
                st.write(f"[Hour Tracker]({config.URL+st.session_state.config['HourTracker']})")
                st.write(f"[Google Drive]({config.DRIVE+st.session_state.config['GoogleDrive']})")


class DevPage(Page):
    def __init__(self, icon):
        super().__init__(icon)

    def dev_page(self):
        st.subheader('Dev Tools')
        with st.expander('Session State'):
            st.write(st.session_state)

    def dev_sidebar(self):
        def toggle_debug():
            st.session_state.debug = not st.session_state.debug

        with st.sidebar:
            with st.expander('+', expanded=True):
                st.write(f'Request Count: {st.session_state.req_count}')
                st.checkbox('Show Debug', value=st.session_state.debug, on_change=toggle_debug())

