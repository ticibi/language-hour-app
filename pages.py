from operator import contains
import streamlit as st
import pandas as pd
import calendar
from urllib.error import HTTPError
import os
from utils import calculate_hours_done_this_month, calculate_hours_required, get_user_info_index, to_excel
import config


class Pages():
    def __init__(self, service):
        self.service = service
        self.user = st.session_state.current_user

    def welcome_message(self):
        return '🦢 Silly Goose' if contains(st.session_state.current_user['Flags'], 'sg') else st.session_state.current_user['Name']
        return '👨‍🍳 Mmmmmm!!!' if contains(st.session_state.current_user['Flags'], 'mmm') else st.session_state.current_user['Name']
        return '🐶 ام ماكس' if contains(st.session_state.current_user['Flags'], 'max') else st.session_state.current_user['Name']

    def history_expander(self):
        if self.user['Entries'].size < 1:
            return
        with st.expander('Show my Language Hour history'):
            try:
                self.service.update_entries(self.user['Name'], worksheet_id=st.session_state.config['HourTracker'])
                st.table(self.user['Entries'])
            except Exception as e:
                print('[error]', e)

    def mytroops_expander(self):
        if not self.user['Subs']:
            return
        st.subheader('My Troops')
        for sub in self.user['Subs'].keys():
            with st.expander(sub):
                hrs_done = calculate_hours_done_this_month(self.service, name=sub)
                hrs_req = calculate_hours_required(self.user['Subs'][sub]['Scores'])
                color = 'green' if hrs_done >= hrs_req else 'red'
                st.markdown(f'<p style="color:{color}">{hrs_done}/{hrs_req} hrs</p>', unsafe_allow_html=True)
                scores = self.user['Subs'][sub]['Scores']
                del scores['Name']
                st.dataframe(pd.DataFrame(scores, index=[0]))
                st.dataframe(self.user['Subs'][sub]['Entries'])

    def entry_form(self):
        with st.form('Entry'):
            name = ''
            st.subheader('Language Hour Entry')
            cols = st.columns((2, 1))
            if contains(st.session_state.current_user['Flags'], 'admin'):
                options = list(st.session_state.members['Name'])
                index = options.index(self.user['Name'])
                name = cols[0].selectbox("Name", options=options, index=index)
            else:
                options = list(self.user['Subs'].keys())
                options.append(self.user['Name'])
                name = cols[0].selectbox("Name", options=options, index=len(options)-1)
            date = cols[1].date_input("Date")
            cols = st.columns((2, 1))
            mods = cols[0].multiselect("Activity", options=['Listening', 'Reading', 'Speaking', 'Transcription', 'Vocab', 'SLTE', 'DLPT', 'ILTP upload', '623A upload'])
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
                    st.warning('🕓 You need to study for more than 0 hours...')
                    return
                if not desc:
                    st.warning('❗ You need to describe what you studied...')
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
                    st.success('Entry submitted! 🎉')
                    st.balloons()
                    st.session_state.entries = self.service.sheets.get_data(columns=None, worksheet_id=st.session_state.config['HourTracker'], tab_name=self.user['Name'])
                    self.service.log(f'submit {hours} hrs', worksheet_id=st.session_state.config['HourTracker'])
                except Exception as e:
                    st.error('could not submit entry :(')
                    raise e

    def main_page(self):
        self.entry_form()
        self.history_expander()
        self.mytroops_expander()

    def sidebar(self):
        def update_score():
            self.service.log(f'updated scores', worksheet_id=st.session_state.config['HourTracker'])

        def account():
            def scores():
                cols = st.columns((1, 1, 1))
                listening = cols[0].text_input('CLang: Listening', value=self.user['Scores']['CL - Listening'])
                listening2 = cols[1].text_input('MSA: Listening', value=self.user['Scores']['MSA - Listening'])
                reading = cols[2].text_input('MSA: Reading', value=self.user['Scores']['MSA - Reading'])
                save = st.button('Save my scores')
                if save:
                    self.user['Scores']['CL - Listening'] = listening
                    self.user['Scores']['MSA - Listening'] = listening2
                    self.user['Scores']['MSA - Reading'] = reading

            def login_info():
                st.text_input('Name', value=self.user['Name'], disabled=True)
                username = st.text_input('Username', value=self.user['Username'])
                password = st.text_input('Password', placeholder='Enter a new password')
                save = st.button('Save my login info')
                if save:
                    self.user['Username'] = username

            ''' 
            for resetting passwords...
            
            import streamlit_authenticator as stauth
            
            def pw_reset():
                # if user clicks on the change/reset pw button or something
                    try:
                        if authenticator.reset_password(username, 'Reset password'):
                            st.success('Password updated')
                    except Exception as e:
                        st.error(e)
            '''
            
            with st.expander('[this doesnt work] My Account'):      " <--- what is this for? "
                st.write('Login Info')
                login_info()
                st.write('My Scores')
                scores()

        def subs():
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

        def files():
            def upload():
                file = st.file_uploader('Upload 623A or ILTP', type=['pdf', 'txt', 'docx'])
                if file:
                    with st.spinner('Uploading...'):
                        try:
                            self.service.drive.upload_file(file, folder_name=self.user['Name'])
                            st.sidebar.success('File uploaded')
                            self.service.log(f'uploaded {file.type} file named "{file.name}"')
                        except Exception as e:
                            st.sidebar.error('Could not upload file :(')
                            raise e
                    os.remove(f"temp/{file.name}")

            def download():
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

            with st.expander('My Files'):
                upload()
                download()
     
        def program_info():
            with st.expander('[beta] Program Info'):
                st.markdown('''
                    *program info goes here
                ''')

        def settings():
            def _check_reminder():
                if not st.session_state.current_user['Reminder']:
                    return False
                return True if st.session_state.current_user['Reminder'] else False

            def _check_report():
                if not st.session_state.current_user['Report']:
                    return False
                return True if st.session_state.current_user['Report'] else False

            with st.expander('[this doesnt work] Preferences'):
                st.session_state.current_user['Reminder'] = 'x' if st.checkbox('Receive e-mail reminders', value=_check_reminder()) else ''
                st.session_state.current_user['Report'] = 'x' if st.checkbox('Receive monthly reports', value=_check_report()) else ''
                st.text_input(
                    'Enter email',
                    value=st.session_state.current_user['Email'] if st.session_state.current_user['Email'] else '',
                    placeholder='Enter email',
                    type='password',
                )

        with st.sidebar:
            st.subheader(f'Welcome {self.welcome_message()}!')
            subs()
            if 'admin' in st.session_state.current_user['Flags']: account()
            files()
            if 'admin' in st.session_state.current_user['Flags']: settings() 
            if 'admin' in st.session_state.current_user['Flags']: program_info()

    def admin_page(self):
        if st.session_state.show_total_month_hours:
            with st.expander(f'Monthly Hours Rundown - {st.session_state.selected_month}', expanded=True):
                with st.spinner('Calculating who done messed up...'):
                    data = []
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
                        data.append(['', check[float(hrs_done) >= float(hrs_req)], name, hrs_done, hrs_req])
                    df = pd.DataFrame(data, columns=['Comments', 'Met', 'Name', 'Hours Done', 'Hours Required'])
                    st.table(df)
                    st.session_state.total_month_all = data

    def admin_sidebar(self):
        def add_member():
            with st.expander('Add Member'):
                with st.form('Add Member'):
                    data = st.session_state.score_tracker
                    name = st.text_input(label="Name", placeholder="Last, First")
                    username = st.text_input(label="Username", placeholder="jsmith")
                    clang = st.selectbox(label="CLang", options=["AP", "AD", "DG", "PV", "PF", "PG", "AV", "AN",])
                    iltp = st.selectbox(label="ILTP Status", options=['ILTP', 'RLTP', 'NONE'])
                    slte = st.date_input(label="SLTE Date")
                    dlpt = st.date_input(label="DLPT Date")
                    cll = st.text_input(label="CL - Listening")
                    msal = st.text_input(label="MSA - Listening")
                    msar = st.text_input(label="MSA - Reading")
                    dialects = st.text_input(label="Dialects", placeholder="Only scores 2 or higher")
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
                            'CL - Listening': cll,
                            'MSA - Listening': msal,
                            'MSA - Reading': msar,
                            'Dialects': dialects if dialects else '',
                            'Mentor': mentor if mentor else '',
                            'Supervisor': supe,
                            'Flags': ' '.join(flags) if flags else '',
                        }
                        try:
                            self.service.add_member(user_data)
                            self.service.log(f'Ddded member {username}')
                        except Exception as e:
                            print(e)
                            st.error('Failed to add member')

        def member_actions():
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

        def admin_actions():
                with st.expander('Admin Actions'):
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

        def rundown():
            with st.expander('Monthly Rundown'):
                month = st.selectbox("Select Month", options=calendar.month_name)# [i + 1 for i in range(12)])
                st.session_state.selected_month = month
                if st.button(f'Show {month} Hours Rundown'):
                    st.session_state.show_total_month_hours = not st.session_state.show_total_month_hours
                #if st.button('Show upcoming DLPTs'):
                #    pass
                #if st.button('Show upcoming SLTEs'):
                #    pass

        with st.sidebar:
            st.sidebar.subheader('Admin')
            add_member()
            member_actions()
            admin_actions()
            rundown()

            with st.expander('Tracker Links'):
                st.write(f"[Master Tracker]({config.URL + config.MASTER_ID})")
                st.write(f"[Score Tracker]({config.URL+st.session_state.config['ScoreTracker']})")
                st.write(f"[Hour Tracker]({config.URL+st.session_state.config['HourTracker']})")
                st.write(f"[Google Drive]({config.DRIVE+st.session_state.config['GoogleDrive']})")

    def dev_page(self):
        st.subheader('Dev Tools')
        with st.expander('[Developer Debug]'):
            st.write(st.session_state)

    def dev_sidebar(self):
        def toggle_debug():
            st.session_state.debug = not st.session_state.debug

        st.sidebar.subheader('[Developer Debug]')
        with st.sidebar:
            with st.expander('+', expanded=True):
                st.write(f'Request Count: {st.session_state.req_count}')
                st.checkbox('Show Debug', value=st.session_state.debug, on_change=toggle_debug())
