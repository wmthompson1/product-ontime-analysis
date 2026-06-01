"""
Migration: drop_poc_tables.py
==============================
Drops 21 empty PoC tables that were created during early development but
never populated.  Also retires their orphaned schema metadata.

Re-runnable: every step is idempotent (DROP TABLE IF EXISTS, DELETE with
WHERE, etc.).  Runs inside a single transaction so it is fully atomic.

ArangoDB purge (Step 11):
  After the SQLite cleanup this script also removes the stale table:: and
  column:: vertices — and their contains edges — from the ArangoDB
  manufacturing_graph so the live graph matches the database.  The step
  is skipped gracefully when ARANGO_HOST / ARANGO_DB env vars are absent.

Usage:
    python hf-space-inventory-sqlgen/migrations/drop_poc_tables.py

Or with an explicit DB path:
    python hf-space-inventory-sqlgen/migrations/drop_poc_tables.py /path/to/manufacturing.db

Skip ArangoDB step explicitly:
    SKIP_ARANGO=1 python hf-space-inventory-sqlgen/migrations/drop_poc_tables.py
"""

import os
import sys
import sqlite3

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_DB = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "app_schema", "manufacturing.db"
)

EMPTY_TABLES = [
    "corrective_actions",
    "daily_deliveries",
    "downtime_events",
    "effectiveness_metrics",
    "equipment_metrics",
    "equipment_reliability",
    "failure_events",
    "financial_impact",
    "industry_benchmarks",
    "maintenance_targets",
    "manufacturing_acronyms",
    "non_conformant_materials",
    "product_defects",
    "product_lines",
    "production_lines",
    "production_quality",
    "production_schedule",
    "products",
    "quality_costs",
    "quality_incidents",
    "users",
]

# Query files that exclusively reference empty tables — their intent-query
# rows become dangling after the tables are dropped.
EXCLUSIVELY_EMPTY_QUERY_FILES = [
    "equipment_reliability.sql",
    "production_analytics.sql",
    "customer_order.sql",
    "delivery_performance_perspectives.sql",
]

# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------

