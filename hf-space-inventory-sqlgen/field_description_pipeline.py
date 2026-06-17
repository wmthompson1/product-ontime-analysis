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

import csv
import json
import os
import sqlite3
import tempfile
from typing import Any, Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
DEFAULT_DB_PATH = os.path.join(_HERE, "app_schema", "manufacturing.db")

# The root-level CSV that mirrors the api_field_descriptions overlay for the
# canonical-graph columns. This is the committed, SME-facing, version-controlled
# copy (same pattern as masking_matrix.csv): it survives a gitignored-DB rebuild
# and is upserted into SQLite on every boot. AI spend happens once when authoring
# this file, never per-boot.
DEFAULT_CSV_PATH = os.path.join(_REPO_ROOT, "field_descriptions.csv")

# CSV column order (also the user-facing column order).
CSV_COLUMNS: Tuple[str, ...] = (
    "table_name",
    "column_name",
    "display_name",
    "description",
    "example_value",
)

# The canonical graph export — source of the 223 column-node target set.
DEFAULT_GRAPH_METADATA_PATH = os.path.join(
    _REPO_ROOT, "replit_integrations", "graph_metadata.json"
)

# Knowledge-base / guide docs the AI draft path may consult selectively. Only the
# lines that actually mention a column (table.column / table:column) or the
# column+table together are pulled in, so the prompt stays small and cheap.
_DEFAULT_KB_DOCS: Tuple[str, ...] = (
    os.path.join(_REPO_ROOT, "docs", "mrp_inventory_knowledge_base.md"),
    os.path.join(_REPO_ROOT, "define-relationship-integration-guide.md"),
)

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
    "column_masking_policies",
    "masking_matrix",
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


# ── knowledge-base context (selective, for the AI path only) ────────────────

# Read docs are cached so a bulk run does not re-read the files per column.
_KB_CACHE: Dict[str, List[str]] = {}

# How much KB text the AI prompt may carry (kept small for cost / focus).
_KB_MAX_LINES = 6
_KB_MAX_CHARS = 700


def _kb_lines(doc_paths: Tuple[str, ...]) -> List[str]:
    """Return (cached) non-empty, stripped lines for the given doc paths."""
    key = "\x00".join(doc_paths)
    cached = _KB_CACHE.get(key)
    if cached is not None:
        return cached
    lines: List[str] = []
    for path in doc_paths:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for raw in fh:
                    s = raw.strip()
                    if s:
                        lines.append(s)
        except OSError:
            continue
    _KB_CACHE[key] = lines
    return lines


def kb_context_for(
    table: str,
    column: str,
    doc_paths: Tuple[str, ...] = _DEFAULT_KB_DOCS,
    max_lines: int = _KB_MAX_LINES,
    max_chars: int = _KB_MAX_CHARS,
) -> str:
    """Pull only the KB/guide lines relevant to one column.

    Selection is deliberately narrow so the AI prompt stays small and cheap:
      1. strong match — a line that names the column as ``table.column`` or
         ``table:column`` (the way concept cards reference real columns);
      2. weak match — a line mentioning the bare column token *and* the table
         token together.
    Returns "" when nothing relevant is found (the prompt is then unchanged).
    """
    if not table or not column:
        return ""
    lines = _kb_lines(doc_paths)
    if not lines:
        return ""

    dotted = f"{table}.{column}".lower()
    coloned = f"{table}:{column}".lower()
    col_token = column.lower()
    tbl_token = table.lower()

    strong: List[str] = []
    weak: List[str] = []
    for ln in lines:
        low = ln.lower()
        if dotted in low or coloned in low:
            strong.append(ln)
        elif col_token in low and tbl_token in low:
            weak.append(ln)

    picked: List[str] = []
    seen = set()
    for ln in strong + weak:
        if ln in seen:
            continue
        seen.add(ln)
        picked.append(ln)
        if len(picked) >= max_lines:
            break

    context = "\n".join(picked).strip()
    if len(context) > max_chars:
        context = context[:max_chars].rstrip()
    return context


# ── drafting ────────────────────────────────────────────────────────────────


def _looks_boolean(samples: List[str], distinct: int) -> bool:
    """True when the observed values look like a yes/no flag."""
    if not samples or distinct > 2:
        return False
    vals = {s.strip().lower() for s in samples}
    return vals.issubset({"0", "1", "y", "n", "yes", "no", "true", "false", "t", "f"})


