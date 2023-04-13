from sqlalchemy import Column, Integer, String, Sequence, Boolean, Date, DateTime, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from datetime import datetime
from extensions import Base
import json
import pandas as pd


MODELS = ['User', 'Course', 'LanguageHour', 'Score', 'File', 'Log', 'Message']

class BaseModel:
    def __repr__(self):
        attrs = []
        for k, v in self.__dict__.items():
            attrs.append(f"{k}={v!r}")
        attrs_str = ", ".join(attrs)
        return f"{self.__class__.__name__}({attrs_str})"
    
    def to_dataframe(self):
        data = {}
        for column in self.__table__.columns:
            data[column.name] = getattr(self, column.name)
        df = pd.DataFrame([data])
        df = df.reset_index(drop=True)
        return df
    
    def to_dict(self):
        data = {}
        for column in self.__table__.columns:
            data[column.name] = getattr(self, column.name)
        return data

class DBConnect(Base, BaseModel):
    __tablename__ = 'dbconnect'
    id = Column(Integer, Sequence('dbc_id_seq'), primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    db_id = Column(Integer)

class Database(Base, BaseModel):
    __tablename__ = 'databases'
    id = Column(Integer, Sequence('db_id_seq'), primary_key=True)
    name = Column(String(55))
    host = Column(String(55))
    port = Column(Integer)
    username = Column(String(55))
    password = Column(String(55))

class User(Base, BaseModel):
    __tablename__ = 'users'
    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    first_name = Column(String(25))
    last_name = Column(String(25))
    middle_initial = Column(String(2))
    username = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(100))
    is_admin = Column(Boolean, default=False)
    is_dev = Column(Boolean, default=False)
    email = Column(String(50))
    language_hours = relationship('LanguageHour', back_populates='user')
    scores = relationship('Score')
    courses = relationship('Course')
    files = relationship('File')

class Course(Base, BaseModel):
    __tablename__ = 'courses'
    id = Column(Integer, Sequence('course_id_seq'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))  # Define foreign key relationship
    name = Column(String(50))
    code = Column(String(50))
    length = Column(Integer)
    start_date = Column(Date)
    end_date = Column(Date)
    user = relationship('User', back_populates='courses')

class LanguageHour(Base, BaseModel):
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
    
class Score(Base, BaseModel):
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

class File(Base, BaseModel):
    __tablename__ = 'files'
    id = Column(Integer, Sequence('file_id_seq'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))  # Define a foreign key relationship
    name = Column(String(100))
    content = Column(LargeBinary) # rename to "content" from "file"
    user = relationship('User', back_populates='files')

class Log(Base, BaseModel):
    __tablename__ = 'logs'
    id = Column(Integer, Sequence('log_id_seq'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))  # Define a foreign key relationship
    message = Column(String(255))
    timestamp = Column(DateTime, default=datetime.utcnow)

class Message(Base, BaseModel):
    __tablename__ = 'messages'
    id = Column(Integer, Sequence('message_id_seq'), primary_key=True)
    sender_id = Column(Integer, ForeignKey('users.id'))
    recipient_id = Column(Integer, ForeignKey('users.id'))
    read = Column(Boolean, default=False)
    archived = Column(Boolean, default=False)
    content = Column(String(255))
    timestamp = Column(DateTime, default=datetime.utcnow)

TABLE = {
    'DBConnect': DBConnect,
    'Database': Database,
    'User': User,
    'Course': Course,
    'LanguageHour': LanguageHour,
    'Score': Score,
    'File': File,
    'Log': Log,
    'Message': Message,
}