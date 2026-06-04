"""
metadata_query_templates.py
===========================
Canned, parameterised SQLite metadata queries for the manufacturing semantic layer.

All functions accept an explicit connection or path so they can be called from
tests without side effects.  No module-level I/O is performed.

Functions
---------
get_column_info(conn, table_name)
    Returns PRAGMA table_info rows for the given table as a list of dicts.

get_schema_tables(conn)
    Returns all table names registered in the schema_nodes table.

get_ground_truth_bindings(manifest_path)
    Returns approved binding rows parsed from the reviewer_manifest.json.
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Column info
# ---------------------------------------------------------------------------

def get_column_info(conn: sqlite3.Connection, table_name: str) -> List[Dict[str, Any]]:
    """Return PRAGMA table_info rows for *table_name* as a list of dicts.

    Each dict contains:
        column_name : str   — column name (original case from PRAGMA)
        data_type   : str   — declared type string, e.g. "TEXT", "INTEGER"
        pk          : bool  — True when the column is part of the primary key
        notnull     : bool  — True when the column has a NOT NULL constraint

    Returns an empty list when the table does not exist or has no columns.

    Parameters
    ----------
    conn:
        An open ``sqlite3.Connection`` (or duck-typed equivalent).
    table_name:
        The exact table name as stored in SQLite's catalog (case-sensitive in
        PRAGMA, but SQLite itself is case-insensitive for table names).
    """
    try:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    except Exception:
        return []

    result: List[Dict[str, Any]] = []
    for row in rows:
        if isinstance(row, sqlite3.Row):
            name = row["name"]
            col_type = row["type"] or "TEXT"
            pk = bool(row["pk"])
            notnull = bool(row["notnull"])
        else:
            _, name, col_type, notnull_raw, _, pk_raw = row
            col_type = col_type or "TEXT"
            pk = bool(pk_raw)
            notnull = bool(notnull_raw)

        result.append(
            {
                "column_name": name,
                "data_type": col_type,
                "pk": pk,
                "notnull": notnull,
            }
        )
    return result


# ---------------------------------------------------------------------------
# Schema tables
# ---------------------------------------------------------------------------

def get_schema_tables(conn: sqlite3.Connection) -> List[str]:
    """Return all table names from the *schema_nodes* table.

    Only rows where ``table_type = 'Table'`` are returned (views and other
    node types are excluded).

    Parameters
    ----------
    conn:
        An open ``sqlite3.Connection``.
    """
    try:
        rows = conn.execute(
            "SELECT table_name FROM schema_nodes WHERE table_type = 'Table' ORDER BY table_name"
        ).fetchall()
    except Exception:
        return []

    if rows and isinstance(rows[0], sqlite3.Row):
        return [r["table_name"] for r in rows]
    return [r[0] for r in rows]


# ---------------------------------------------------------------------------
# Ground truth bindings
# ---------------------------------------------------------------------------

def get_ground_truth_bindings(manifest_path: str) -> List[Dict[str, Any]]:
    """Return approved binding rows from the reviewer manifest JSON.

    Each dict contains:
        binding_key    : str  — unique key for the binding
        perspective    : str  — perspective name (e.g. "Quality")
        concept_anchor : str  — concept anchor string (e.g. "DEFECTSEVERITYQUALITY")
        file_path      : str  — relative path to the approved SQL snippet file
        logic_type     : str  — e.g. "DIRECT"

    Only entries where ``validation_status == "APPROVED"`` are returned.

    Parameters
    ----------
    manifest_path:
        Filesystem path to ``reviewer_manifest.json``.
    """
    if not os.path.exists(manifest_path):
        return []

    try:
        with open(manifest_path, "r") as fh:
            manifest = json.load(fh)
    except Exception:
        return []

    snippets = manifest.get("approved_snippets", {})
    result: List[Dict[str, Any]] = []

    for binding_key, entry in snippets.items():
        if entry.get("validation_status") != "APPROVED":
            continue
        result.append(
            {
                "binding_key": binding_key,
                "perspective": entry.get("perspective", ""),
                "concept_anchor": entry.get("concept_anchor", ""),
                "file_path": entry.get("file_path", ""),
                "logic_type": entry.get("logic_type", "DIRECT"),
            }
        )

    return result
