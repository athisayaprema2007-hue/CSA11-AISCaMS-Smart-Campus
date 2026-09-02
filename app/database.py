"""SQLite connection management and schema bootstrap.

The database is created automatically the first time the application starts,
so no manual migration step is required on a clean machine.
"""

import os
import sqlite3

from flask import current_app, g

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.sql")


def connect(db_path):
    """Open a connection with row access by name and foreign keys enforced."""
    if db_path != ":memory:":
        directory = os.path.dirname(os.path.abspath(db_path))
        if directory and not os.path.isdir(directory):
            os.makedirs(directory, exist_ok=True)
    connection = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_schema(connection):
    """Create every table/index declared in schema.sql (idempotent)."""
    with open(SCHEMA_FILE, "r", encoding="utf-8") as handle:
        connection.executescript(handle.read())
    connection.commit()
    return connection


def create_database(db_path, seed=True):
    """Create (if needed) and optionally seed a database file."""
    from .seed import seed_database

    connection = connect(db_path)
    init_schema(connection)
    if seed:
        seed_database(connection)
    return connection


def get_db():
    """Return the connection bound to the current Flask request context."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE_PATH"])
    return g.db


def close_db(exception=None):  # pragma: no cover - exercised by Flask teardown
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_app(app):
    """Register teardown handlers and ensure the database exists."""
    app.teardown_appcontext(close_db)
    db_path = app.config["DATABASE_PATH"]
    connection = connect(db_path)
    try:
        init_schema(connection)
        if app.config.get("SEED_ON_STARTUP", False):
            from .seed import seed_database

            seed_database(connection)
    finally:
        connection.close()
