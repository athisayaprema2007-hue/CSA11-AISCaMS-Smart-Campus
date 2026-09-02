"""Repository pattern - shared SQLite access helpers.

Repositories are the only objects in the system that speak SQL.  Services and
the web layer receive domain objects, which keeps persistence details out of
the business rules (low coupling) and puts every query for one aggregate in a
single cohesive class.
"""

import sqlite3

from ..exceptions import NotFoundError, ValidationError


class BaseRepository:
    """Common behaviour for every repository."""

    table = None

    def __init__(self, connection):
        self._connection = connection

    @property
    def connection(self):
        return self._connection

    # ----------------------------------------------------------- utilities
    def query(self, sql, params=()):
        return self._connection.execute(sql, params).fetchall()

    def query_one(self, sql, params=()):
        return self._connection.execute(sql, params).fetchone()

    def scalar(self, sql, params=(), default=0):
        row = self.query_one(sql, params)
        if row is None or row[0] is None:
            return default
        return row[0]

    def execute(self, sql, params=(), commit=True):
        try:
            cursor = self._connection.execute(sql, params)
        except sqlite3.IntegrityError as exc:
            raise ValidationError("Database rejected the operation: %s" % exc,
                                  {"constraint": str(exc)})
        if commit:
            self._connection.commit()
        return cursor

    def commit(self):
        self._connection.commit()

    def count(self, where="1=1", params=()):
        return int(self.scalar("SELECT COUNT(*) FROM %s WHERE %s" % (self.table, where),
                               params))

    def exists(self, where, params=()):
        return self.count(where, params) > 0

    def require(self, row, message):
        if row is None:
            raise NotFoundError(message)
        return row
