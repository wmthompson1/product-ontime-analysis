#!/usr/bin/env python3
"""
graph_metadata_queries.py — SQLite connection wrapper for manufacturing.db metadata.

Provides a path resolver and a single query function that returns a pandas DataFrame.
All queries are expected to be pre-built SQL strings from metadata_query_templates.py.

Usage (from private repo with PYTHONPATH set to cloned public repo root):
    from replit_integrations.graph_metadata_queries import get_graph_metadata
    from replit_integrations.metadata_query_templates import list_perspectives

    df = get_graph_metadata(list_perspectives())
    print(df)
"""
import os
import sqlite3

import pandas as pd


_DEFAULT_DB_RELATIVE = os.path.join(
    "hf-space-inventory-sqlgen", "app_schema", "manufacturing.db"
)


def get_manufacturing_db_path() -> str:
    """Resolve the path to manufacturing.db.

    Resolution order:
    1. ``SQLITE_DB_PATH`` environment variable (absolute or relative path).
    2. Relative fallback: ``hf-space-inventory-sqlgen/app_schema/manufacturing.db``
       resolved from the current working directory.

    Returns:
        Absolute path string to manufacturing.db.

    Raises:
        FileNotFoundError: If the resolved path does not exist on disk.
    """
    env_path = os.environ.get("SQLITE_DB_PATH")
    if env_path:
        resolved = os.path.abspath(env_path)
    else:
        resolved = os.path.abspath(_DEFAULT_DB_RELATIVE)

    if not os.path.exists(resolved):
        raise FileNotFoundError(
            f"manufacturing.db not found at '{resolved}'. "
            "Set the SQLITE_DB_PATH environment variable to the correct path, "
            "or run from the repo root so the relative fallback resolves correctly."
        )
    return resolved


def get_graph_metadata(
    query: str,
    params=None,
    db_path: str = None,
) -> pd.DataFrame:
    """Execute a SQL query against manufacturing.db and return the result as a DataFrame.

    Opens a new SQLite connection per call (connection-per-call pattern — no persistent
    state), executes the query, and closes the connection before returning.

    Args:
        query:   A valid SQL SELECT string. Use pre-built strings from
                 ``metadata_query_templates`` rather than writing raw SQL here.
        params:  Optional sequence or dict of bind parameters passed directly to
                 ``pd.read_sql_query`` (uses ``?`` placeholders for positional,
                 ``:name`` for named).
        db_path: Absolute path to manufacturing.db. When ``None`` the path is
                 resolved by :func:`get_manufacturing_db_path`.

    Returns:
        pandas.DataFrame with one row per result row.  Returns an empty DataFrame
        (with column names) if the query matches no rows.

    Raises:
        FileNotFoundError:       If the database file cannot be located.
        sqlite3.OperationalError: If the SQL is invalid or references unknown tables /
                                  columns.  The original SQLite error message is
                                  preserved in the exception.
    """
    if db_path is None:
        db_path = get_manufacturing_db_path()

    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(query, conn, params=params)
    except sqlite3.OperationalError:
        raise
    finally:
        conn.close()

    return df


def close_connection() -> None:
    """Resource cleanup stub.

    This module uses a connection-per-call pattern: each :func:`get_graph_metadata`
    call opens and closes its own connection.  There is no shared persistent
    connection to clean up.  This function exists as a placeholder so callers that
    follow a connect/query/close lifecycle pattern compile without modification.
    """
