from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from settings import settings

# Engine: knows how to communicate with PostgreSQL.
engine = create_engine(settings.database_url)

# Factory: creates new database sessions.
SessionLocal = sessionmaker(bind=engine)


def get_db():
    database_session = SessionLocal()
    try:
        yield database_session
    finally:
        database_session.close()