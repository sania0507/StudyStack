from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+psycopg://studystack_user:0507@localhost:5432/studystack"

# SQLAlchemy's engine → It creates SQLAlchemy's engine, which knows how to communicate with the database.
engine = create_engine(DATABASE_URL)

# SQLAlchemy's Session → manages a particular DB transaction
SessionLocal = sessionmaker(bind=engine) 
# sessionmaker is a factory for creating new Session objects(basically gives us a new session),
# Session Objects are used to interact with the database.
# The bind=engine argument tells the sessionmaker to use the engine we created earlier to connect to the database.
