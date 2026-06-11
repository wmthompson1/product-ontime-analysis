"""masking_policy_pipeline.py — suggest + persist column masking policies (DAB stand-in).

The masking counterpart to ``field_description_pipeline.py``. A masking policy is
a per-column choice of *strategy* (how the value is obscured downstream) plus a
plain-language *rationale*. Policies are persisted to ``column_masking_policies``
and, once certified, published into ``dab_config.json`` (each field's ``masking``
attribute) by ``scripts/sync_masking_to_dab_config.py``.

Strategies (the closed vocabulary, matching the SQLite CHECK constraint):

  - ``none``    — no masking; the raw value is exposed.
  - ``hash``    — irreversible one-way hash; preserves joinability / grouping
                  while hiding the underlying value (SSN, account no, tax id).
  - ``partial`` — partial mask that keeps part of the value for usability
                  (email domain, last digits of a phone, initial of a name).
  - ``redact``  — fully hidden / dropped; no analytic value retained
                  (passwords, secrets, full street addresses).

Suggestions are **deterministic only** — a name-based heuristic, no LLM, no API
spend. This is the project's cost-conscious default and the explicit requirement
for this surface (the masking tab never calls an AI model).

Persistence is idempotent: the table uses the four-column PK
(source_database, schema_name, table_name, column_name) and this module upserts.
``upsert_masking_policy`` (the *save* step) deliberately never changes the
``certified`` flag, so re-authoring a strategy does not silently un-certify it;
``certify_masking_policy`` is the only path that writes ``certified``.

This module is self-contained (its own sqlite helpers and the strategy heuristic)
so it can be imported by ``app.py`` for the UI "Suggest strategy" action and run
head-less by a seed/fill script without importing the full FastAPI/Gradio app.
"""
from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

# Reuse the business-column enumeration + humanizer from the description pipeline
# so masking and descriptions agree on exactly which columns are "business"
# columns (same metadata/staging exclusions).
from field_description_pipeline import (  # noqa: E402
    DEFAULT_DB_PATH,
    humanize,
    list_business_columns,
)

# Must match app.py SQL_MCP_SOURCE_DATABASE / _DEFAULT_SCHEMA so the schema
# browser overlay and the publish step find these rows.
SOURCE_DATABASE = os.environ.get("SQL_MCP_SOURCE_DATABASE", "manufacturing")
SCHEMA_NAME = os.environ.get("SQL_MCP_DEFAULT_SCHEMA", "dbo")

# The closed vocabulary of masking strategies (matches the SQLite CHECK).
MASKING_STRATEGIES: Tuple[str, ...] = ("none", "hash", "partial", "redact")

# Deterministic name heuristic. Each rule is (keywords, strategy, rationale).
# Rules are evaluated in priority order; the FIRST whose keyword is a substring
# of the (lowercased) column name wins. Highest-sensitivity rules come first so
# that, e.g., "password" -> redact is checked before a generic name rule.
_HEURISTIC_RULES: List[Tuple[Tuple[str, ...], str, str]] = [
    (
        ("password", "passwd", "pwd", "secret", "token", "api_key", "apikey",
         "private_key"),
        "redact",
        "Credential / secret material — fully redact; it has no analytic value "
        "and must never be exposed.",
    ),
    (
        ("ssn", "social_security", "tax_id", "taxid", "ein", "passport",
         "national_id", "drivers_license", "license_no", "account_number",
         "account_no", "acct_no", "iban", "routing_number", "routing_no",
         "card_number", "credit_card", "card_no", "dob", "date_of_birth",
         "birth_date"),
        "hash",
        "Sensitive government / financial identifier — irreversibly hash so it "
        "stays joinable for analysis without exposing the real value.",
    ),
    (
        ("email", "e_mail"),
        "partial",
        "Contact email (PII) — partial mask keeps the domain for analytics "
        "while hiding the local part.",
    ),
    (
        ("phone", "fax", "mobile", "telephone", "cell_no"),
        "partial",
        "Contact phone number (PII) — partial mask keeps the last digits for "
        "verification while hiding the rest.",
    ),
    (
        ("first_name", "last_name", "middle_name", "full_name", "contact_name",
         "person_name", "given_name", "surname", "maiden_name"),
        "partial",
        "Personal name (PII) — partial mask keeps an initial for readability "
        "while hiding the full name.",
    ),
    (
        ("street", "address_line", "addr_line", "address1", "address_1",
         "home_address", "mailing_address"),
        "redact",
        "Street-level address (location PII) — redact; coarser fields (city, "
        "state) can stay for regional analysis.",
    ),
]


# ── deterministic suggestion ────────────────────────────────────────────────


def suggest_masking_strategy(
    table: str, column: str, db_path: str = DEFAULT_DB_PATH
) -> Dict[str, Any]:
    """Return a deterministic masking suggestion for a column. No API spend.

    Matches the lowercased column name against ``_HEURISTIC_RULES`` in priority
    order. When nothing matches, the safe default ``none`` is returned with a
    rationale prompting SME review. ``db_path`` is accepted for signature
    symmetry with the description pipeline (the heuristic is name-based and does
    not currently read the data).
    """
    col_l = (column or "").lower()
    for keywords, strategy, rationale in _HEURISTIC_RULES:
        if any(k in col_l for k in keywords):
            return {
                "masking_strategy": strategy,
                "rationale": rationale,
                "_source": "deterministic",
            }
    return {
        "masking_strategy": "none",
        "rationale": (
            f"No sensitive-data signal detected in the name "
            f"'{humanize(column)}' on {humanize(table)}; defaulting to no "
            f"masking. Review and override if this column holds PII."
        ),
        "_source": "deterministic",
    }


