"""field_description_pipeline.py — draft + persist field descriptions (DAB stand-in).

The pipeline turns a structural column into a drafted field description
(display_name, description, example_value), persists it to
``api_field_descriptions``, and supports certifying it into
``dab_field_definitions`` — the local stand-in for the company DAB (Data Asset
Bundle / field dictionary).

Two draft modes:

  - **deterministic** (default): builds a draft from the column name, declared
    type, and a sample of distinct values read from the database. No API spend,
    works offline. This is the safe default for the project's cost-conscious
    preference.
  - **AI-assisted** (opt-in, explicit): when ``use_ai=True`` and
    ``OPENAI_API_KEY`` is set, asks OpenAI to write a richer plain-language
    description. Falls back to the deterministic draft on any error or missing
    key, so the pipeline never hard-fails on the AI path.

Persistence is idempotent: both tables use the four-column PK
(source_database, schema_name, table_name, column_name) and this module upserts.

This module is intentionally self-contained (its own sqlite helpers) so it can be
imported by ``app.py`` for the UI "Generate draft" action and run head-less by a
seed/fill script without importing the full FastAPI/Gradio app.
"""
from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(_HERE, "app_schema", "manufacturing.db")

# Must match app.py SQL_MCP_SOURCE_DATABASE / _DEFAULT_SCHEMA so the schema
# browser overlay and the SolderEngine lookup find these rows.
SOURCE_DATABASE = os.environ.get("SQL_MCP_SOURCE_DATABASE", "manufacturing")
SCHEMA_NAME = os.environ.get("SQL_MCP_DEFAULT_SCHEMA", "dbo")

# Internal infrastructure tables — never described as business columns.
_METADATA_TABLES = {
    "api_field_descriptions",
    "schema_topology_metadata",
    "dab_field_definitions",
    "column_bindings",
}

# Abbreviations expanded when humanizing a column/table name into a display name.
_ABBR = {
    "id": "ID", "qty": "Quantity", "po": "PO", "ncm": "NCM", "oee": "OEE",
    "cert": "Certification", "uom": "UoM", "sku": "SKU", "fk": "FK",
    "no": "No.", "num": "Number", "ts": "Timestamp", "dt": "Date",
}

# When the AI path is used, this model is the default (override via env).
_AI_MODEL = os.environ.get("FIELD_DESC_AI_MODEL", "gpt-4o-mini")

# Categorical heuristic: a column with at most this many distinct values is
# treated as a bounded categorical / status / type field (the semantic signal).
_CATEGORICAL_MAX_DISTINCT = 25


# ── name helpers ────────────────────────────────────────────────────────────


def humanize(name: str) -> str:
    """Turn a snake_case identifier into a Title Case display label."""
    cleaned = (name or "").replace("_", " ").strip()
    if not cleaned:
        return name or ""
    words = []
    for w in cleaned.split():
        words.append(_ABBR.get(w.lower(), w.capitalize()))
    return " ".join(words)


# ── sqlite read helpers ─────────────────────────────────────────────────────


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _column_meta(db_path: str, table: str, column: str) -> Optional[Dict[str, Any]]:
    conn = _connect(db_path)
    try:
        for r in conn.execute(f'PRAGMA table_info("{table}")').fetchall():
            if r["name"] == column:
                return {
                    "type": (r["type"] or ""),
                    "notnull": r["notnull"],
                    "pk": r["pk"],
                }
        return None
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def _sample_values(db_path: str, table: str, column: str, limit: int = 8) -> List[str]:
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            f'SELECT DISTINCT "{column}" AS v FROM "{table}" '
            f'WHERE "{column}" IS NOT NULL '
            f'  AND TRIM(CAST("{column}" AS TEXT)) <> "" '
            f"LIMIT ?",
            (limit,),
        ).fetchall()
        return [str(r["v"]) for r in rows]
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def _distinct_count(db_path: str, table: str, column: str) -> int:
    conn = _connect(db_path)
    try:
        r = conn.execute(
            f'SELECT COUNT(DISTINCT "{column}") AS c FROM "{table}"'
        ).fetchone()
        return int(r["c"]) if r and r["c"] is not None else 0
    except sqlite3.Error:
        return 0
    finally:
        conn.close()


# ── drafting ────────────────────────────────────────────────────────────────


