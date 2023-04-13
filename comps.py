import streamlit as st
import pandas as pd
from db import reset_autoincrement, delete_row_by_id, session
from models import MODELS, TABLE, File, LanguageHour
from utils import dot_dict, to_excel, spacer
from sqlalchemy import text
from db import change_database_connection, get_database_name, get_databases
from config import DB1
from extensions import create_session


def connect_to_database(db):
    # Get all databases
    databases = [d.name for d in get_databases(db)]
    databases.insert(0, DB1)

    # Create the UI
    cols = st.columns([1, 1, 1])
    database = cols[0].selectbox('Select a database to connect to: ', options=databases)
    spacer(cols[1], 2)
    if cols[1].button('Connect', type='primary'):
        engine = change_database_connection(database)
        db = create_session(engine)
        cols[0].success(f'Connected to {get_database_name(engine)} successfully!')
    return db

def download_file(db):
    cols = st.columns([1, 2])
    file_id = cols[0].number_input('Download file by ID', step=1)
    spacer(cols[1], 2)
    if cols[1].button('Download'):
        if file_id:
            pass

def delete_row(db):
    st.write('Delete row in selected table by ID: ')
    cols = st.columns([1, 1, 1])
    id = cols[0].number_input('ID', step=1)
    class_name = cols[1].selectbox('Table', index=len(MODELS)-1, options=MODELS)
    cls = TABLE[class_name]
    count = db.query(cls).count()
    data = db.query(cls).filter_by(id=id).first()
    if not data:
        st.info('Data for this row and table does not exist.')
        return
    
    data_dict = dot_dict(data.to_dict())
    cols[0].write(f':red[Note: This action will remove:]')
    st.dataframe(data_dict, use_container_width=True)

    spacer(cols[2], len=2)
    if cols[2].button('Delete Row'):
        delete_row_by_id(db, cls, int(id))

def delete_entities(db):
    cols = st.columns([2, 1])
    class_name = cols[0].selectbox('Choose table to delete:', index=len(MODELS)-1, options=MODELS)
    cls = TABLE[class_name]
    count = db.query(cls).count()
    cols[0].write(f':red[Note: This action will remove {count} rows of data and is irreversable.]')
    
    spacer(cols[1], len=2)
    if cols[1].button(f'Delete ALL {cls.__tablename__}'):
        with session(db) as db:
            db.query(cls).delete()
            st.info(f'Deleted all {cls.__tablename__}.')

            # Reset auto-increment value to 1
            db.execute(text(f"ALTER TABLE {cls.__tablename__} AUTO_INCREMENT = 1"))

            # Inform the user that the table has been deleted
            st.info(f'Auto-increment for {cls.__tablename__} has been reset.')

def display_entities(db, cls, user_id=None, exclude=[]):
    if user_id:
        entities = db.query(cls).filter(cls.user_id == user_id).all()
    else:
        entities = db.query(cls).all()
    if not entities:
        st.info(f"No {cls.__name__} entities found.")
        return
    data = [entity.to_dataframe() for entity in entities]
    df = pd.concat(data)
    if exclude:
        df = df.drop(columns=exclude)
    df = df.set_index('id')
    st.dataframe(df, use_container_width=True)

def reset_entity_id(db, cls):
    if st.button(f'Reset {cls.__tablename__}'):
        reset_autoincrement(cls.__tablename__)

def submit_entry(db, entry):
    with session(db) as db:
        db.add(entry)

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
    with st.expander('Upload language hours', expanded=True):
        file = st.file_uploader(':green[Upload an excel file here to populate history]', type=['xlsx'])
        if file:
            language_hours = read_excel(file, user_id)
            with session(db) as db:
                for x in language_hours:
                    db.add(x)
            st.success('added hours!')

def upload_pdf(db, user_id: int):
    file = st.file_uploader('Upload PDF file', type='pdf')
    if file:
        contents = file.read()
        try:
            new_file = File(name=file.name, file=contents, user_id=user_id)
            with session(db) as db:
                db.add(new_file)
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

def create_entity_form(db, cls, exclude=['id']):
#    with st.form(f'create_{cls.__name__}_form'):
#        st.write(f'Add {cls.__name__}')
#        for column in cls.__table__.columns:
#            if column.name not in exclude:
#                value = st.text_input(column.name)
#                setattr(cls, column.name, value)
#        if st.form_submit_button('Submit'):
#            instance = cls()
#            for column in cls.__table__.columns:
#                if column.name not in exclude:
#                    setattr(instance, column.name, getattr(cls, column.name))
#            with session(db) as db:
#                db.add(instance)
#            st.success(f'Added {cls.__name__}!')
    pass