# ── persistence (idempotent upserts) ────────────────────────────────────────


def upsert_masking_policy(
    table: str,
    column: str,
    masking_strategy: str,
    rationale: Optional[str],
    db_path: str = DEFAULT_DB_PATH,
    source_database: str = SOURCE_DATABASE,
    schema_name: str = SCHEMA_NAME,
) -> Dict[str, Any]:
    """Idempotent *save* of a strategy + rationale (the authoring step).

    On conflict this updates ``masking_strategy`` and ``rationale`` only — it
    never touches ``certified``, so saving an edited policy does not silently
    un-certify a previously certified column.
    """
    strategy = (masking_strategy or "none").lower()
    if strategy not in MASKING_STRATEGIES:
        return {"ok": False, "error": f"Unknown masking strategy: {masking_strategy!r}"}
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO column_masking_policies
                (source_database, schema_name, table_name, column_name,
                 masking_strategy, rationale, certified, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
            ON CONFLICT(source_database, schema_name, table_name, column_name)
            DO UPDATE SET
                masking_strategy = excluded.masking_strategy,
                rationale        = excluded.rationale,
                updated_at       = CURRENT_TIMESTAMP
            """,
            (source_database, schema_name, table, column, strategy, rationale),
        )
        conn.commit()
        return {"ok": True}
    except sqlite3.Error as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()


def certify_masking_policy(
    table: str,
    column: str,
    masking_strategy: str,
    rationale: Optional[str],
    certified: bool = True,
    db_path: str = DEFAULT_DB_PATH,
    source_database: str = SOURCE_DATABASE,
    schema_name: str = SCHEMA_NAME,
) -> Dict[str, Any]:
    """Idempotent upsert that writes the ``certified`` flag (the certify step).

    Persists the current strategy + rationale alongside the flag so certifying
    also captures any edits shown in the panel.
    """
    strategy = (masking_strategy or "none").lower()
    if strategy not in MASKING_STRATEGIES:
        return {"ok": False, "error": f"Unknown masking strategy: {masking_strategy!r}"}
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO column_masking_policies
                (source_database, schema_name, table_name, column_name,
                 masking_strategy, rationale, certified, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(source_database, schema_name, table_name, column_name)
            DO UPDATE SET
                masking_strategy = excluded.masking_strategy,
                rationale        = excluded.rationale,
                certified        = excluded.certified,
                updated_at       = CURRENT_TIMESTAMP
            """,
            (source_database, schema_name, table, column, strategy, rationale,
             1 if certified else 0),
        )
        conn.commit()
        return {"ok": True}
    except sqlite3.Error as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()


# ── headless bulk pipeline ──────────────────────────────────────────────────


def _policied_columns(
    db_path: str, source_database: str, schema_name: str
) -> set:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT table_name, column_name FROM column_masking_policies "
            "WHERE source_database = ? AND schema_name = ?",
            (source_database, schema_name),
        ).fetchall()
        return {(r["table_name"], r["column_name"]) for r in rows}
    except sqlite3.Error:
        return set()
    finally:
        conn.close()


def fill_missing_masking(
    db_path: str = DEFAULT_DB_PATH,
    source_database: str = SOURCE_DATABASE,
    schema_name: str = SCHEMA_NAME,
    skip_prefixes: Tuple[str, ...] = ("stg_",),
    verbose: bool = False,
) -> int:
    """Auto-flag obviously sensitive business columns lacking a policy row.

    For every business column without an existing policy, runs the deterministic
    heuristic and upserts a row **only when the suggested strategy is not
    ``none``**. This avoids drowning the table in trivial ``none`` rows: only the
    columns the heuristic recognizes as sensitive are auto-policied; everything
    else is left for explicit SME review. Idempotent — already-policied columns
    are never touched. Returns the number of columns newly policied.
    """
    existing = _policied_columns(db_path, source_database, schema_name)
    count = 0
    for table, column in list_business_columns(db_path, skip_prefixes):
        if (table, column) in existing:
            continue
        s = suggest_masking_strategy(table, column, db_path=db_path)
        if s.get("masking_strategy", "none") == "none":
            continue
        res = upsert_masking_policy(
            table, column,
            s.get("masking_strategy", "none"), s.get("rationale"),
            db_path=db_path, source_database=source_database, schema_name=schema_name,
        )
        if res.get("ok"):
            count += 1
            if verbose:
                print(f"  flagged [{s.get('masking_strategy')}]: {table}.{column}")
    return count


def compute_masking_coverage(schema: Dict[str, Any]) -> Dict[str, int]:
    """Aggregate masking coverage across every table in *schema*.

    *schema* is the unified-schema mapping ``{table: {column: meta}}`` where each
    ``meta`` may carry ``masking_strategy`` (present only when a policy row
    exists) and ``masking_certified``. Returns overall totals
    ``{tables, columns, policied, certified}`` where ``policied`` counts columns
    that have any policy row (a decision was made, including an explicit
    ``none``) and ``certified`` counts certified policies — the global
    counterpart to the per-table counts shown for a single selected entity.
    """
    tables = columns = policied = certified = 0
    for cols in (schema or {}).values():
        tables += 1
        for meta in (cols or {}).values():
            columns += 1
            if meta.get("masking_strategy") is not None:
                policied += 1
            if meta.get("masking_certified"):
                certified += 1
    return {
        "tables": tables,
        "columns": columns,
        "policied": policied,
        "certified": certified,
    }


__all__ = [
    "MASKING_STRATEGIES",
    "suggest_masking_strategy",
    "upsert_masking_policy",
    "certify_masking_policy",
    "fill_missing_masking",
    "compute_masking_coverage",
    "DEFAULT_DB_PATH",
]
