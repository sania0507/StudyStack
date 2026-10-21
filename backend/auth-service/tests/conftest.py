
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Set this in your shell before pytest runs.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError("Set TEST_DATABASE_URL before running tests")

if not TEST_DATABASE_URL.rstrip("/").endswith("/studystack_auth_test"):
    raise RuntimeError(
        "Tests may only use the studystack_auth_test database"
    )

from main import app
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


@pytest.fixture
def client():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()

