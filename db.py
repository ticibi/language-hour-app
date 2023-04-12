from sqlalchemy.orm import sessionmaker
from extensions import Base, db1
import streamlit as st
from models import User, DBConnect
from contextlib import contextmanager
from sqlalchemy import create_engine, MetaData, exists
from sqlalchemy.engine.url import make_url
from config import HOST, DB_USERNAME, DB_PASSWORD, CONNECTOR
from models import Database
from utils import dot_dict
import pandas as pd


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
        db_info = None
        data = get_db_id_by_username(db, username)
        if data:
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

def get_user_by_username(db, username):
    with session(db) as _db:
        result = _db.query(User).filter(User.username==username).first()
        return dot_dict(result.to_dict()) if result else None

def get_user_by_name(db, last_name):
    with session(db) as _db:
        result = _db.query(User).filter(User.last_name==last_name).first()
        return dot_dict(result.to_dict()) if result else None

def get_user_by_id(db, id):
    with session(db) as _db:
        result = _db.query(User).filter(User.id==id).first()
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

def test_db(engine):
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

def edit_user(db, user_id: int, name: str = None, username: str = None, password: str = None, is_admin: bool = None, email: str = None, group_id: int = None) -> bool:
    with session(db) as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            if name:
                user.name = name
            if username:
                user.username = username
            if password:
                user.password_hash = password
            if is_admin is not None:
                user.is_admin = is_admin
            if email:
                user.email = email
            if group_id:
                user.group_id = group_id
            return True
        return False

def get_databases(db):
    with session(db) as db:
        results = db.query(Database).all()
        data = []
        for item in results:
            data.append(dot_dict(item.to_dict()))
        return data

def get_table(db, table):
    with session(db) as db:
        results = db.query(table).all()

        df = pd.DataFrame([item.to_dict() for item in results])
        return df
    
def get_database_tables(engine):
    # create a metadata object and reflect the database schema
    metadata = MetaData()
    metadata.reflect(bind=engine)

    # get a list of all table names in the database
    return metadata.tables.keys()