def deterministic_draft(
    table: str, column: str, db_path: str = DEFAULT_DB_PATH
) -> Dict[str, Any]:
    """Build a field-description draft from schema + a data sample. No API spend."""
    meta = _column_meta(db_path, table, column) or {"type": "", "pk": 0}
    type_label = (meta.get("type") or "value").upper()
    samples = _sample_values(db_path, table, column)
    distinct = _distinct_count(db_path, table, column)

    parts: List[str] = []
    if meta.get("pk"):
        parts.append(f"Primary key / unique identifier for the {humanize(table)} record.")

    is_categorical = bool(samples) and 0 < distinct <= _CATEGORICAL_MAX_DISTINCT
    if is_categorical and not meta.get("pk"):
        shown = ", ".join(samples)
        parts.append(
            f"Categorical {humanize(column)} on {humanize(table)} "
            f"({distinct} distinct value{'s' if distinct != 1 else ''}); "
            f"observed values include: {shown}."
        )
    elif not meta.get("pk"):
        parts.append(
            f"{type_label} field on {humanize(table)} capturing the "
            f"{humanize(column).lower()}."
        )

    description = " ".join(parts).strip()
    return {
        "display_name": humanize(column),
        "description": description,
        "example_value": samples[0] if samples else "",
        "_type": type_label,
        "_distinct": distinct,
        "_samples": samples,
        "_source": "deterministic",
    }


def ai_draft(table: str, column: str, db_path: str = DEFAULT_DB_PATH) -> Dict[str, Any]:
    """AI-assisted draft (OpenAI). Falls back to the deterministic draft on any error."""
    base = deterministic_draft(table, column, db_path)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        base["_note"] = "OPENAI_API_KEY not set — used deterministic draft."
        return base

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        samples = base.get("_samples") or []
        prompt = (
            "You are a manufacturing data-dictionary author. Write a concise, "
            "plain-language business description (1-2 sentences) for a database "
            "column so a non-technical analyst understands what it means and how "
            "it is used. Do not restate the column name verbatim, do not mention "
            "SQL types, and return ONLY the description text.\n\n"
            f"Table: {table}\n"
            f"Column: {column}\n"
            f"Declared type: {base.get('_type')}\n"
            f"Distinct values in data: {base.get('_distinct')}\n"
            f"Sample values: {', '.join(samples) if samples else 'n/a'}\n"
        )
        resp = client.chat.completions.create(
            model=_AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=180,
        )
        text = (resp.choices[0].message.content or "").strip()
        if text:
            base["description"] = text
            base["_source"] = "ai"
            base["_note"] = f"Drafted by {_AI_MODEL}."
    except Exception as exc:  # noqa: BLE001 — never hard-fail the draft path
        base["_note"] = (
            f"AI draft failed ({type(exc).__name__}) — used deterministic draft."
        )
    return base


def draft_field_description(
    table: str,
    column: str,
    use_ai: bool = False,
    db_path: str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """Return a draft {display_name, description, example_value, _source, ...}.

    ``use_ai=True`` opts into the OpenAI path (explicit, one column at a time);
    otherwise the deterministic, no-spend draft is returned.
    """
    if use_ai:
        return ai_draft(table, column, db_path)
    return deterministic_draft(table, column, db_path)


# ── persistence (idempotent upserts) ────────────────────────────────────────


def upsert_field_description(
    table: str,
    column: str,
    display_name: Optional[str],
    description: Optional[str],
    example_value: Optional[str],
    db_path: str = DEFAULT_DB_PATH,
    source_database: str = SOURCE_DATABASE,
    schema_name: str = SCHEMA_NAME,
) -> Dict[str, Any]:
    """Idempotent upsert into ``api_field_descriptions``."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO api_field_descriptions
                (source_database, schema_name, table_name, column_name,
                 display_name, description, example_value, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(source_database, schema_name, table_name, column_name)
            DO UPDATE SET
                display_name  = excluded.display_name,
                description   = excluded.description,
                example_value = excluded.example_value,
                updated_at    = CURRENT_TIMESTAMP
            """,
            (source_database, schema_name, table, column,
             display_name, description, example_value),
        )
        conn.commit()
        return {"ok": True}
    except sqlite3.Error as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()


