"""Everything about connecting to PostgreSQL lives here."""
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

# Connection string: postgresql://USER:PASSWORD@HOST:PORT/DATABASE
# Later, in Docker Compose, you will just set DATABASE_URL and change HOST to the db service name.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://aviatickets:aviatickets@localhost:5432/aviatickets",
)


def get_connection():
    """Open a new connection. Rows come back as dicts: {"id": 1, "seat": "12C"}.

    Use it as `with get_connection() as conn:` - it commits on success
    and rolls back automatically if an error happens.
    """
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    """Create tables and demo flights from schema.sql."""
    sql = (Path(__file__).parent / "schema.sql").read_text()
    with get_connection() as conn:
        conn.execute(sql)
