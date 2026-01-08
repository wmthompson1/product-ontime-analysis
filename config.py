# small compatibility helper for env names
import os

def getenv_compat(new_name, old_name=None, default=None):
    v = os.getenv(new_name)
    if v:
        return v
    if old_name:
        return os.getenv(old_name, default)
    return default

# Postgres (explicit)
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("PGDATABASE_URL")

# Arango: prefer ARANGO_* but fall back to older 'database_' names if still present
ARANGO_URL = getenv_compat("ARANGO_URL", old_name="database_url", default=None)
ARANGO_ROOT_PASSWORD = getenv_compat("ARANGO_ROOT_PASSWORD", old_name="database_password", default="arangopass")
ARANGO_HOST = getenv_compat("ARANGO_HOST", old_name="database_host", default="127.0.0.1")
ARANGO_PORT = int(getenv_compat("ARANGO_PORT", old_name="database_port", default=8529))
ARANGO_DB = getenv_compat("ARANGO_DB", old_name="database_db", default="_system")