def certify_field_definition(
    table: str,
    column: str,
    field_definition: Optional[str],
    certified: bool = True,
    db_path: str = DEFAULT_DB_PATH,
    source_database: str = SOURCE_DATABASE,
    schema_name: str = SCHEMA_NAME,
) -> Dict[str, Any]:
    """Idempotent upsert into ``dab_field_definitions`` (the DAB stand-in)."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO dab_field_definitions
                (source_database, schema_name, table_name, column_name,
                 field_definition, certified, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(source_database, schema_name, table_name, column_name)
            DO UPDATE SET
                field_definition = excluded.field_definition,
                certified        = excluded.certified,
                updated_at       = CURRENT_TIMESTAMP
            """,
            (source_database, schema_name, table, column,
             field_definition, 1 if certified else 0),
        )
        conn.commit()
        return {"ok": True}
    except sqlite3.Error as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()


# ── headless bulk pipeline ──────────────────────────────────────────────────


def list_business_columns(
    db_path: str = DEFAULT_DB_PATH,
    skip_prefixes: Tuple[str, ...] = ("stg_",),
) -> List[Tuple[str, str]]:
    """Return (table, column) pairs for ERP/business tables.

    Excludes internal metadata tables, sqlite_* tables, and any table whose name
    starts with one of ``skip_prefixes`` (staging tables are not curated business
    vocabulary).
    """
    conn = _connect(db_path)
    try:
        tables = [
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        ]
    finally:
        conn.close()

    out: List[Tuple[str, str]] = []
    for t in tables:
        if t in _METADATA_TABLES or t.startswith("sqlite_"):
            continue
        if any(t.startswith(p) for p in skip_prefixes):
            continue
        conn = _connect(db_path)
        try:
            cols = [r["name"] for r in conn.execute(f'PRAGMA table_info("{t}")').fetchall()]
        finally:
            conn.close()
        for c in cols:
            out.append((t, c))
    return out


def _described_columns(
    db_path: str, source_database: str, schema_name: str
) -> set:
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT table_name, column_name FROM api_field_descriptions "
            "WHERE source_database = ? AND schema_name = ?",
            (source_database, schema_name),
        ).fetchall()
        return {(r["table_name"], r["column_name"]) for r in rows}
    except sqlite3.Error:
        return set()
    finally:
        conn.close()


def fill_missing(
    db_path: str = DEFAULT_DB_PATH,
    use_ai: bool = False,
    source_database: str = SOURCE_DATABASE,
    schema_name: str = SCHEMA_NAME,
    skip_prefixes: Tuple[str, ...] = ("stg_",),
    verbose: bool = False,
) -> int:
    """Draft + upsert a description for every business column lacking one.

    Idempotent: already-described columns (including SME-curated ones) are left
    untouched, so re-running only fills the gaps. Returns the number of columns
    newly described.
    """
    existing = _described_columns(db_path, source_database, schema_name)
    count = 0
    for table, column in list_business_columns(db_path, skip_prefixes):
        if (table, column) in existing:
            continue
        d = draft_field_description(table, column, use_ai=use_ai, db_path=db_path)
        res = upsert_field_description(
            table, column,
            d.get("display_name"), d.get("description"), d.get("example_value"),
            db_path=db_path, source_database=source_database, schema_name=schema_name,
        )
        if res.get("ok"):
            count += 1
            if verbose:
                print(f"  drafted [{d.get('_source')}]: {table}.{column} -> {d.get('display_name')}")
    return count


def compute_field_coverage(schema: Dict[str, Any]) -> Dict[str, int]:
    """Aggregate described/certified coverage across every table in *schema*.

    *schema* is the unified-schema mapping ``{table: {column: meta}}`` where each
    ``meta`` may carry ``description`` and ``certified``. Returns overall totals
    ``{tables, columns, described, certified}`` — the global counterpart to the
    per-table counts shown for a single selected entity.
    """
    tables = columns = described = certified = 0
    for cols in (schema or {}).values():
        tables += 1
        for meta in (cols or {}).values():
            columns += 1
            if meta.get("description"):
                described += 1
            if meta.get("certified"):
                certified += 1
    return {
        "tables": tables,
        "columns": columns,
        "described": described,
        "certified": certified,
    }


__all__ = [
    "humanize",
    "compute_field_coverage",
    "draft_field_description",
    "deterministic_draft",
    "ai_draft",
    "upsert_field_description",
    "certify_field_definition",
    "list_business_columns",
    "fill_missing",
    "DEFAULT_DB_PATH",
]
