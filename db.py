from sqlalchemy.orm import sessionmaker
from extensions import Base, db1
import streamlit as st
from models import User, DBConnect, LanguageHour, Score
from contextlib import contextmanager
from sqlalchemy import create_engine, MetaData, exists, and_, text
from sqlalchemy.engine.url import make_url
from config import HOST, DB_USERNAME, DB_PASSWORD, CONNECTOR
from models import Database
from utils import calculate_required_hours, spacer, dot_dict, calculate_total_hours, filter_monthly_hours
import pandas as pd
import calendar
import datetime


@contextmanager
def session(db):
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()

def connect_user_to_database(username):
    # Create an engine for the appropriate database
    user_db = get_user_database_connection_info(db1, username)
    if not user_db:
        return None
    user_engine = create_engine(f'{CONNECTOR}://{user_db.username}:{user_db.password}@{user_db.host}/{user_db.name}')
    st.session_state.engine = user_engine
    Base.metadata.bind = user_engine

    # Create a session for the appropriate database
    UserSession = sessionmaker(bind=user_engine)
    user_session = UserSession()
    st.session_state.session = user_session

    db_name = get_database_name(user_engine)
    st.sidebar.write(f'connected to :blue[{db_name}]')

    return user_session

def check_db_empty(db):
    with session(db) as db:
        users = db.query(User).count()
        if not users:
            return True
        return False

def check_username_exists(db, username):
    with session(db) as db:
        result = db.query(exists().where(DBConnect.username==username)).scalar()
        return result

def get_user_database_connection_info(db, username):
        '''connect the user to the appropriate database'''
        data = get_db_id_by_username(db, username)
        if not data:
            return None
        db_info = get_database_by_id(db, data.db_id)
        return db_info

def get_db_id_by_username(db, username):
    with session(db) as db:
        result = db.query(DBConnect).filter(DBConnect.username==username).first()
        return dot_dict(result.to_dict()) if result else None

def get_database_by_id(db, id):
    with session(db) as db:
        result = db.query(Database).filter(Database.id==id).first()
        return dot_dict(result.to_dict()) if result else None

def get_database_by_name(db, name):
    with session(db) as db:
        result = db.query(Database).filter(Database.name==name).first()
        return dot_dict(result.to_dict()) if result else None

def get_database_name(engine):
    url = make_url(engine.url)
    return url.database

def commit_or_rollback(db, commit: bool):
    with session(db) as db:
        if commit:
            db.commit()
            st.success("Changes committed!")
        else:
            db.rollback()
            st.warning("Changes rolled back.")

def get_all_users(_db):
    '''returns all user models as dot dict'''
    with session(_db) as _db:
        results = _db.query(User).all()
        data = []
        for item in results:
            data.append(dot_dict(item.to_dict()))
        return data
    
def get_score_by_id(db, id):
    '''returns all user models as dot dict'''
    with session(db) as db:
        result = db.query(Score).get(id)
        return dot_dict(result.to_dict()) if result else None

def get_user_by(_db, selector, value):
    '''returns user model as dot dict based on selector type: username, last_name, or id'''
    with session(_db) as _db:
        if selector == 'username':
            result = _db.query(User).filter(User.username==value).first()
        elif selector == 'last_name':
            result = _db.query(User).filter(User.last_name==value).first()
        elif selector == 'id':
            result = _db.query(User).filter(User.id==value).first()
        else:
            return None
        return dot_dict(result.to_dict()) if result else None

def reset_autoincrement(engine, table_name):
    with engine.connect() as conn:
        conn.execute(f"ALTER TABLE {table_name} AUTO_INCREMENT = 1")

def delete_row_by_id(db, cls, id):
    with session(db) as db:
        row = db.query(cls).filter_by(id=id).first()
        if row:
            db.delete(row)
            st.success(f"Row deleted successfully!")
        else:
            st.warning(f"Row not found.")

def change_database_connection(db_name, username=DB_USERNAME, password=DB_PASSWORD, host=HOST):
    return create_engine(f'mysql+pymysql://{username}:{password}@{host}/{db_name}')

def test_db_connection(engine):
    try:
        conn = engine.connect()
        print('Connection successful!')
        conn.close()
        return True
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return False

def clear_db(engine) -> bool:
    '''clear database: delete all tables and data inside the database'''
    try:
        Base.metadata.drop_all(engine)
        return True
    except Exception as e:
        print(f"Error dropping tables: {e}")
        return False

def get_databases(_db):
    with session(_db) as _db:
        results = _db.query(Database).all()
        data = []
        for item in results:
            data.append(dot_dict(item.to_dict()))
        return data

def get_table(_db, table):
    with session(_db) as _db:
        results = _db.query(table).all()
        df = pd.DataFrame([item.to_dict() for item in results])
        return df

