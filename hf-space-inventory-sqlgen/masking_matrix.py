"""masking_matrix.py — the column-masking DAG matrix, kept in sync between a root
CSV and SQLite.

The masking matrix records the *deterministic* masking applied to each column as
data flows through the SQLMesh DAG, from the synthetic twin into the pre-stage
server. It is intentionally separate from ``column_masking_policies`` (the SME
strategy/rationale authoring surface) — the two live side by side.

The matrix lives in two places that stay in sync:

  - a human-editable CSV at the repo root: ``masking_matrix.csv``
  - the SQLite ``masking_matrix`` table (the queryable runtime copy)

The CSV is the authored "certificate": once a row's data has been pulled into
SQLMesh from the twin, its ``status`` is set to ``static`` / ``complete`` (locked
/ certified). Rows still being worked are ``active``. ``load_matrix_from_csv``
(CSV → SQLite) and ``export_matrix_to_csv`` (SQLite → CSV) keep the two copies in
agreement; both are idempotent. There is no LLM anywhere on this surface.

Columns (the closed CSV schema, in order):
  dag_no, table_name, column_name, parent_table, parent_column, masking_rule,
  masking_type, field_length, masking_mode, pre_stage_server, status

``dag_no`` is the DAG node id and the table's primary key; ``parent_table`` /
``parent_column`` carry the lineage between nodes. ``field_length`` is the
column's width in the schema — the masked value is truncated to it so it stays
the same width as the field (0 = unbounded -> full 64-char digest). Because the
matrix's columns belong to the private SQL Server schema (not this local SQLite
twin), that width is carried here as data rather than resolved from a live schema.

This module is self-contained (its own sqlite + csv helpers) so it can be
imported by ``app.py`` to keep the table in sync on startup and run head-less by
a seed/CI script without importing the full FastAPI/Gradio app.
"""
from __future__ import annotations

import csv
import hashlib
import os
import sqlite3
import tempfile
from typing import Any, Dict, List, Optional

# Reuse the canonical manufacturing.db location.
from field_description_pipeline import DEFAULT_DB_PATH  # noqa: E402

_HF_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HF_DIR)

# The root-level CSV that mirrors the masking_matrix table (the SME-facing copy
# used for approval; the app can write it back).
DEFAULT_CSV_PATH = os.path.join(_REPO_ROOT, "masking_matrix.csv")

# The CSV column order — also the table's user-facing column order.
MATRIX_COLUMNS: tuple = (
    "dag_no",
    "table_name",
    "column_name",
    "parent_table",
    "parent_column",
    "masking_rule",
    "masking_type",
    "field_length",
    "masking_mode",
    "pre_stage_server",
    "status",
)

# Closed status vocabulary (matches the SQLite CHECK). ``static`` / ``complete``
# mean the row is certified / locked (data already pulled into SQLMesh);
# ``active`` means still in progress.
MATRIX_STATUSES: tuple = ("active", "static", "complete")

# Columns that are required (NOT NULL) and the empty-string-defaulted text cols.
_TEXT_COLS = (
    "column_name", "parent_table", "parent_column",
    "masking_rule", "masking_type", "pre_stage_server",
)

