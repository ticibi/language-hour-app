import streamlit as st
import pandas as pd
from excel_utils import upload_excel
from db import reset_autoincrement, delete_row_by_id
from models import Group, File, LanguageHour
import models
from config import MODALITIES
from utils import to_excel


def render_html(file: str):
    with open(f'components/{file}.html', 'r') as f:
        html = f.read()
        st.markdown(html, unsafe_allow_html=True)

def delete_row(db):
    st.write('Delete Row By ID')
    cols = st.columns([1, 1])
    id = cols[0].number_input('Row ID', step=1)
    cls = cols[1].selectbox('Table', options=models.__models__)
    if st.button('Delete'):
        delete_row_by_id(db, models.hash_table[cls], int(id))

def delete_entities(db, cls):
    if st.button(f'Delete {cls.__tablename__}'):
        db.query(cls).delete()
        db.commit()

def display_entities(db, cls, exclude=[]):
    entities = db.query(cls).all()
    if not entities:
        st.write(f"No {cls.__name__} entities found.")
        return
    data = [entity.to_dataframe() for entity in entities]
    df = pd.concat(data)
    if exclude:
        df = df.drop(columns=exclude)
    st.write(df)

def create_entity_form(db, cls, exclude=['id']):
    with st.form(f'create_{cls.__name__}_form'):
        st.write(f'Add {cls.__name__}')
        for column in cls.__table__.columns:
            if column.name not in exclude:
                if column.name.lower() == 'date':
                    value = st.date_input(column.name)
                elif column.name.lower() == 'is_admin':
                    value = st.checkbox(column.name)
                elif column.name.lower() == 'modalities':
                    value = st.multiselect(column.name, options=MODALITIES)
                elif column.name.lower() == 'hours':
                    value = st.number_input(column.name, step=1)
                elif column.name.lower() == 'group_id':
                    value = int(st.number_input('group', min_value=15, step=1))
                else:
                    value = st.text_input(column.name)
                setattr(cls, column.name, value)
        if st.form_submit_button('Submit'):
            instance = cls()
            for column in cls.__table__.columns:
                if column.name not in exclude:
                    setattr(instance, column.name, getattr(cls, column.name))
            db.add(instance)
            db.commit()
            st.success(f'Added {cls.__name__}!')

def reset_entity_id(db, cls):
    if st.button(f'Reset {cls.__tablename__}'):
        reset_autoincrement(cls.__tablename__)

def upload_language_hours(db):
    upload_excel(db, 2)

def upload_pdf(db, user_id: int):
    file = st.file_uploader('Upload PDF file', type='pdf')
    if file:
        contents = file.read()
        try:
            new_file = File(name=file.name, file=contents, user_id=user_id)
            db.add(new_file)
            db.commit()
            st.success('File uploaded successfully!')
        except:
            st.warning('Failed to upload file.')

def download_to_excel(db, cls, user_id: int):
    language_hours = db.query(cls).filter(cls.user_id == user_id).all()
    df = pd.concat([lh.to_dataframe() for lh in language_hours], ignore_index=True)
    return to_excel(df)
