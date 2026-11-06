"""Everything about connecting to PostgreSQL lives here."""
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://aviatickets:aviatickets@localhost:5432/aviatickets",
)


def get_connection():
    """Open a new connection. Rows come back as dicts: {"id": 1, "seat": "12C"}."""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    """Create tables and demo flights from schema.sql."""
    sql = (Path(__file__).parent / "schema.sql").read_text()
    with get_connection() as conn:
        # Several replicas start at the same time: the lock makes them run
        # schema.sql one after another (no duplicate demo flights).
        conn.execute("SELECT pg_advisory_xact_lock(827364)")
        conn.execute(sql)
