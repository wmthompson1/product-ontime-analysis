"""masking_type.py — the masking-type reference lookup, kept in sync between a
root CSV and SQLite.

A small closed lookup that maps each ``masking_type`` to its numeric
``masking_mode`` (the mode recorded against each row of the masking_matrix) plus
a ``status`` so a type can be retired without being deleted. Like the masking
matrix, it lives in two places kept in agreement:

  - a human-editable CSV at the repo root: ``masking_type.csv``
  - the SQLite ``masking_type`` table (the queryable runtime copy)

``load_types_from_csv`` (CSV -> SQLite) and ``export_types_to_csv`` (SQLite ->
CSV) keep the two copies in sync; both are idempotent. ``replace_types`` is the
UI save path: replace the table from the edited rows, then mirror to the CSV (the
SME-facing copy). There is no LLM anywhere on this surface.

Columns (the closed CSV schema, in order):
  masking_type, masking_mode, status

This module mirrors ``masking_matrix.py``'s CSV<->SQLite plumbing and is
self-contained so it can be imported by ``app.py`` (sync on startup) or run from
a head-less script without importing the full FastAPI/Gradio app.
"""
from __future__ import annotations

import csv
import os
import sqlite3
import tempfile
from typing import Any, Dict, List, Optional

# Reuse the canonical manufacturing.db location.
from field_description_pipeline import DEFAULT_DB_PATH  # noqa: E402

_HF_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HF_DIR)

# The root-level CSV that mirrors the masking_type table.
DEFAULT_CSV_PATH = os.path.join(_REPO_ROOT, "masking_type.csv")

# The CSV column order — also the table's user-facing column order.
TYPE_COLUMNS: tuple = ("masking_type", "masking_mode", "status")

# Closed status vocabulary (matches the SQLite CHECK). 'active' means the type may
# be assigned in the matrix; 'inactive' retires it without deleting it.
TYPE_STATUSES: tuple = ("active", "inactive")

# Kept textually identical to the guard in app.py and app_schema/schema_sqlite.sql.
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS masking_type (
    masking_type TEXT    NOT NULL PRIMARY KEY,
    masking_mode INTEGER NOT NULL DEFAULT 0,
    status       TEXT    NOT NULL DEFAULT 'active'
        CHECK(status IN ('active', 'inactive'))
)
"""

# The curated default lookup (used to (re)create the CSV if it is missing).
DEFAULT_TYPES: List[Dict[str, Any]] = [
    {"masking_type": "deterministic_hash", "masking_mode": 1, "status": "active"},
    {"masking_type": "change to null", "masking_mode": 2, "status": "active"},
    {"masking_type": "obfuscate binary text", "masking_mode": 3, "status": "active"},
]


# ── helpers ─────────────────────────────────────────────────────────────────


def ensure_table(conn: sqlite3.Connection) -> None:
    """Create the masking_type table if missing."""
    conn.execute(CREATE_TABLE_SQL)


def _to_int(value: Any, default: int) -> int:
    """Coerce a CSV/grid cell to int, tolerating '30' / '30.0' / '' / junk."""
    s = str(value if value is not None else "").strip()
    if not s:
        return default
    try:
        return int(s)
    except ValueError:
        try:
            return int(float(s))
        except ValueError:
            return default


def _clean_row(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize one CSV/DB row. Returns None for a row with no masking_type."""
    def g(name: str) -> str:
        return str(raw.get(name) or "").strip()

    masking_type = g("masking_type")
    if not masking_type:
        return None

    masking_mode = _to_int(g("masking_mode"), 0)
    if masking_mode < 0:
        masking_mode = 0

    status = g("status").lower() or "active"
    if status not in TYPE_STATUSES:
        status = "active"

    return {
        "masking_type": masking_type,
        "masking_mode": masking_mode,
        "status": status,
    }


def read_csv_rows(csv_path: str = DEFAULT_CSV_PATH) -> List[Dict[str, Any]]:
    """Read + normalize the lookup CSV. Returns [] if the file is absent."""
    if not os.path.exists(csv_path):
        return []
    rows: List[Dict[str, Any]] = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for raw in csv.DictReader(fh):
            cleaned = _clean_row(raw)
            if cleaned is not None:
                rows.append(cleaned)
    return rows


# ── sync: CSV → SQLite ──────────────────────────────────────────────────────


