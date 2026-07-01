import os
from contextlib import contextmanager

import psycopg2
from dotenv import load_dotenv

load_dotenv()

# All DB_* values always come from the environment — populated from .env
# locally, or injected by the hosting platform in the cloud. No credentials
# are ever hardcoded here.
_REQUIRED_VARS = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]


def _db_config() -> dict:
    app_env = os.getenv("APP_ENV", "local")
    values = {}

    for key in _REQUIRED_VARS:
        value = os.getenv(key)
        if not value:
            raise EnvironmentError(
                f"{key} is not set. Add it to your .env file (APP_ENV='{app_env}')."
            )
        values[key] = value

    return {
        "host": values["DB_HOST"],
        "port": values["DB_PORT"],
        "dbname": values["DB_NAME"],
        "user": values["DB_USER"],
        "password": values["DB_PASSWORD"],
    }


@contextmanager
def get_connection():
    """Yields a psycopg2 connection, committing on success and rolling back on error."""
    conn = psycopg2.connect(**_db_config())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
