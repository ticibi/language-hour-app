from sqlalchemy import Column, Integer, String, Sequence, Boolean, Date, DateTime, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from datetime import datetime
from extensions import Base
import json
import pandas as pd

__models__ = ['User', 'Group', 'Course', 'LanguageHour', 'Score', 'File', 'Log', 'Message']

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

class User(Base, BaseModel):
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
    
    def to_dataframe(self):
        data = {
            'id': [self.id],
            'name': [self.name],
            'username': [self.username],
            'password_hash': [self.password_hash],
            'is_admin': [self.is_admin],
            'group_id': [self.group_id],
        }
        return pd.DataFrame(data)

class Group(Base, BaseModel):
    __tablename__ = 'groups'
    id = Column(Integer, Sequence('group_id_seq'), primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    users = relationship('User', backref='group') # Relationship with User table
    
    def to_dataframe(self):
        data = {
            'id': [self.id],
            'name': [self.name],
        }
        return pd.DataFrame(data)

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

    def __repr__(self):
        return f"<Course(id='{self.id}', name='{self.name}')>"
    
    def to_dataframe(self):
        data = {
            'id': [self.id],
            'name': [self.name],
        }
        return pd.DataFrame(data)

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
    file = Column(LargeBinary)
    user = relationship('User', back_populates='files')

class Log(Base, BaseModel):
    __tablename__ = 'logs'
    id = Column(Integer, Sequence('log_id_seq'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))  # Define a foreign key relationship
    message = Column(String(255))
    date = Column(Date)

class Message(Base, BaseModel):
    __tablename__ = 'messages'
    id = Column(Integer, Sequence('message_id_seq'), primary_key=True)
    sender_id = Column(Integer, ForeignKey('users.id'))
    recipient_id = Column(Integer, ForeignKey('users.id'))
    content = Column(String(255))
    timestamp = Column(DateTime, default=datetime.utcnow)

hash_table = {
    'User': User,
    'Group': Group,
    'Course': Course,
    'LanguageHour': LanguageHour,
    'Score': Score,
    'File': File,
    'Log': Log,
    'Message': Message,
}