from .base import Base
from .domain import Domain
from .task import Task
#That Task import causes SQLAlchemy to register the tasks table in Base.metadata.