import os

def getenv_compat(new_name, old_name=None, default=None):
    v = os.getenv(new_name)
    if v:
        return v
    if old_name:
        return os.getenv(old_name, default)
    return default

SQLITE_DB_PATH = os.getenv(
    "SQLITE_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "hf-space-inventory-sqlgen", "app_schema", "manufacturing.db")
)

SQLALCHEMY_DATABASE_URI = f"sqlite:///{SQLITE_DB_PATH}"

ARANGO_URL = getenv_compat("ARANGO_URL", default=None)
ARANGO_ROOT_PASSWORD = getenv_compat("ARANGO_ROOT_PASSWORD", default="arangopass")
ARANGO_HOST = getenv_compat("ARANGO_HOST", default="127.0.0.1")
ARANGO_PORT = int(getenv_compat("ARANGO_PORT", default=8529))
ARANGO_DB = getenv_compat("ARANGO_DB")
