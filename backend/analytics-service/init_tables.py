#!/usr/bin/env python
"""Creates only the tables this service owns.

The task service owns the shared schema. Analytics only owns
processed_events, so it must not try to create domains or tasks —
that would race the task service at startup.

The consumer container starts at the same moment and creates the same
table, so a duplicate-object error here simply means the other container
won the race. That is a success, not a failure.
"""
from sqlalchemy.exc import IntegrityError, ProgrammingError

from database import engine
from models import ProcessedEvent

try:
    ProcessedEvent.__table__.create(bind=engine, checkfirst=True)
    print("processed_events is ready.")
except (IntegrityError, ProgrammingError):
    # The other analytics container created it first.
    print("processed_events already exists (created by another container).")
