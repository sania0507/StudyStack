import os
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

# Safety check BEFORE importing the application.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError("Set TEST_DATABASE_URL before running tests")

parsed_url = make_url(TEST_DATABASE_URL)

if parsed_url.database != "studystack_analytics_test":
    raise RuntimeError(
        "Tests may only use the studystack_analytics_test database"
    )

# The analytics service only reads these tables, but the tests need to
# create and drop them, so the URL is set before importing.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from main import app
from auth import get_current_user_id
from database import get_db
from models import Base, Domain, StudySession, Task

test_engine = create_engine(TEST_DATABASE_URL)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_current_user(request: Request) -> UUID:
    user_id = request.headers.get("X-Test-User-ID")

    if not user_id:
        raise RuntimeError("Missing X-Test-User-ID test header")

    return UUID(user_id)


@pytest.fixture(autouse=True)
def test_database():
    Base.metadata.create_all(bind=test_engine)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = override_current_user

    try:
        yield
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def user_a():
    return uuid4()


@pytest.fixture
def client(user_a):
    with TestClient(
        app,
        headers={"X-Test-User-ID": str(user_a)},
    ) as test_client:
        yield test_client


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def domain_id(client, db, user_a):
    domain = Domain(
        id=uuid4(),
        name="University",
        colour="violet",
        user_id=user_a,
    )
    db.add(domain)
    db.commit()

    return domain.id


def add_session(db, user_id, domain_id, minutes, finished_at):
    session = StudySession(
        id=uuid4(),
        user_id=user_id,
        domain_id=domain_id,
        minutes=minutes,
        finished_at=finished_at,
    )
    db.add(session)
    db.commit()

    return session


def add_task(db, domain_id, completed=False, due_date=None):
    task = Task(
        id=uuid4(),
        domain_id=domain_id,
        title="Study DBMS",
        completed=completed,
        completed_at=datetime.now() if completed else None,
        due_date=due_date,
    )
    db.add(task)
    db.commit()

    return task


@pytest.fixture
def add_session():
    return add_session


@pytest.fixture
def add_task():
    return add_task

