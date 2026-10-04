from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import uuid

# This > creates our application's base class, ITS the foundation from which further ORM models are declared. 
# Domain class and other ORM models(Task, StudySession) will inherit from this base class.
class Base(DeclarativeBase):
    pass

# Domain class is a SQLAlchemy ORM model that has inherited from base class and represents the "domains" table in the PostgreSQL database. 
# The Domain class has three attributes: id, name, and colour. 
# The id attribute has python-type= UUID and is the primary key for the table. The name and colour attributes has python-type= strings and cannot be null.

class Domain(Base):
    __tablename__ = "domains" #SQLAlchemy maps this class to the DB table in postgresql named domains.

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True) # tells SQLAlchemy that python-side type is UUID.
    name: Mapped[str] = mapped_column(nullable=False)
    colour: Mapped[str] = mapped_column(nullable=False)
    