def get_database_tables(_engine):
    # create a metadata object and reflect the database schema
    metadata = MetaData()
    metadata.reflect(bind=_engine)

    # get a list of all table names in the database
    return metadata.tables.keys()

def upload_bulk_excel(db, file):
    xls = pd.ExcelFile(file)
    for sheet in xls.sheet_names:
        df = pd.read_excel(file, sheet_name=sheet, engine='openpyxl')
        df = df.fillna('')

        # Split the sheet name at the comma
        split_name = sheet.split(', ')

        # Get the user database info
        with session(db) as db:
            user = db.query(User).filter(and_(User.first_name==split_name[1], User.last_name==split_name[0])).first()
            if not user:
                print(f'skipping {sheet}')
                st.info(f'skipping {sheet}')
                continue

            for _, row in df.iterrows():
                language_hour = LanguageHour(
                    user_id=user.id,
                    date=row['Date'],
                    hours=row['Hours'],
                    description=row['Description'],
                    modalities=row['Modality'],
                )
                db.add(language_hour)
        print(f'added all entries from {sheet}')
        st.info(f'added all entries from {sheet}')
    st.success('Finished adding all entries.')

def get_table_names(_engine):
    metadata = MetaData()
    metadata.reflect(bind=_engine)
    return metadata.tables.keys()

def get_user_model_by_id(_db, cls, user_id):
    '''returns user data for provided model as a dot dict'''
    with session(_db) as _db:
        results = _db.query(cls).filter(cls.user_id==user_id).all()
        data = []
        for item in results:
            data.append(dot_dict(item.to_dict()))
        return data

def get_user_language_hours(db, user_id):
    '''returns user language hours as a dot dict'''
    with session(db) as _db:
        results = _db.query(LanguageHour).filter(LanguageHour.user_id==user_id).all()
        data = []
        for item in results:
            data.append(dot_dict(item.to_dict()))
        return data

def rundown(db):
    current_month = datetime.date.today().month
    current_year = datetime.date.today().year

    cols = st.columns([1, 1, 1])
    selected_month = cols[0].selectbox('Month', key='rundown_month', index=current_month, options=calendar.month_name)
    year = cols[1].number_input('Year', key='rundown_year', value=current_year, min_value=2021, step=1)
    spacer(cols[2], 2)
    if cols[2].button('Gimme da rundown', type='primary'):
        pass

        month = list(calendar.month_name).index(selected_month)

        data = []
        users = get_all_users(db)
        for user in users:
            lang_hours = get_user_language_hours(db, user.id)
            score_data = get_user_model_by_id(db, Score, user.id)
            if not score_data:
                st.warning(f'skipping {user.username}: no score data found.')
                continue
            hours_required = calculate_required_hours(score_data[0])
            filtered_hours = filter_monthly_hours(lang_hours, month, year)
            hours_done = calculate_total_hours(filtered_hours)
            status = '✅' if hours_done >= hours_required else '❌'
            info = dot_dict({'status': status,'user': user.last_name, 'hours': hours_done, 'hours_required': hours_required})
            data.append(info)

        df = pd.DataFrame(data)
        if df.empty:
            st.info('There is no data to show.')
            return
        df = df.set_index('user')
        st.dataframe(df, use_container_width=False)

def add_column(engine, table, column_name, data_type):
    connection = engine.connect()
    statement = text(f'ALTER TABLE {table} ADD COLUMN {column_name} {data_type}')
    try:
        connection.execute(statement)
        print(f'Added column "{column_name} ({data_type})" to {table}')
        st.info(f'Added column "{column_name} ({data_type})" to {table}')
    except:
        print(f'Failed to add column to {table}')
        st.warning(f'Failed to add column to {table}')
    connection.close()

def lowdown(db):
    def highlight_row(row):
        today = datetime.date.today()
        delta = datetime.timedelta(days=60)
        due_date = row[3] + datetime.timedelta(days=365)
        prior = due_date - delta
        diff = due_date - today
        if today >= prior:
            return ['background-color: rgba(255, 227, 18, 0.2)'] * len(row)
        return [''] * len(row)

    data = []
    users = get_all_users(db)
    for user in users:
        name = f'{user.last_name}, {user.first_name}'
        scores = get_user_model_by_id(db, Score, user.id)
        if not scores:
            continue
        if scores[0].CL is True:
            data.append([name, scores[0].dicode, f'{scores[0].listening}/{scores[0].reading}', scores[0].date])
    
    df = pd.DataFrame(data, columns=['Name', 'Dicode', 'Score', 'DLPT Date'])
    df = df.style.apply(highlight_row, axis=1)
    st.dataframe(df, use_container_width=True)

