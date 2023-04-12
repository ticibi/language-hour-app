from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy_utils import create_database, database_exists
from config import DB_USERNAME, DB_PASSWORD, HOST, DB1, CONNECTOR

def create_session(engine):
    '''create the database: creates engine and returns session'''
    if not database_exists(engine.url):
        try:
            create_database(engine.url)
            print('created database')
        except Exception as e:
            print(f"Could not create database: {e}")
            return False

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        Base.metadata.create_all(engine)
        print('Successfully created database.')
        return session
    except Exception as e:
        print(f"Error creating tables: {e}")
        session.close()
        return False
    
# Define the base
Base = declarative_base()

# Define the SQLAlchemy model for your table
db1_engine = create_engine(f'{CONNECTOR}://{DB_USERNAME}:{DB_PASSWORD}@{HOST}/{DB1}')
db1 = create_session(db1_engine)