def run(db_path: str) -> None:
    db_path = os.path.abspath(db_path)
    if not os.path.exists(db_path):
        print(f"ERROR: database not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=OFF")

    try:
        with conn:
            # 1. Drop each empty ERP table
            for table in EMPTY_TABLES:
                result = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,)
                ).fetchone()
                if result:
                    conn.execute(f"DROP TABLE IF EXISTS {table}")
                    print(f"  DROP TABLE {table}")
                else:
                    print(f"  SKIP (already gone): {table}")

            # 2. Delete schema_nodes rows for dropped tables
            placeholders = ",".join("?" * len(EMPTY_TABLES))
            deleted = conn.execute(
                f"DELETE FROM schema_nodes WHERE table_name IN ({placeholders})",
                EMPTY_TABLES
            ).rowcount
            print(f"  schema_nodes: deleted {deleted} rows")

            # 3. Delete ground_truth_table_usage rows for dropped tables
            deleted = conn.execute(
                f"DELETE FROM ground_truth_table_usage WHERE table_name IN ({placeholders})",
                EMPTY_TABLES
            ).rowcount
            print(f"  ground_truth_table_usage: deleted {deleted} rows")

            # 4. Delete schema_intent_queries rows for query files that now
            #    have no remaining referenced tables in the live DB.
            qf_placeholders = ",".join("?" * len(EXCLUSIVELY_EMPTY_QUERY_FILES))
            deleted = conn.execute(
                f"DELETE FROM schema_intent_queries WHERE query_file IN ({qf_placeholders})",
                EXCLUSIVELY_EMPTY_QUERY_FILES
            ).rowcount
            print(f"  schema_intent_queries: deleted {deleted} rows "
                  f"(exclusively-empty-table query files)")

            # 5. Remove schema_intent_concepts rows for intents that now have
            #    no remaining schema_intent_queries entries.
            deleted = conn.execute("""
                DELETE FROM schema_intent_concepts
                WHERE intent_id IN (
                    SELECT si.intent_id
                    FROM schema_intents si
                    LEFT JOIN schema_intent_queries siq
                        ON si.intent_id = siq.intent_id
                    WHERE siq.id IS NULL
                )
            """).rowcount
            print(f"  schema_intent_concepts: deleted {deleted} orphaned rows")

            # 6. Remove schema_intent_perspectives rows for orphaned intents.
            deleted = conn.execute("""
                DELETE FROM schema_intent_perspectives
                WHERE intent_id IN (
                    SELECT si.intent_id
                    FROM schema_intents si
                    LEFT JOIN schema_intent_queries siq
                        ON si.intent_id = siq.intent_id
                    WHERE siq.id IS NULL
                )
            """).rowcount
            print(f"  schema_intent_perspectives: deleted {deleted} orphaned rows")

            # 7. Remove orphaned schema_intents rows.
            deleted = conn.execute("""
                DELETE FROM schema_intents
                WHERE intent_id NOT IN (
                    SELECT DISTINCT intent_id FROM schema_intent_queries
                )
            """).rowcount
            print(f"  schema_intents: deleted {deleted} orphaned rows")

            # 8. Delete schema_concept_fields rows for dropped tables.
            deleted = conn.execute(
                f"DELETE FROM schema_concept_fields WHERE table_name IN ({placeholders})",
                EMPTY_TABLES
            ).rowcount
            print(f"  schema_concept_fields: deleted {deleted} rows")

            # 9. Delete schema_concepts that are now fully orphaned — no
            #    remaining intent_concepts references AND no concept_fields
            #    references (after step 8 removal).
            deleted = conn.execute("""
                DELETE FROM schema_concepts
                WHERE concept_id NOT IN (
                    SELECT concept_id FROM schema_intent_concepts
                )
                AND concept_id NOT IN (
                    SELECT concept_id FROM schema_concept_fields
                )
            """).rowcount
            print(f"  schema_concepts: deleted {deleted} orphaned rows")

            # 10. Delete schema_perspective_concepts rows for concepts that
            #     no longer exist in schema_concepts.
            deleted = conn.execute("""
                DELETE FROM schema_perspective_concepts
                WHERE concept_id NOT IN (
                    SELECT concept_id FROM schema_concepts
                )
            """).rowcount
            print(f"  schema_perspective_concepts: deleted {deleted} orphaned rows")

        print("\nMigration complete. Verifying ...")

        # Verification
        remaining = conn.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name IN ({placeholders})",
            EMPTY_TABLES
        ).fetchall()
        if remaining:
            print(f"WARNING: tables still present: {[r[0] for r in remaining]}")
            sys.exit(1)
        else:
            print(f"OK: all {len(EMPTY_TABLES)} empty tables removed")

        node_count = conn.execute(
            f"SELECT COUNT(*) FROM schema_nodes WHERE table_name IN ({placeholders})",
            EMPTY_TABLES
        ).fetchone()[0]
        print(f"OK: schema_nodes dangling rows = {node_count} (expect 0)")

        usage_count = conn.execute(
            f"SELECT COUNT(*) FROM ground_truth_table_usage WHERE table_name IN ({placeholders})",
            EMPTY_TABLES
        ).fetchone()[0]
        print(f"OK: ground_truth_table_usage dangling rows = {usage_count} (expect 0)")

        total_tables = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        print(f"OK: remaining tables in DB = {total_tables}")

    finally:
        conn.close()

    # 11. Purge stale ArangoDB vertices and edges for the dropped tables.
    purge_arango_stale_vertices(EMPTY_TABLES)


# ---------------------------------------------------------------------------
# ArangoDB purge — Step 11
# ---------------------------------------------------------------------------

