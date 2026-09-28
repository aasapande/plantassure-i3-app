"""MySQL connection settings, read from environment variables (backend/.env
locally, the hosting provider's settings when deployed). Never hard-coded.

For a hosted database that requires SSL (e.g. Aiven), set DB_SSL_CA_PEM to the
provider's CA certificate text; the connection is then encrypted and verified.
"""
import os
import tempfile
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

import pymysql
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))


@lru_cache(maxsize=1)
def ssl_options() -> dict | None:
    pem = os.environ.get("DB_SSL_CA_PEM", "").strip()
    if not pem:
        return None
    ca_file = Path(tempfile.gettempdir()) / "plantassure-db-ca.pem"
    ca_file.write_text(pem.replace("\\n", "\n") + "\n", encoding="utf-8")
    return {"ca": str(ca_file)}


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
        ssl=ssl_options(),
        connect_timeout=15,
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
