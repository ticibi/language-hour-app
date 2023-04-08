from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine
from config import DB_USERNAME, DB_PASSWORD, HOST, DB_NAME


# Define the Base
Base = declarative_base()

# Define the SQLAlchemy model for your table
engine = create_engine(f'mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{HOST}/{DB_NAME}')

