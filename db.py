from sqlalchemy import create_engine, Column, Integer, String, Sequence, Boolean, Date, DateTime, ForeignKey, ARRAY, LargeBinary
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy_utils import create_database, database_exists
import pandas as pd
from datetime import datetime
import json
from config import DB_USERNAME, DB_PASSWORD, HOST, DB_NAME
import streamlit as st

# Define the SQLAlchemy model for your table
Base = declarative_base()
engine = create_engine(f'mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{HOST}/{DB_NAME}')


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    name = Column(String(50))
    username = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(100))
    is_admin = Column(Boolean, default=False)
    email = Column(String(50))
    group_id = Column(Integer, ForeignKey('groups.id'))
    language_hours = relationship('LanguageHour', back_populates='user')
    scores = relationship('Score')
    courses = relationship('Course')
    files = relationship('File')

class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, Sequence('group_id_seq'), primary_key=True)
    name = Column(String(50), nullable=False)
    users = relationship('User', backref='group') # Relationship with User table

class Course(Base):
    __tablename__ = 'courses'
    id = Column(Integer, Sequence('course_id_seq'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))  # Define foreign key relationship
    name = Column(String(50))
    code = Column(String(50))
    length = Column(Integer)
    start_date = Column(Date)
    end_date = Column(Date)
    user = relationship('User', back_populates='courses')

class LanguageHour(Base):
    __tablename__ = 'language_hours'
    id = Column(Integer, Sequence('language_hour_id_seq'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))  # Define foreign key relationship
    date = Column(Date)
    hours = Column(Integer)
    description = Column(String(250))
    modalities = Column(String(100))
    user = relationship('User', back_populates='language_hours')

    def __init__(self, date, hours, description, modalities, user_id):
        self.date = date
        self.hours = hours
        self.description = description
        self.modalities = json.dumps(modalities)  # Serialize array to JSON string
        self.user_id = user_id

    @property
    def modalities_list(self):
        return json.loads(self.modalities) if self.modalities else []

class Score(Base):
    __tablename__ = 'scores'
    id = Column(Integer, Sequence('score_id_seq'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))  # Define a foreign key relationship
    langauge = Column(String(50))
    dicode = Column(String(50))
    listening = Column(String(5))
    reading = Column(String(5))
    speaking = Column(String(5))
    date = Column(Date)
    user = relationship('User', back_populates='scores')

class File(Base):
    __tablename__ = 'files'
    id = Column(Integer, Sequence('file_id_seq'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))  # Define a foreign key relationship
    name = Column(String(100))
    file = Column(LargeBinary)
    user = relationship('User', back_populates='files')

class Log(Base):
    __tablename__ = 'logs'
    id = Column(Integer, Sequence('log_id_seq'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))  # Define a foreign key relationship
    message = Column(String(255))
    date = Column(Date)

class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, Sequence('message_id_seq'), primary_key=True)
    sender_id = Column(Integer, ForeignKey('users.id'))
    recipient_id = Column(Integer, ForeignKey('users.id'))
    content = Column(String(255))
    timestamp = Column(DateTime, default=datetime.utcnow)

@st.cache_resource
def create_db():
    '''creates engine and returns session'''
    if not database_exists(engine.url):
        try:
            create_database(engine.url)
            print('created database')
        except:
            print('could not create database')
    try:
        conn = engine.connect()
        print('Connection successful!')
        conn.close()
    except Exception as e:
        print('Error:', e)
    # Create an SQLalchemy engine and session
    #engine = create_engine(DATABASE_URI)  # Replace with your database connection details
    #Base.metadata.drop_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    # Create the table if it doesn't exist
    Base.metadata.create_all(engine)
    return session

def clear_db():
    Base.metadata.drop_all(engine)

## Query the data from the table
#users = session.query(User).all()

## Convert the query result to a Pandas DataFrame
#df = pd.DataFrame([(user.id, user.name, user.age) for user in users], columns=['ID', 'Name', 'Age'])
#
## Save the DataFrame to an Excel file
#df.to_excel('users.xlsx', index=False)
