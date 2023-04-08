import pandas as pd
from models import LanguageHour
import streamlit as st


def read_excel(file, user_id):
    '''convert lang hour excel sheet to a list'''
    df = pd.read_excel(file, engine='openpyxl')
    language_hours = []
    for _, row in df.iterrows():
        language_hour = LanguageHour(
            user_id=user_id,
            date=row['Date'],
            hours=row['Hours'],
            description=row['Description'],
            modalities=row['Modality'],
        )
        language_hours.append(language_hour)
    return language_hours

def upload_excel(session, user_id):
    with st.expander('Language Hour Upload', expanded=True):
        file = st.file_uploader('Upload an excel file here to populate history', type=['xlsx'])
        if file:
            language_hours = read_excel(file, user_id)
            for x in language_hours:
                session.add(x)
            session.commit()
            st.success('added hours!')