def _deterministic_description(
    table: str, column: str, meta: Dict[str, Any], samples: List[str], distinct: int
) -> str:
    """Pattern-based plain-language description — accurate, no SQL jargon, no spend."""
    tbl = humanize(table).lower()
    col_l = column.lower()
    human_col = humanize(column).lower()
    type_u = (meta.get("type") or "").upper()
    is_numeric = any(t in type_u for t in ("INT", "REAL", "NUM", "DEC", "FLOAT", "DOUB"))

    # Primary key.
    if meta.get("pk"):
        return f"Unique identifier for each {tbl} record."

    # Foreign-key style reference (e.g. part_id, site_id) that is not the PK.
    if col_l.endswith("_id") and len(col_l) > 3:
        target = humanize(col_l[:-3]).lower()
        return f"Links each {tbl} to its related {target}."

    # Timestamps.
    if col_l in ("created_at", "create_date", "created_date"):
        return f"Timestamp for when the {tbl} record was created."
    if col_l in ("updated_at", "modified_at", "last_modified", "update_date"):
        return f"Timestamp for when the {tbl} record was last updated."
    if col_l.endswith("_at"):
        base = humanize(col_l[:-3]).lower()
        return f"Timestamp marking when the {tbl} was {base}."
    if col_l.endswith("_date") or col_l == "date":
        base = humanize(col_l[:-5]).lower() if col_l.endswith("_date") else ""
        what = f"{base} date" if base else "date"
        return f"The {what} for the {tbl}."

    # Yes/no flag.
    if _looks_boolean(samples, distinct) or col_l.startswith(("is_", "has_")):
        subject = human_col
        for prefix in ("is_", "has_"):
            if col_l.startswith(prefix):
                subject = humanize(col_l[len(prefix):]).lower()
        return f"Yes/no flag indicating whether the {tbl} {subject}."

    # Human-readable name.
    if col_l == "name" or col_l.endswith("_name"):
        base = humanize(col_l[:-5]).lower() if col_l.endswith("_name") else tbl
        return f"Human-readable name of the {base}."

    # Free-text.
    if col_l in ("description", "notes", "note", "comment", "comments", "remark",
                 "remarks") or col_l.endswith("_description") or col_l.endswith("_notes"):
        return f"Free-text {human_col} for the {tbl}."

    # Bounded category / status / type field — list the observed values.
    is_categorical = bool(samples) and 0 < distinct <= _CATEGORICAL_MAX_DISTINCT
    if is_categorical and not is_numeric:
        shown = ", ".join(samples[:6])
        return (
            f"The {human_col} of each {tbl}; one of a small set of values such "
            f"as: {shown}."
        )

    # Numeric measure.
    if is_numeric:
        return f"Numeric {human_col} recorded for each {tbl}."

    # Generic free-form text fallback.
    return f"The {human_col} for each {tbl} record."


def deterministic_draft(
    table: str, column: str, db_path: str = DEFAULT_DB_PATH
) -> Dict[str, Any]:
    """Build a field-description draft from schema + a data sample. No API spend."""
    meta = _column_meta(db_path, table, column) or {"type": "", "pk": 0}
    type_label = (meta.get("type") or "value").upper()
    samples = _sample_values(db_path, table, column)
    distinct = _distinct_count(db_path, table, column)

    description = _deterministic_description(table, column, meta, samples, distinct)
    return {
        "display_name": humanize(column),
        "description": description,
        "example_value": samples[0] if samples else "",
        "_type": type_label,
        "_distinct": distinct,
        "_samples": samples,
        "_source": "deterministic",
    }


def ai_draft(
    table: str,
    column: str,
    db_path: str = DEFAULT_DB_PATH,
    use_kb: bool = False,
    kb_context: Optional[str] = None,
) -> Dict[str, Any]:
    """AI-assisted draft (OpenAI). Falls back to the deterministic draft on any error.

    When ``use_kb`` is set, relevant knowledge-base / guide lines for the column
    are pulled in (selectively, capped) and added to the prompt as reference
    notes. Pass ``kb_context`` directly to override the lookup (e.g. in tests).
    """
    base = deterministic_draft(table, column, db_path)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        base["_note"] = "OPENAI_API_KEY not set — used deterministic draft."
        return base

    if kb_context is None and use_kb:
        kb_context = kb_context_for(table, column)
    kb_context = (kb_context or "").strip()
    base["_kb_used"] = bool(kb_context)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        samples = base.get("_samples") or []
        kb_block = (
            "\nReference notes (authoritative domain context — use only the parts "
            f"relevant to this column):\n{kb_context}\n" if kb_context else ""
        )
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
            f"{kb_block}"
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
    use_kb: bool = False,
) -> Dict[str, Any]:
    """Return a draft {display_name, description, example_value, _source, ...}.

    ``use_ai=True`` opts into the OpenAI path (explicit, one column at a time);
    otherwise the deterministic, no-spend draft is returned. ``use_kb=True``
    (AI path only) lets the prompt consult the KB/guide for the column.
    """
    if use_ai:
        return ai_draft(table, column, db_path, use_kb=use_kb)
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


# ── canonical-graph column set + committed CSV mirror ───────────────────────


