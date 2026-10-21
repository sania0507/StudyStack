import os
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

if parsed_url.database != "studystack_main_test":
    raise RuntimeError(
        "Tests may only use the studystack_main_test database"
    )

# Import the app only after verifying the test database URL.
from main import app
from auth import get_current_user_id
from database import get_db
from models import Base

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


# Each request identifies its simulated test user through a header.
# This override is for tests only; production JWT authentication remains unchanged.
def override_current_user(request: Request) -> UUID:
    user_id = request.headers.get("X-Test-User-ID")

    if not user_id:
        raise RuntimeError("Missing X-Test-User-ID test header")

    return UUID(user_id)


@pytest.fixture(autouse=True)
def test_database():
    # All tables are created and dropped once per test.
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
def user_b():
    return uuid4()


@pytest.fixture
def client(user_a):
    with TestClient(
        app,
        headers={"X-Test-User-ID": str(user_a)},
    ) as test_client:
        yield test_client


@pytest.fixture
def second_user_client(user_b):
    with TestClient(
        app,
        headers={"X-Test-User-ID": str(user_b)},
    ) as test_client:
        yield test_client


@pytest.fixture
def domain_id(client):
    response = client.post(
        "/domains",
        json={"name": "University"},
    )
    assert response.status_code == 200
    return response.json()["id"]


@pytest.fixture
def task_id(client, domain_id):
    response = client.post(
        "/tasks",
        json={
            "domain_id": domain_id,
            "title": "Study database systems",
        },
    )
    assert response.status_code == 200
    return response.json()["id"]