def purge_arango_stale_vertices(tables: list) -> None:
    """Remove stale table/column vertices and contains edges from ArangoDB.

    For each table name in *tables* this function:
      - Deletes all ``column::TABLE.*`` vertices from the ``columns``
        collection (AQL prefix filter on ``table_name`` property).
      - Deletes the matching ``contains`` edges (same ``_key`` values as
        the column vertices, so one AQL pass covers both).
      - Deletes the ``table::TABLE`` vertex from the ``tables`` collection.

    Idempotent: already-absent documents are silently skipped (IGNORE).
    Skipped entirely when:
      - ``SKIP_ARANGO=1`` env var is set, OR
      - ``ARANGO_HOST`` or ``ARANGO_DB`` env vars are absent.
    """
    if os.environ.get("SKIP_ARANGO"):
        print("\n  [ArangoDB] SKIP_ARANGO=1 — skipping graph purge.")
        return

    arango_host = (
        os.environ.get("ARANGO_HOST") or
        os.environ.get("DATABASE_HOST", "")
    ).strip()
    arango_db_name = os.environ.get("ARANGO_DB", "").strip()

    if not arango_host or not arango_db_name:
        print(
            "\n  [ArangoDB] ARANGO_HOST / ARANGO_DB not set — "
            "skipping graph purge.  Run this step manually once ArangoDB "
            "is reachable, or re-run this migration with those env vars set."
        )
        return

    try:
        from arango import ArangoClient
    except ImportError:
        print(
            "\n  [ArangoDB] python-arango not installed — "
            "skipping graph purge."
        )
        return

    username = os.environ.get("ARANGO_USER", "root")
    password = os.environ.get("ARANGO_ROOT_PASSWORD", "")

    # Normalise host (ArangoCloud omits port in some env configs).
    if "arangodb.cloud" in arango_host and ":" not in arango_host.split("//", 1)[-1]:
        arango_host = f"{arango_host}:8529"

    try:
        client = ArangoClient(hosts=arango_host)
        db = client.db(arango_db_name, username=username, password=password)
        # Quick connectivity check
        db.collections()
    except Exception as exc:
        print(f"\n  [ArangoDB] Connection failed ({exc}) — skipping graph purge.")
        return

    print(f"\n  [ArangoDB] Connected to {arango_host}/{arango_db_name}")

    total_cols_removed = 0
    total_edges_removed = 0
    total_tables_removed = 0

    for table in tables:
        table_upper = table.strip().upper()
        table_vertex_key = f"table::{table_upper}"
        col_prefix = f"column::{table_upper}."

        # --- columns + contains edges ---
        # AQL: collect keys of all column vertices for this table, then remove
        # both the column vertex and the identically-keyed contains edge.
        aql_cols = """
        FOR doc IN columns
          FILTER doc.table_name == @tname
          REMOVE { _key: doc._key } IN columns OPTIONS { ignoreErrors: true }
          RETURN doc._key
        """
        aql_edges = """
        FOR doc IN contains
          FILTER STARTS_WITH(doc._key, @prefix)
          REMOVE { _key: doc._key } IN contains OPTIONS { ignoreErrors: true }
          RETURN doc._key
        """
        aql_table = """
        REMOVE { _key: @tkey } IN tables OPTIONS { ignoreErrors: true }
        RETURN @tkey
        """

        try:
            col_keys = list(db.aql.execute(aql_cols, bind_vars={"tname": table_upper}))
            total_cols_removed += len(col_keys)
        except Exception as exc:
            print(f"    WARNING: columns AQL for {table}: {exc}")

        try:
            edge_keys = list(db.aql.execute(aql_edges, bind_vars={"prefix": col_prefix}))
            total_edges_removed += len(edge_keys)
        except Exception as exc:
            print(f"    WARNING: contains AQL for {table}: {exc}")

        try:
            removed = list(db.aql.execute(aql_table, bind_vars={"tkey": table_vertex_key}))
            # REMOVE with ignoreErrors returns nothing on miss; len > 0 means removed
            total_tables_removed += 1 if removed else 0
        except Exception as exc:
            print(f"    WARNING: tables AQL for {table}: {exc}")

    print(
        f"  [ArangoDB] Purge complete: "
        f"{total_tables_removed} table vertices, "
        f"{total_cols_removed} column vertices, "
        f"{total_edges_removed} contains edges removed."
    )


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB
    print(f"Running drop_poc_tables migration on: {db_path}\n")
    run(db_path)
