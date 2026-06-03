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


def get_table_columns(
    table_name: str,
    db_path: str = None,
) -> "pd.DataFrame":
    """Return column metadata for a table via PRAGMA table_info().

    SQLite has no ``information_schema``.  This function is the canonical
    replacement: it calls ``PRAGMA table_info(<table>)`` and returns the
    result as a DataFrame with human-readable column names.

    Args:
        table_name: Physical table name in manufacturing.db.
        db_path:    Absolute path to manufacturing.db.  When ``None`` the
                    path is resolved by :func:`get_manufacturing_db_path`.

    Returns:
        DataFrame with columns:
            cid           – 0-based column index
            name          – column name
            type          – declared type (TEXT / INTEGER / REAL / BLOB / …)
            notnull       – 1 if NOT NULL constraint present, else 0
            default_value – default expression, or None
            pk            – 1 if column is part of the PRIMARY KEY, else 0

    Raises:
        FileNotFoundError:        If the database file cannot be located.
        sqlite3.OperationalError: If the table does not exist.
    """
    if db_path is None:
        db_path = get_manufacturing_db_path()

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        if not rows:
            raise sqlite3.OperationalError(
                f"PRAGMA table_info returned no rows for table '{table_name}'. "
                "Check that the table exists."
            )
        df = pd.DataFrame(
            rows,
            columns=["cid", "name", "type", "notnull", "default_value", "pk"],
        )
    finally:
        conn.close()

    return df


def get_table_foreign_keys(
    table_name: str,
    db_path: str = None,
) -> "pd.DataFrame":
    """Return foreign-key constraints for a table via PRAGMA foreign_key_list().

    SQLite stores FK metadata in PRAGMA, not in information_schema.
    Returns an empty DataFrame (with column names) when the table has no FKs.

    Args:
        table_name: Physical table name in manufacturing.db.
        db_path:    Absolute path to manufacturing.db.  When ``None`` the
                    path is resolved by :func:`get_manufacturing_db_path`.

    Returns:
        DataFrame with columns:
            fk_id       – FK constraint index (0-based, per SQLite)
            seq         – column sequence within the FK (for composite FKs)
            ref_table   – referenced (parent) table name
            from_col    – column in this table that carries the FK value
            to_col      – column in the parent table being referenced
            on_update   – referential action on UPDATE (NO ACTION / CASCADE / …)
            on_delete   – referential action on DELETE
            match       – MATCH clause (NONE for most SQLite FKs)

    Raises:
        FileNotFoundError:        If the database file cannot be located.
        sqlite3.OperationalError: If the table does not exist.
    """
    if db_path is None:
        db_path = get_manufacturing_db_path()

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()
        df = pd.DataFrame(
            rows,
            columns=["fk_id", "seq", "ref_table", "from_col", "to_col",
                     "on_update", "on_delete", "match"],
        )
    finally:
        conn.close()

    return df


def get_all_table_names(
    include_views: bool = False,
    db_path: str = None,
) -> "pd.DataFrame":
    """Return every physical table name from sqlite_master.

    Uses ``sqlite_master`` (the SQLite equivalent of
    ``information_schema.tables``) rather than PRAGMA so the result
    flows through the standard :func:`get_graph_metadata` path.

    Args:
        include_views: When ``True`` also return rows with type='view'.
        db_path:       Absolute path to manufacturing.db.

    Returns:
        DataFrame with columns:
            name  – table (or view) name
            type  – 'table' or 'view'
            sql   – the original CREATE TABLE / CREATE VIEW statement
    """
    types = "('table', 'view')" if include_views else "('table')"
    query = (
        f"SELECT name, type, sql FROM sqlite_master "
        f"WHERE type IN {types} AND name NOT LIKE 'sqlite_%' "
        f"ORDER BY name"
    )
    return get_graph_metadata(query, db_path=db_path)


def get_table_index_info(
    table_name: str,
    db_path: str = None,
) -> "pd.DataFrame":
    """Return index metadata for a table via PRAGMA index_list() + index_info().

    Args:
        table_name: Physical table name in manufacturing.db.
        db_path:    Absolute path to manufacturing.db.

    Returns:
        DataFrame with columns:
            index_name  – index name (auto-named or user-defined)
            unique      – 1 if unique index, else 0
            col_rank    – ordinal position of column within the index
            col_name    – column name covered by the index
    """
    if db_path is None:
        db_path = get_manufacturing_db_path()

    conn = sqlite3.connect(db_path)
    try:
        indexes = conn.execute(f"PRAGMA index_list({table_name})").fetchall()
        rows = []
        for idx in indexes:
            idx_name, unique = idx[1], idx[2]
            cols = conn.execute(f"PRAGMA index_info({idx_name})").fetchall()
            for col in cols:
                rows.append((idx_name, unique, col[0], col[2]))
        df = pd.DataFrame(rows, columns=["index_name", "unique", "col_rank", "col_name"])
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
