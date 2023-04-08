from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists
from extensions import Base, engine
import streamlit as st
from models import User
from contextlib import contextmanager


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

def commit_or_rollback(db, commit: bool):
    with session(db) as db:
        if commit:
            db.commit()
            st.success("Changes committed!")
        else:
            db.rollback()
            st.warning("Changes rolled back.")

def get_user(db, username: str):
    return db.query(User).filter(User.username == username).first()

def reset_autoincrement(table_name):
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

@st.cache_resource
def create_db():
    '''creates engine and returns session'''
    if not database_exists(engine.url):
        try:
            create_database(engine.url)
            print('created database')
        except Exception as e:
            print(f"Could not create database: {e}")
            return None
    
    try:
        conn = engine.connect()
        print('Connection successful!')
        conn.close()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None
    
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        Base.metadata.create_all(engine)
        st.session_state['db'] = session
        print('Successfully created database.')
        return session
    except Exception as e:
        print(f"Error creating tables: {e}")
        session.close()
        return None

@st.cache_resource
def clear_db():
    try:
        Base.metadata.drop_all(engine)
        return True
    except Exception as e:
        print(f"Error dropping tables: {e}")
        return False