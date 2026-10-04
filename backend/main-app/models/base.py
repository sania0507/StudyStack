from sqlalchemy.orm import DeclarativeBase


# This > creates our application's base class, ITS the foundation from which further ORM models are declared.
# Domain class and other ORM models(Task, StudySession) will inherit from this base class.
class Base(DeclarativeBase):
    pass