def graph_column_keys(
    graph_metadata_path: str = DEFAULT_GRAPH_METADATA_PATH,
) -> List[Tuple[str, str]]:
    """Return the (table, column) pairs for every column node in the graph.

    This is the *exact* target set for field descriptions — the columns that
    appear as ``node_type == "column"`` nodes in the canonical graph export. The
    list is sorted (table, column) so the committed CSV is deterministic.
    """
    with open(graph_metadata_path, "r", encoding="utf-8") as fh:
        meta = json.load(fh)
    keys = {
        (n["table_name"], n["column_name"])
        for n in meta.get("nodes", [])
        if n.get("node_type") == "column"
    }
    return sorted(keys)


def read_descriptions_csv(
    csv_path: str = DEFAULT_CSV_PATH,
) -> List[Dict[str, str]]:
    """Read the field-descriptions CSV. Returns [] if the file is absent."""
    if not os.path.exists(csv_path):
        return []
    out: List[Dict[str, str]] = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for raw in csv.DictReader(fh):
            tbl = (raw.get("table_name") or "").strip()
            col = (raw.get("column_name") or "").strip()
            if not tbl or not col:
                continue
            out.append({
                "table_name": tbl,
                "column_name": col,
                "display_name": (raw.get("display_name") or "").strip(),
                "description": (raw.get("description") or "").strip(),
                "example_value": (raw.get("example_value") or "").strip(),
            })
    return out


def write_descriptions_csv(
    rows: List[Dict[str, str]],
    csv_path: str = DEFAULT_CSV_PATH,
) -> int:
    """Write rows to the CSV (atomic), sorted by (table_name, column_name)."""
    ordered = sorted(rows, key=lambda r: (r["table_name"], r["column_name"]))
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


def load_descriptions_from_csv(
    csv_path: str = DEFAULT_CSV_PATH,
    db_path: str = DEFAULT_DB_PATH,
    source_database: str = SOURCE_DATABASE,
    schema_name: str = SCHEMA_NAME,
) -> Dict[str, Any]:
    """Upsert every CSV row into ``api_field_descriptions`` (idempotent).

    Mirrors the masking_matrix CSV→SQLite boot sync: the committed CSV is the
    SME-facing source of truth, re-applied on every boot so the descriptions
    survive a gitignored-DB rebuild. Returns ``{"ok", "loaded"}`` or an error.
    """
    rows = read_descriptions_csv(csv_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_field_descriptions (
                source_database TEXT    NOT NULL,
                schema_name     TEXT    NOT NULL,
                table_name      TEXT    NOT NULL,
                column_name     TEXT    NOT NULL,
                display_name    TEXT,
                description     TEXT,
                example_value   TEXT,
                updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (source_database, schema_name, table_name, column_name)
            )
            """
        )
        for r in rows:
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
                (source_database, schema_name, r["table_name"], r["column_name"],
                 r["display_name"], r["description"], r["example_value"]),
            )
        conn.commit()
        return {"ok": True, "loaded": len(rows)}
    except sqlite3.Error as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()


def compute_graph_coverage(
    csv_path: str = DEFAULT_CSV_PATH,
    graph_metadata_path: str = DEFAULT_GRAPH_METADATA_PATH,
) -> Dict[str, Any]:
    """File-vs-file coverage of the canonical-graph columns by the committed CSV.

    DB-independent (so it is robust in CI): proves the committed CSV describes
    every column node in the graph and carries no rows for non-graph columns.
    Returns ``{total, described, missing, extra, duplicates}`` where *missing*
    are graph columns with no non-empty description, *extra* are CSV rows that
    are not graph columns, and *duplicates* are ``(table, column)`` keys that
    appear in more than one CSV row (which would let a stale/conflicting row
    slip past a set-based "exact" claim).
    """
    graph = set(graph_column_keys(graph_metadata_path))
    rows = read_descriptions_csv(csv_path)
    described = {
        (r["table_name"], r["column_name"])
        for r in rows
        if r["description"]
    }
    seen: Dict[Any, int] = {}
    for r in rows:
        key = (r["table_name"], r["column_name"])
        seen[key] = seen.get(key, 0) + 1
    csv_keys = set(seen)
    duplicates = sorted(k for k, n in seen.items() if n > 1)
    missing = sorted(graph - described)
    extra = sorted(csv_keys - graph)
    return {
        "total": len(graph),
        "described": len(graph & described),
        "missing": missing,
        "extra": extra,
        "duplicates": duplicates,
    }


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
    "kb_context_for",
    "compute_field_coverage",
    "compute_graph_coverage",
    "draft_field_description",
    "deterministic_draft",
    "ai_draft",
    "upsert_field_description",
    "certify_field_definition",
    "list_business_columns",
    "fill_missing",
    "graph_column_keys",
    "read_descriptions_csv",
    "write_descriptions_csv",
    "load_descriptions_from_csv",
    "DEFAULT_DB_PATH",
    "DEFAULT_CSV_PATH",
    "DEFAULT_GRAPH_METADATA_PATH",
    "CSV_COLUMNS",
]
