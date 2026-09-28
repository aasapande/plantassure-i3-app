"""MySQL connection settings, read from backend/.env (never hard-coded)."""
import os
from contextlib import contextmanager
from pathlib import Path

import pymysql
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))


def connect(database: str | None = None) -> pymysql.connections.Connection:
    return pymysql.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", "3307")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=database or os.environ.get("DB_NAME", "plantassure_i3"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


@contextmanager
def cursor(database: str | None = None):
    """Yields a cursor; commits on success, rolls back on error."""
    conn = connect(database)
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
