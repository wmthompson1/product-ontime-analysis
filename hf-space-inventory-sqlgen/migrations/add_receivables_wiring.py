"""
Migration: Wire the Receivables side of the semantic layer.

The OrderAccountingState concept (customer_order.status, Receivables
perspective) had ZERO intent links, so the selector chain dead-ended at
"No analytical intent elevates this concept". This migration:

  1. Adds intent order_revenue_recognition (intent 19) — revenue
     recognition roll-up of the customer order book.
  2. Links it to the Receivables perspective.
  3. Wires it to the three ground-truth queries in receivables.sql.
  4. Links it to the OrderAccountingState concept so the
     Table → Column → Concept → Intent → Query chain is complete.

Run once:
    cd hf-space-inventory-sqlgen
    python migrations/add_receivables_wiring.py

Safe to re-run — uses INSERT OR IGNORE on all rows.
"""

import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

NEW_INTENT = {
    "intent_id": 19,
    "intent_name": "order_revenue_recognition",
    "intent_category": "receivables",
    "description": "Revenue recognition roll-up of the customer order book — recognized (Closed), billable (Shipped), and backlog (Open) value, per state and per customer",
    "typical_question": "How much order revenue is recognized vs billable vs backlog? Which customers carry the most unbilled AR?",
    "primary_binding_key": "start_date",
}

NEW_INTENT_PERSPECTIVES = [
    {"intent_id": 19, "perspective_id": 5, "explanation": "order_revenue_recognition within Receivables perspective — the accounting read of the order book"},
]

NEW_INTENT_QUERIES = [
    {"intent_id": 19, "query_category": "receivables",
     "query_file": "receivables.sql", "query_index": 0,
     "query_name": "Order Revenue Recognition Status"},
    {"intent_id": 19, "query_category": "receivables",
     "query_file": "receivables.sql", "query_index": 1,
     "query_name": "Customer AR Exposure"},
    {"intent_id": 19, "query_category": "receivables",
     "query_file": "receivables.sql", "query_index": 2,
     "query_name": "Open Order Backlog Aging"},
]

# Concept link: order_revenue_recognition ← OrderAccountingState
# (resolves to customer_order.status) so the intent — and its queries —
# are reachable through the Table → Column → Concept chain.
NEW_INTENT_CONCEPT = {
    "intent_id": 19,
    "concept_name": "OrderAccountingState",
    "explanation": "Revenue recognition is read from customer_order.status; OrderAccountingState is the concept that anchors the chain",
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

    # 2. Perspective link
    for row in NEW_INTENT_PERSPECTIVES:
        cur.execute("""
            INSERT OR IGNORE INTO schema_intent_perspectives
                (intent_id, perspective_id, intent_factor_weight, explanation)
            VALUES (:intent_id, :perspective_id, 1, :explanation)
        """, row)
        print(f"  intent_perspective {row['intent_id']}↔{row['perspective_id']}: {cur.rowcount} inserted")

    # 3. Query wiring
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
    print(f"  intent_concept 19↔{NEW_INTENT_CONCEPT['concept_name']}: {cur.rowcount} inserted")

    conn.commit()
    conn.close()
    print("\nDone. Receivables wiring complete.")


if __name__ == "__main__":
    print(f"DB: {os.path.abspath(DB_PATH)}")
    run()
