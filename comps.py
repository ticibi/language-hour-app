import streamlit as st
import pandas as pd
from db import reset_autoincrement, delete_row_by_id
from models import MODELS, TABLE, File, LanguageHour
from utils import to_excel

def download_file(db):
    cols = st.columns([1, 2])
    file_id = cols[1].number_input('File ID', step=1)
    if cols[0].button('Download File by ID'):
        if file_id:
            pass

def delete_row(db):
    st.write('Delete Row By ID')
    cols = st.columns([1, 1])
    id = cols[0].number_input('ID', step=1)
    cls = cols[1].selectbox('Table', options=MODELS)
    if st.button('Delete Row'):
        delete_row_by_id(db, TABLE[cls], int(id))

def delete_entities(db, cls):
    if st.button(f'Delete {cls.__tablename__}'):
        db.query(cls).delete()
        db.commit()
        db.close()

def display_entities(db, cls, user_id=None, exclude=[]):
    if user_id:
        entities = db.query(cls).filter(cls.user_id == user_id).all()
    else:
        entities = db.query(cls).all()
    if not entities:
        st.write(f"No {cls.__name__} entities found.")
        return
    data = [entity.to_dataframe() for entity in entities]
    df = pd.concat(data)
    if exclude:
        df = df.drop(columns=exclude)
    st.dataframe(df, use_container_width=True)

def create_entity_form(db, cls, exclude=['id']):
    with st.form(f'create_{cls.__name__}_form'):
        st.write(f'Add {cls.__name__}')
        for column in cls.__table__.columns:
            if column.name not in exclude:
                value = st.text_input(column.name)
                setattr(cls, column.name, value)
        if st.form_submit_button('Submit'):
            instance = cls()
            for column in cls.__table__.columns:
                if column.name not in exclude:
                    setattr(instance, column.name, getattr(cls, column.name))
            db.add(instance)
            db.commit()
            db.close()
            st.success(f'Added {cls.__name__}!')

def reset_entity_id(db, cls):
    if st.button(f'Reset {cls.__tablename__}'):
        reset_autoincrement(cls.__tablename__)

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

def upload_excel(db, user_id):
    with st.expander('Language Hour Upload', expanded=True):
        file = st.file_uploader('Upload an excel file here to populate history', type=['xlsx'])
        if file:
            language_hours = read_excel(file, user_id)
            for x in language_hours:
                db.add(x)
            db.commit()
            db.close()
            st.success('added hours!')

def upload_language_hours(db, user_id):
    upload_excel(db, user_id)

def upload_pdf(db, user_id: int):
    file = st.file_uploader('Upload PDF file', type='pdf')
    if file:
        contents = file.read()
        try:
            new_file = File(name=file.name, file=contents, user_id=user_id)
            db.add(new_file)
            db.commit()
            db.close()
            st.success('File uploaded successfully!')
        except:
            st.warning('Failed to upload file.')

def download_to_excel(db, cls, user_id: int):
    language_hours = db.query(cls).filter(cls.user_id == user_id).all()
    if not language_hours:
        return
    df = pd.concat([lh.to_dataframe() for lh in language_hours], ignore_index=True)
    return to_excel(df)

def render_html(file: str):
    with open(f'components/{file}.html', 'r') as f:
        html = f.read()
        st.markdown(html, unsafe_allow_html=True)
