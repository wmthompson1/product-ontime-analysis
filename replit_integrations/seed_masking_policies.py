"""Seed SME-facing column masking policies into ``column_masking_policies`` (SQLite).

The masking counterpart to ``seed_field_descriptions.py``. ``column_masking_policies``
is the local stand-in for the company DAB's masking layer: here we author a
masking *strategy* + *rationale* per sensitive column; an SME (or the DAB feed)
is the authority and may overwrite them.

Scope: a curated set of obviously-sensitive PII columns (contact details, names,
addresses). Staging (``stg_``) columns are intentionally skipped — they are not
part of the curated business vocabulary.

Strategies are chosen deterministically (no LLM). The curated entries below are
hand-picked; ``--fill-missing`` additionally auto-flags any other business
column the name heuristic recognizes as sensitive (it never writes ``none``
rows, so unreviewed columns stay unreviewed).

Idempotent: ``column_masking_policies`` has the four-part PK
(source_database, schema_name, table_name, column_name); this upserts, so
re-running refreshes the curated policies without creating duplicates. The seed
deliberately leaves rows *uncertified* — certification is an explicit SME action
in the Data Masking tab.
"""
import argparse
import os
import sqlite3
import sys

_HF_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "hf-space-inventory-sqlgen",
)
if _HF_DIR not in sys.path:
    sys.path.insert(0, _HF_DIR)

DB_PATH = os.path.join(_HF_DIR, "app_schema", "manufacturing.db")

# Must match the app defaults (app.py SQL_MCP_SOURCE_DATABASE / _DEFAULT_SCHEMA)
# so the schema browser overlay and the publish step find these rows.
SOURCE_DATABASE = os.environ.get("SQL_MCP_SOURCE_DATABASE", "manufacturing")
SCHEMA_NAME = os.environ.get("SQL_MCP_DEFAULT_SCHEMA", "dbo")

# (table_name, column_name, masking_strategy, rationale)
MASKING_POLICIES = [
    ("customer", "email", "partial",
     "Contact email (PII) — partial mask keeps the domain for analytics while "
     "hiding the local part."),
    ("customer", "phone", "partial",
     "Contact phone number (PII) — partial mask keeps the last digits for "
     "verification while hiding the rest."),
    ("customer", "first_name", "partial",
     "Personal name (PII) — partial mask keeps an initial for readability while "
     "hiding the full name."),
    ("customer", "last_name", "partial",
     "Personal name (PII) — partial mask keeps an initial for readability while "
     "hiding the full name."),
    ("supplier", "email", "partial",
     "Supplier contact email (PII) — partial mask keeps the domain while hiding "
     "the local part."),
    ("supplier", "phone", "partial",
     "Supplier contact phone (PII) — partial mask keeps the last digits while "
     "hiding the rest."),
]


def _seed_curated() -> int:
    """Upsert the SME-curated masking policies. Returns the count attempted."""
    from masking_policy_pipeline import upsert_masking_policy

    seeded = 0
    for table, column, strategy, rationale in MASKING_POLICIES:
        res = upsert_masking_policy(
            table, column, strategy, rationale,
            db_path=DB_PATH, source_database=SOURCE_DATABASE, schema_name=SCHEMA_NAME,
        )
        if res.get("ok"):
            print(f"  masking policy: {table}.{column} -> {strategy}")
            seeded += 1
        else:
            print(f"  SKIP {table}.{column}: {res.get('error')}")
    return seeded


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed SME-curated column masking policies; optionally flag the rest.",
    )
    parser.add_argument(
        "--fill-missing", action="store_true",
        help="After seeding the curated set, auto-flag any other business column "
             "the deterministic name heuristic recognizes as sensitive "
             "(idempotent; never writes 'none' rows; curated rows are preserved).",
    )
    args = parser.parse_args(argv)

    if not os.path.exists(DB_PATH):
        raise SystemExit(f"ERROR: manufacturing.db not found at {DB_PATH}")

    seeded = _seed_curated()
    print(f"seeded {seeded} curated masking policy/policies (idempotent; stand-in for DAB).")

    if args.fill_missing:
        from masking_policy_pipeline import fill_missing_masking
        print("auto-flagging additional sensitive columns (deterministic heuristic)...")
        flagged = fill_missing_masking(
            db_path=DB_PATH,
            source_database=SOURCE_DATABASE,
            schema_name=SCHEMA_NAME,
            verbose=True,
        )
        print(f"flagged {flagged} previously-unpolicied sensitive column(s).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