# Kept textually identical to the guard in app.py (ensure_app_metadata_tables)
# and to app_schema/schema_sqlite.sql.
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS masking_matrix (
    dag_no           TEXT    NOT NULL PRIMARY KEY,
    table_name       TEXT    NOT NULL,
    column_name      TEXT    NOT NULL DEFAULT '',
    parent_table     TEXT    NOT NULL DEFAULT '',
    parent_column    TEXT    NOT NULL DEFAULT '',
    masking_rule     TEXT,
    masking_type     TEXT,
    field_length     INTEGER NOT NULL DEFAULT 0,
    masking_mode     INTEGER NOT NULL DEFAULT 1,
    pre_stage_server TEXT,
    status           TEXT    NOT NULL DEFAULT 'active'
        CHECK(status IN ('active', 'static', 'complete'))
)
"""

# The curated default matrix (used to (re)create the CSV if it is missing).
DEFAULT_MATRIX: List[Dict[str, Any]] = [
    {"dag_no": "1.1", "table_name": "vendor", "column_name": "id",
     "parent_table": "", "parent_column": "",
     "masking_rule": "hash_sha256(id,length)",
     "masking_type": "deterministic_hash", "field_length": 30, "masking_mode": 1,
     "pre_stage_server": "sql-lab-2", "status": "static"},
    {"dag_no": "1.2", "table_name": "part", "column_name": "pref_vendor",
     "parent_table": "vendor", "parent_column": "id",
     "masking_rule": "hash_sha256(pref_vendor,length)",
     "masking_type": "deterministic_hash", "field_length": 30, "masking_mode": 1,
     "pre_stage_server": "sql-lab-2", "status": "static"},
    {"dag_no": "1.3", "table_name": "work_order", "column_name": "part_id",
     "parent_table": "part", "parent_column": "id",
     "masking_rule": "hash_sha256(id,length)",
     "masking_type": "deterministic_hash", "field_length": 30, "masking_mode": 1,
     "pre_stage_server": "sql-lab-2", "status": "static"},
    {"dag_no": "2.0", "table_name": "user_def_fields", "column_name": "",
     "parent_table": "", "parent_column": "",
     "masking_rule": "hash_sha256(id,length)",
     "masking_type": "deterministic_hash", "field_length": 0, "masking_mode": 1,
     "pre_stage_server": "sql-lab-2", "status": "active"},
]


# ── helpers ─────────────────────────────────────────────────────────────────


def ensure_table(conn: sqlite3.Connection) -> None:
    """Create the masking_matrix table if missing; self-heal older tables.

    ``CREATE TABLE IF NOT EXISTS`` is a no-op when the table already exists, so a
    column added after a DB was first created (``field_length``) is back-filled
    here with an idempotent ``ALTER TABLE ADD COLUMN``.
    """
    conn.execute(CREATE_TABLE_SQL)
    existing = {row[1] for row in conn.execute("PRAGMA table_info(masking_matrix)")}
    if "field_length" not in existing:
        conn.execute(
            "ALTER TABLE masking_matrix ADD COLUMN field_length INTEGER NOT NULL DEFAULT 0"
        )


def _dag_sort_key(dag_no: str):
    """Numeric-aware sort key so '1.2' sorts before '1.10' and '2.0'."""
    parts = []
    for piece in str(dag_no or "").split("."):
        parts.append((0, int(piece)) if piece.isdigit() else (1, piece))
    return parts


def _to_int(value: Any, default: int) -> int:
    """Coerce a CSV/grid cell to int, tolerating '30' / '30.0' / '' / junk.

    The grid editor can hand back floats (``30.0``) or blanks for the numeric
    columns, so plain ``int(str)`` is not enough.
    """
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
    """Normalize one CSV/DB row into the canonical typed shape.

    Trims whitespace on every field, coerces ``masking_mode``/``field_length`` to
    int (defaults 1 / 0; ``field_length`` is clamped to >= 0),
    defaults blank required text columns to '', and coerces an unknown/blank
    ``status`` to 'active' so a hand-edited CSV never breaks the load. Returns
    ``None`` for a row with no ``dag_no`` (the primary key) — it is skipped.
    """
    def g(name: str) -> str:
        return str(raw.get(name) or "").strip()

    dag_no = g("dag_no")
    if not dag_no:
        return None

    masking_mode = _to_int(g("masking_mode"), 1)

    field_length = _to_int(g("field_length"), 0)
    if field_length < 0:
        field_length = 0

    status = g("status").lower() or "active"
    if status not in MATRIX_STATUSES:
        status = "active"

    return {
        "dag_no": dag_no,
        "table_name": g("table_name"),
        "column_name": g("column_name"),
        "parent_table": g("parent_table"),
        "parent_column": g("parent_column"),
        "masking_rule": g("masking_rule"),
        "masking_type": g("masking_type"),
        "field_length": field_length,
        "masking_mode": masking_mode,
        "pre_stage_server": g("pre_stage_server"),
        "status": status,
    }


def read_csv_rows(csv_path: str = DEFAULT_CSV_PATH) -> List[Dict[str, Any]]:
    """Read + normalize the matrix CSV. Returns [] if the file is absent."""
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


def load_matrix_from_csv(
    csv_path: str = DEFAULT_CSV_PATH, db_path: str = DEFAULT_DB_PATH
) -> Dict[str, Any]:
    """Upsert every CSV row into the SQLite ``masking_matrix`` table (by dag_no).

    Idempotent: re-running refreshes existing rows in place and inserts new ones,
    keyed on ``dag_no``. Returns ``{"ok", "loaded"}`` (rows upserted) or an error.
    """
    rows = read_csv_rows(csv_path)
    conn = sqlite3.connect(db_path)
    try:
        ensure_table(conn)
        for r in rows:
            conn.execute(
                """
                INSERT INTO masking_matrix
                    (dag_no, table_name, column_name, parent_table, parent_column,
                     masking_rule, masking_type, field_length, masking_mode,
                     pre_stage_server, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(dag_no) DO UPDATE SET
                    table_name       = excluded.table_name,
                    column_name      = excluded.column_name,
                    parent_table     = excluded.parent_table,
                    parent_column    = excluded.parent_column,
                    masking_rule     = excluded.masking_rule,
                    masking_type     = excluded.masking_type,
                    field_length     = excluded.field_length,
                    masking_mode     = excluded.masking_mode,
                    pre_stage_server = excluded.pre_stage_server,
                    status           = excluded.status
                """,
                (r["dag_no"], r["table_name"], r["column_name"], r["parent_table"],
                 r["parent_column"], r["masking_rule"], r["masking_type"],
                 r["field_length"], r["masking_mode"], r["pre_stage_server"],
                 r["status"]),
            )
        conn.commit()
        return {"ok": True, "loaded": len(rows)}
    except sqlite3.Error as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()


# ── read + sync: SQLite → CSV ───────────────────────────────────────────────


def read_matrix(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Return every matrix row as a dict, ordered by the DAG number."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        ensure_table(conn)
        rows = conn.execute(
            f"SELECT {', '.join(MATRIX_COLUMNS)} FROM masking_matrix"
        ).fetchall()
        out = [dict(r) for r in rows]
        out.sort(key=lambda r: _dag_sort_key(r["dag_no"]))
        return out
    finally:
        conn.close()


def export_matrix_to_csv(
    db_path: str = DEFAULT_DB_PATH, csv_path: str = DEFAULT_CSV_PATH
) -> int:
    """Write the SQLite matrix back out to the CSV (DAG order). Atomic write.

    Keeps the CSV consistent after programmatic edits to the table. Returns the
    number of rows written.
    """
    rows = read_matrix(db_path)
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=os.path.dirname(os.path.abspath(csv_path)), suffix=".csv.tmp"
    )
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(MATRIX_COLUMNS))
            writer.writeheader()
            for r in rows:
                writer.writerow({c: r.get(c, "") for c in MATRIX_COLUMNS})
        os.replace(tmp, csv_path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return len(rows)


def write_default_csv(csv_path: str = DEFAULT_CSV_PATH) -> int:
    """(Re)create the CSV from ``DEFAULT_MATRIX``. Returns rows written."""
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(MATRIX_COLUMNS))
        writer.writeheader()
        for r in DEFAULT_MATRIX:
            writer.writerow({c: r.get(c, "") for c in MATRIX_COLUMNS})
    return len(DEFAULT_MATRIX)


def count_rows(db_path: str = DEFAULT_DB_PATH) -> int:
    """Return the number of rows in the masking_matrix table."""
    conn = sqlite3.connect(db_path)
    try:
        ensure_table(conn)
        return conn.execute("SELECT COUNT(*) FROM masking_matrix").fetchone()[0]
    finally:
        conn.close()


# ── the deterministic masking transform (the matrix's hash_sha256 rule) ──────

# The env var (secret) that holds the masking salt. The salt stays in the
# environment / secret flow — it is never stored in the matrix, CSV, or code.
SALT_ENV_VAR = os.environ.get("MASK_SALT_ENV", "GEMIN_SALT")


def get_salt(salt: Optional[str] = None, salt_env: str = SALT_ENV_VAR) -> str:
    """Return the masking salt from the argument or the secret env var.

    Raises if neither is set — masking must never silently run unsalted.
    """
    resolved = salt if salt is not None else os.environ.get(salt_env)
    if not resolved:
        raise RuntimeError(
            f"Masking salt is required: pass salt=... or set the {salt_env} "
            f"secret (it lives in the environment / secret flow)."
        )
    return resolved


def hash_sha256(
    value: Any,
    length: int = 0,
    salt: Optional[str] = None,
    salt_env: str = SALT_ENV_VAR,
) -> Any:
    """The matrix's ``hash_sha256(col, length)`` rule, made executable.

    Deterministically masks *value*: ``SHA-256(value + salt)`` as an uppercase
    hex digest, then truncated to *length* characters so the masked value is the
    **same width as the field in the schema**. ``length <= 0`` returns the full
    64-char digest. NULL / empty values pass through unchanged (nothing to mask).
    The salt comes from the secret env flow (see ``get_salt``); the same value +
    salt + length always yields the same output, so masked keys stay joinable.
    """
    if value is None or value == "":
        return value
    resolved_salt = get_salt(salt, salt_env)
    digest = hashlib.sha256(
        f"{value}{resolved_salt}".encode("utf-8")
    ).hexdigest().upper()
    if length and length > 0:
        return digest[:length]
    return digest


def mask_row_value(
    row: Dict[str, Any],
    value: Any,
    salt: Optional[str] = None,
    salt_env: str = SALT_ENV_VAR,
) -> Any:
    """Mask *value* for a matrix *row*, sized to that row's schema width.

    This is the executable form of the row's ``hash_sha256(col, length)`` rule:
    ``length`` is the row's stored ``field_length`` (the column's width in the
    schema), so the masked output is the same width as the field. A
    ``field_length`` of 0 means unbounded -> the full 64-char digest. NULL /
    empty values pass through unchanged.
    """
    try:
        length = int(row.get("field_length") or 0)
    except (TypeError, ValueError):
        length = 0
    return hash_sha256(value, length, salt=salt, salt_env=salt_env)


# ── the UI save path: replace the table from edited rows, mirror to the CSV ──


def replace_matrix(
    rows: List[Dict[str, Any]],
    db_path: str = DEFAULT_DB_PATH,
    csv_path: str = DEFAULT_CSV_PATH,
) -> Dict[str, Any]:
    """Replace the entire ``masking_matrix`` table with *rows*, mirror to the CSV.

    The UI save path: *rows* come from the edited grid. Each is normalized via
    ``_clean_row`` (rows without a ``dag_no`` are dropped); a duplicate ``dag_no``
    (the primary key) is rejected; an all-empty input is refused so the matrix is
    never silently wiped. On success the table is replaced in a single
    transaction and the CSV — the SME-facing copy used for approval — is rewritten
    in DAG order. Returns ``{"ok", "saved", "csv_written", "csv_path"}`` or
    ``{"ok": False, "error"}``.
    """
    cleaned: List[Dict[str, Any]] = []
    seen = set()
    for raw in rows or []:
        c = _clean_row(raw)
        if c is None:
            continue
        if c["dag_no"] in seen:
            return {"ok": False, "error": f"duplicate dag_no '{c['dag_no']}'"}
        seen.add(c["dag_no"])
        cleaned.append(c)
    if not cleaned:
        return {
            "ok": False,
            "error": "refusing to save an empty matrix (no rows with a dag_no)",
        }
    conn = sqlite3.connect(db_path)
    try:
        ensure_table(conn)
        conn.execute("DELETE FROM masking_matrix")
        for r in cleaned:
            conn.execute(
                """
                INSERT INTO masking_matrix
                    (dag_no, table_name, column_name, parent_table, parent_column,
                     masking_rule, masking_type, field_length, masking_mode,
                     pre_stage_server, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (r["dag_no"], r["table_name"], r["column_name"], r["parent_table"],
                 r["parent_column"], r["masking_rule"], r["masking_type"],
                 r["field_length"], r["masking_mode"], r["pre_stage_server"],
                 r["status"]),
            )
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()
    written = export_matrix_to_csv(db_path=db_path, csv_path=csv_path)
    return {
        "ok": True,
        "saved": len(cleaned),
        "csv_written": written,
        "csv_path": csv_path,
    }


__all__ = [
    "MATRIX_COLUMNS",
    "MATRIX_STATUSES",
    "DEFAULT_CSV_PATH",
    "DEFAULT_DB_PATH",
    "DEFAULT_MATRIX",
    "CREATE_TABLE_SQL",
    "SALT_ENV_VAR",
    "ensure_table",
    "read_csv_rows",
    "load_matrix_from_csv",
    "read_matrix",
    "export_matrix_to_csv",
    "replace_matrix",
    "write_default_csv",
    "count_rows",
    "get_salt",
    "hash_sha256",
    "mask_row_value",
]