def load_types_from_csv(
    csv_path: str = DEFAULT_CSV_PATH, db_path: str = DEFAULT_DB_PATH
) -> Dict[str, Any]:
    """Upsert every CSV row into the SQLite ``masking_type`` table (by type).

    Idempotent: re-running refreshes existing rows in place and inserts new ones.
    Returns ``{"ok", "loaded"}`` (rows upserted) or ``{"ok": False, "error"}``.
    """
    rows = read_csv_rows(csv_path)
    conn = sqlite3.connect(db_path)
    try:
        ensure_table(conn)
        for r in rows:
            conn.execute(
                """
                INSERT INTO masking_type (masking_type, masking_mode, status)
                VALUES (?, ?, ?)
                ON CONFLICT(masking_type) DO UPDATE SET
                    masking_mode = excluded.masking_mode,
                    status       = excluded.status
                """,
                (r["masking_type"], r["masking_mode"], r["status"]),
            )
        conn.commit()
        return {"ok": True, "loaded": len(rows)}
    except sqlite3.Error as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()


# ── read + sync: SQLite → CSV ───────────────────────────────────────────────


def read_types(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Return every lookup row as a dict, ordered by mode then type name."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        ensure_table(conn)
        rows = conn.execute(
            f"SELECT {', '.join(TYPE_COLUMNS)} FROM masking_type "
            "ORDER BY masking_mode, masking_type"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def export_types_to_csv(
    db_path: str = DEFAULT_DB_PATH, csv_path: str = DEFAULT_CSV_PATH
) -> int:
    """Write the SQLite lookup back out to the CSV. Atomic write. Returns rows."""
    rows = read_types(db_path)
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=os.path.dirname(os.path.abspath(csv_path)), suffix=".csv.tmp"
    )
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(TYPE_COLUMNS))
            writer.writeheader()
            for r in rows:
                writer.writerow({c: r.get(c, "") for c in TYPE_COLUMNS})
        os.replace(tmp, csv_path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return len(rows)


def replace_types(
    rows: List[Dict[str, Any]],
    db_path: str = DEFAULT_DB_PATH,
    csv_path: str = DEFAULT_CSV_PATH,
) -> Dict[str, Any]:
    """Replace the whole masking_type table with *rows*, then mirror to the CSV.

    The UI save path. Rows without a masking_type are dropped; a duplicate
    masking_type (the primary key) is rejected; an all-empty input is refused so
    the lookup is never silently wiped. On success the table is replaced in one
    transaction and the CSV rewritten. Returns
    ``{"ok", "saved", "csv_written", "csv_path"}``.
    """
    cleaned: List[Dict[str, Any]] = []
    seen = set()
    for raw in rows or []:
        c = _clean_row(raw)
        if c is None:
            continue
        if c["masking_type"] in seen:
            return {"ok": False, "error": f"duplicate masking_type '{c['masking_type']}'"}
        seen.add(c["masking_type"])
        cleaned.append(c)
    if not cleaned:
        return {"ok": False, "error": "refusing to save an empty masking_type table"}
    conn = sqlite3.connect(db_path)
    try:
        ensure_table(conn)
        conn.execute("DELETE FROM masking_type")
        for r in cleaned:
            conn.execute(
                "INSERT INTO masking_type (masking_type, masking_mode, status) "
                "VALUES (?, ?, ?)",
                (r["masking_type"], r["masking_mode"], r["status"]),
            )
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()
    written = export_types_to_csv(db_path=db_path, csv_path=csv_path)
    return {"ok": True, "saved": len(cleaned), "csv_written": written, "csv_path": csv_path}


def write_default_csv(csv_path: str = DEFAULT_CSV_PATH) -> int:
    """(Re)create the CSV from ``DEFAULT_TYPES``. Returns rows written."""
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(TYPE_COLUMNS))
        writer.writeheader()
        for r in DEFAULT_TYPES:
            writer.writerow({c: r.get(c, "") for c in TYPE_COLUMNS})
    return len(DEFAULT_TYPES)


def count_rows(db_path: str = DEFAULT_DB_PATH) -> int:
    """Return the number of rows in the masking_type table."""
    conn = sqlite3.connect(db_path)
    try:
        ensure_table(conn)
        return conn.execute("SELECT COUNT(*) FROM masking_type").fetchone()[0]
    finally:
        conn.close()


__all__ = [
    "TYPE_COLUMNS",
    "TYPE_STATUSES",
    "DEFAULT_CSV_PATH",
    "DEFAULT_DB_PATH",
    "DEFAULT_TYPES",
    "CREATE_TABLE_SQL",
    "ensure_table",
    "read_csv_rows",
    "load_types_from_csv",
    "read_types",
    "export_types_to_csv",
    "replace_types",
    "write_default_csv",
    "count_rows",
]
