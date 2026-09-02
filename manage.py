"""Database utility commands.

    python manage.py init-db     create the schema
    python manage.py seed        create the schema and insert the demo campus
    python manage.py summary     print the row count of every table
    python manage.py reset       delete the database file and re-seed it
"""

import argparse
import os
import sys

from app.config import BaseConfig
from app.database import connect, init_schema
from app.seed import seed_database, summary

DB_PATH = BaseConfig.DATABASE_PATH


def _print_counts(connection):
    counts = summary(connection)
    width = max(len(name) for name in counts)
    for table, total in counts.items():
        print("%-*s %d" % (width + 2, table, total))
    print("-" * (width + 8))
    print("%-*s %d" % (width + 2, "TOTAL ROWS", sum(counts.values())))


def main(argv=None):
    parser = argparse.ArgumentParser(description="AISCaMS database management")
    parser.add_argument("command", choices=["init-db", "seed", "summary", "reset"])
    args = parser.parse_args(argv)

    if args.command == "reset" and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Removed %s" % DB_PATH)

    connection = connect(DB_PATH)
    init_schema(connection)
    if args.command in ("seed", "reset"):
        seed_database(connection)
        print("Demo campus seeded in %s" % DB_PATH)
    if args.command in ("seed", "reset", "summary"):
        _print_counts(connection)
    if args.command == "init-db":
        print("Schema ready at %s" % DB_PATH)
    connection.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
