import streamlit as st
import config


class Form:
    def __init__(self, name, username, clang, iltp, slte, dlpt, clangl, clangr, dialects, mentor, supe, flags):
        self.name = name
        self.username = username
        self.clang = clang
        self.iltp = iltp
        self.slte = slte
        self.dlpt = dlpt
        self.clangl = clangl
        self.clangr = clangr
        self.dialects = dialects
        self.mentor = mentor
        self.supe = supe
        self.flags = flags
        self.data = {
            'Name': self.name,
            'Username': self.username,
            'CLang': self.clang,
            'ILTP': self.iltp,
            'SLTE': self.slte,
            'DLPT': self.dlpt,
            config.CLANG_L: self.clangl,
            config.CLANG_R: self.clangr,
            'Dialects': self.dialects,
            'Mentor': self.mentor,
            'Supervisor': self.supe,
            'Flags': self.flags,
        }

    def submit(self, service):
        try:
            service.add_member(
                self.data,
                st.session_state.config['HourTracker'],
                st.session_state.config['ScoreTracker'],
            )
            self.service.log(f'Added member {self.username}')
        except Exception as e:
            print(e)
            st.error('Failed to add member.')


    
