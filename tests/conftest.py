"""Shared Pytest fixtures: isolated database, seeded campus, facade and client.

The demo campus is seeded once per test session into a template database file;
every test then works on its own copy, so the tests stay fully isolated while
the expensive password hashing runs only once.
"""

import os
import shutil
import sys
from datetime import timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app                       # noqa: E402
from app.database import connect, init_schema    # noqa: E402
from app.seed import seed_database               # noqa: E402
from app.services.campus_facade import CampusFacade  # noqa: E402
from app.utils import now, to_db                 # noqa: E402


@pytest.fixture(scope="session")
def template_db(tmp_path_factory):
    """A seeded database created once and copied by every test."""
    path = str(tmp_path_factory.mktemp("template") / "aiscams_template.db")
    connection = connect(path)
    init_schema(connection)
    seed_database(connection)
    connection.close()
    return path


@pytest.fixture
def db_path(tmp_path, template_db):
    path = str(tmp_path / "aiscams_test.db")
    shutil.copyfile(template_db, path)
    return path


@pytest.fixture
def empty_db_path(tmp_path):
    """A database with the schema only, used by the seeding tests."""
    return str(tmp_path / "aiscams_empty.db")


@pytest.fixture
def connection(db_path):
    conn = connect(db_path)
    yield conn
    conn.close()


@pytest.fixture
def seeded(connection):
    """The connection of an already seeded campus."""
    return connection


@pytest.fixture
def facade(seeded):
    return CampusFacade(seeded)


@pytest.fixture
def repos(facade):
    return facade.repos


@pytest.fixture
def users(repos):
    """Handy dictionary of the seeded demo accounts."""
    return {user.username: user for user in repos.users.list_users()}


@pytest.fixture
def resources(repos):
    return {resource.code: resource for resource in repos.resources.list_resources()}


@pytest.fixture
def app(db_path):
    return create_app("testing", DATABASE_PATH=db_path, SEED_ON_STARTUP=False,
                      SECRET_KEY="test-key")


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def login(client):
    """Sign a demo account in and return the test client."""
    def _login(username, password="campus123"):
        response = client.post("/login", data={"username": username,
                                               "password": password},
                               follow_redirects=True)
        assert response.status_code == 200
        return client
    return _login


@pytest.fixture
def slot():
    """A conflict free future booking window (start, end) as strings."""
    start = (now() + timedelta(days=3)).replace(hour=9, minute=0, second=0, microsecond=0)
    return to_db(start), to_db(start + timedelta(hours=2))
