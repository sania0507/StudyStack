from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from settings import settings

engine=create_engine(settings.database_url)
SessionLocal=sessionmaker(bind=engine)

def get_db():
    database_session=SessionLocal() # SessionLocal() creates a database session.
    try: 
        yield database_session # yield database_session hands that session to FastAPI's dependency system.
    finally: # finally ensures .close() runs when the dependency finishes, including when the request raises an exception.
        database_session.close() 
# closing a session is not the same as committing a transaction. 
#Your endpoint will still need to commit successful database changes and roll back failed transactions.

