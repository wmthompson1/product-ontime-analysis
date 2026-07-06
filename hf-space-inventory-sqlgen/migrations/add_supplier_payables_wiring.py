"""
Migration: Re-wire supplier intents to reflect the payables framing.

Changes:
  1. Add Finance (2) cross-link to supplier_scorecard (intent 4) — was Quality-only,
     but late-rate_pct is an AP signal that drives payment-term decisions.
  2. Add new intent supplier_payables_exposure (intent 18) — pure AP roll-up,
     Finance perspective only, maps to query 3 in supplier_performance.sql.

Run once:
    cd hf-space-inventory-sqlgen
    python migrations/add_supplier_payables_wiring.py

Safe to re-run — uses INSERT OR IGNORE on all rows.
"""

import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

NEW_INTENT = {
    "intent_id": 18,
    "intent_name": "supplier_payables_exposure",
    "intent_category": "supplier_performance",
    "description": "AP exposure roll-up by supplier — total units received, estimated payables, and early-pay eligibility flag",
    "typical_question": "Show me payables exposure by vendor from July 1st. What do we owe suppliers this quarter?",
    "primary_binding_key": "start_date",
}

NEW_INTENT_PERSPECTIVES = [
    # supplier_scorecard (4) already has Quality (1) — add Finance (2)
    {"intent_id": 4,  "perspective_id": 2, "explanation": "supplier_scorecard within Finance perspective — late-rate drives AP penalty and payment-term decisions"},
    # supplier_payables_exposure → Finance only
    {"intent_id": 18, "perspective_id": 2, "explanation": "supplier_payables_exposure within Finance perspective — pure AP roll-up"},
]

NEW_INTENT_QUERIES = [
    # NOTE: index 2 ("Supplier Payables Exposure", cost-proxy estimate) is
    # deliberately NOT wired — it reads daily_deliveries / product_lines,
    # which are removed from the schema, and its estimate framing conflicts
    # with the SME definition: AP exposure = TOTAL DUE from the payables ledger.
    # index 3 — exposure = TOTAL DUE (sum of unpaid invoice amounts)
    {"intent_id": 18, "query_category": "supplier_performance",
     "query_file": "supplier_performance.sql", "query_index": 3,
     "query_name": "Supplier AP Total Due"},
    # index 4 — AP aging buckets
    {"intent_id": 18, "query_category": "supplier_performance",
     "query_file": "supplier_performance.sql", "query_index": 4,
     "query_name": "AP Aging by Supplier"},
    # index 5 — three-way match exception holds
    {"intent_id": 18, "query_category": "supplier_performance",
     "query_file": "supplier_performance.sql", "query_index": 5,
     "query_name": "Three-Way Match Exceptions"},
]

# Concept link: supplier_payables_exposure ← ThreeWayMatchState
# (resolves to payables.three_way_match_status) so the intent — and its
# queries — are reachable through the Table → Column → Concept chain.
NEW_INTENT_CONCEPT = {
    "intent_id": 18,
    "concept_name": "ThreeWayMatchState",
    "explanation": "AP exposure is read from the payables ledger; ThreeWayMatchState is the payables-table concept that anchors the chain",
}


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. New intent
    cur.execute("""
        INSERT OR IGNORE INTO schema_intents
            (intent_id, intent_name, intent_category, description, typical_question, primary_binding_key)
        VALUES (:intent_id, :intent_name, :intent_category, :description, :typical_question, :primary_binding_key)
    """, NEW_INTENT)
    print(f"  intent {NEW_INTENT['intent_name']}: {cur.rowcount} inserted")

    # 2. Perspective cross-links
    for row in NEW_INTENT_PERSPECTIVES:
        cur.execute("""
            INSERT OR IGNORE INTO schema_intent_perspectives
                (intent_id, perspective_id, intent_factor_weight, explanation)
            VALUES (:intent_id, :perspective_id, 1, :explanation)
        """, row)
        print(f"  intent_perspective {row['intent_id']}↔{row['perspective_id']}: {cur.rowcount} inserted")

    # 3. Query wiring for new intent
    # Self-heal: an earlier version of this migration inserted index 3 with a
    # name that matches no "-- Query:" marker in the file, so it never resolved.
    cur.execute("""
        DELETE FROM schema_intent_queries
        WHERE intent_id = 18 AND query_file = 'supplier_performance.sql'
          AND query_name IN (
              'Supplier AP exposure and payment recommendation',
              'Supplier Payables Exposure'
          )
    """)
    if cur.rowcount:
        print(f"  removed {cur.rowcount} stale intent_query row(s)")
    for row in NEW_INTENT_QUERIES:
        cur.execute("""
            INSERT OR IGNORE INTO schema_intent_queries
                (intent_id, query_category, query_file, query_index, query_name)
            VALUES (:intent_id, :query_category, :query_file, :query_index, :query_name)
        """, row)
        print(f"  intent_query '{row['query_name']}': {cur.rowcount} inserted")

    # 4. Concept link so the intent is reachable via Table→Column→Concept chain
    cur.execute("""
        INSERT OR IGNORE INTO schema_intent_concepts
            (intent_id, concept_id, intent_factor_weight, explanation)
        SELECT :intent_id, c.concept_id, 1, :explanation
        FROM schema_concepts c
        WHERE c.concept_name = :concept_name
    """, NEW_INTENT_CONCEPT)
    print(f"  intent_concept 18↔{NEW_INTENT_CONCEPT['concept_name']}: {cur.rowcount} inserted")

    conn.commit()
    conn.close()
    print("\nDone. Supplier → payables wiring complete.")


if __name__ == "__main__":
    print(f"DB: {os.path.abspath(DB_PATH)}")
    run()
