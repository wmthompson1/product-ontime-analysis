"""Table-level meta-context overlay (api_table_descriptions).

This is the table-grain sibling of ``field_description_pipeline.py``. A metric is
a *semantic* node (a concept), and the AI needs business meta-context about the
physical tables a metric draws from — what the table records, its grain, and how
it participates in metrics — to reason about and explain a metric.

That meta-context lives in an SME-editable, committed CSV at the repo root
(``table_descriptions.csv``) which is upserted into the ``api_table_descriptions``
SQLite overlay on every boot (same pattern as masking_matrix.csv and
field_descriptions.csv). It is an OVERLAY ONLY: it is NEVER written onto the
physical table/column nodes of the canonical graph, so ``graph_metadata.json``
stays byte-identical. AI spend (if any) happens once when authoring the CSV,
never per-boot.
"""

import csv
import os
import sqlite3
import tempfile
from typing import Any, Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
DEFAULT_DB_PATH = os.path.join(_HERE, "app_schema", "manufacturing.db")

# Committed, SME-facing, version-controlled copy. Survives a gitignored-DB
# rebuild and is re-applied on every boot.
DEFAULT_CSV_PATH = os.path.join(_REPO_ROOT, "table_descriptions.csv")

# CSV column order (also the user-facing column order).
CSV_COLUMNS: Tuple[str, ...] = (
    "table_name",
    "display_name",
    "description",
    "ai_context",
)

# Must match app.py SQL_MCP_SOURCE_DATABASE / _DEFAULT_SCHEMA so the overlay
# lookups line up with api_field_descriptions.
SOURCE_DATABASE = os.environ.get("SQL_MCP_SOURCE_DATABASE", "manufacturing")
SCHEMA_NAME = os.environ.get("SQL_MCP_DEFAULT_SCHEMA", "dbo")

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS api_table_descriptions (
    source_database TEXT    NOT NULL,
    schema_name     TEXT    NOT NULL,
    table_name      TEXT    NOT NULL,
    display_name    TEXT,
    description     TEXT,
    ai_context      TEXT,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_database, schema_name, table_name)
)
"""


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def read_descriptions_csv(csv_path: str = DEFAULT_CSV_PATH) -> List[Dict[str, str]]:
    """Read the table-descriptions CSV. Returns [] if the file is absent."""
    if not os.path.exists(csv_path):
        return []
    out: List[Dict[str, str]] = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for raw in csv.DictReader(fh):
            tbl = (raw.get("table_name") or "").strip()
            if not tbl:
                continue
            out.append({
                "table_name": tbl,
                "display_name": (raw.get("display_name") or "").strip(),
                "description": (raw.get("description") or "").strip(),
                "ai_context": (raw.get("ai_context") or "").strip(),
            })
    return out


def write_descriptions_csv(
    rows: List[Dict[str, str]],
    csv_path: str = DEFAULT_CSV_PATH,
) -> int:
    """Write rows to the CSV (atomic), sorted by table_name."""
    ordered = sorted(rows, key=lambda r: r["table_name"])
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=os.path.dirname(os.path.abspath(csv_path)), suffix=".csv.tmp"
    )
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(CSV_COLUMNS))
            writer.writeheader()
            for r in ordered:
                writer.writerow({c: r.get(c, "") for c in CSV_COLUMNS})
        os.replace(tmp, csv_path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return len(ordered)


def upsert_table_description(
    table: str,
    display_name: Optional[str],
    description: Optional[str],
    ai_context: Optional[str],
    db_path: str = DEFAULT_DB_PATH,
    source_database: str = SOURCE_DATABASE,
    schema_name: str = SCHEMA_NAME,
) -> Dict[str, Any]:
    """Idempotent upsert into ``api_table_descriptions``."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(_CREATE_SQL)
        conn.execute(
            """
            INSERT INTO api_table_descriptions
                (source_database, schema_name, table_name,
                 display_name, description, ai_context, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(source_database, schema_name, table_name)
            DO UPDATE SET
                display_name = excluded.display_name,
                description  = excluded.description,
                ai_context   = excluded.ai_context,
                updated_at   = CURRENT_TIMESTAMP
            """,
            (source_database, schema_name, table,
             display_name, description, ai_context),
        )
        conn.commit()
        return {"ok": True}
    except sqlite3.Error as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()


def get_table_description(
    table: str,
    db_path: str = DEFAULT_DB_PATH,
    source_database: str = SOURCE_DATABASE,
    schema_name: str = SCHEMA_NAME,
) -> Dict[str, Any]:
    """Return the api_table_descriptions row for a table, or {} if absent."""
    if not table:
        return {}
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT display_name, description, ai_context "
            "FROM api_table_descriptions "
            "WHERE source_database=? AND schema_name=? AND table_name=?",
            (source_database, schema_name, table),
        ).fetchone()
        return dict(row) if row else {}
    except sqlite3.Error:
        return {}
    finally:
        conn.close()


def load_descriptions_from_csv(
    csv_path: str = DEFAULT_CSV_PATH,
    db_path: str = DEFAULT_DB_PATH,
    source_database: str = SOURCE_DATABASE,
    schema_name: str = SCHEMA_NAME,
) -> Dict[str, Any]:
    """Upsert every CSV row into ``api_table_descriptions`` (idempotent).

    Mirrors the field-descriptions boot sync: the committed CSV is the SME-facing
    source of truth, re-applied on every boot so the meta-context survives a
    gitignored-DB rebuild. Returns ``{"ok", "loaded"}`` or an error.
    """
    rows = read_descriptions_csv(csv_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(_CREATE_SQL)
        for r in rows:
            conn.execute(
                """
                INSERT INTO api_table_descriptions
                    (source_database, schema_name, table_name,
                     display_name, description, ai_context, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(source_database, schema_name, table_name)
                DO UPDATE SET
                    display_name = excluded.display_name,
                    description  = excluded.description,
                    ai_context   = excluded.ai_context,
                    updated_at   = CURRENT_TIMESTAMP
                """,
                (source_database, schema_name, r["table_name"],
                 r["display_name"], r["description"], r["ai_context"]),
            )
        conn.commit()
        return {"ok": True, "loaded": len(rows)}
    except sqlite3.Error as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()
