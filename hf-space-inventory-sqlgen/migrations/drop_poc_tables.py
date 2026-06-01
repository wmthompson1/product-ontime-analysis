"""
Migration: drop_poc_tables.py
==============================
Drops 21 empty PoC tables that were created during early development but
never populated.  Also retires their orphaned schema metadata.

Re-runnable: every step is idempotent (DROP TABLE IF EXISTS, DELETE with
WHERE, etc.).  Runs inside a single transaction so it is fully atomic.

Usage:
    python hf-space-inventory-sqlgen/migrations/drop_poc_tables.py

Or with an explicit DB path:
    python hf-space-inventory-sqlgen/migrations/drop_poc_tables.py /path/to/manufacturing.db
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


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB
    print(f"Running drop_poc_tables migration on: {db_path}\n")
    run(db_path)
