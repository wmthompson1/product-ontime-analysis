"""
Migration: Add Customer_Order perspective, intents, and ground truth query wiring.

Run once:
    cd hf-space-inventory-sqlgen
    python migrations/add_customer_order_perspective.py

Safe to re-run — uses INSERT OR IGNORE on all rows.
"""

import sqlite3, os, sys

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

PERSPECTIVE = {
    "perspective_id": 6,
    "perspective_name": "Customer_Order",
    "description": "Order fulfillment, delivery commitment, and customer-facing quality exposure",
    "stakeholder_role": "Sales Manager, Account Manager, Customer Success",
    "priority_focus": "On-time delivery, fill rate, defect exposure on customer orders",
}

# Three intents — one per query in customer_order.sql
INTENTS = [
    {
        "intent_id": 12,
        "intent_name": "customer_order_lifecycle",
        "intent_category": "customer_order",
        "description": "Order fulfillment status — completion rate vs plan by product line",
        "typical_question": "Show me order completion for July. Which lines are behind schedule?",
        "primary_binding_key": "start_date",
    },
    {
        "intent_id": 13,
        "intent_name": "customer_order_delivery",
        "intent_category": "customer_order",
        "description": "Delivery performance to customer — on-time rate, fill rate, quality score",
        "typical_question": "What is our on-time delivery rate from July 1st?",
        "primary_binding_key": "start_date",
    },
    {
        "intent_id": 14,
        "intent_name": "customer_order_quality_exposure",
        "intent_category": "customer_order",
        "description": "Defect exposure on customer-facing orders — severity breakdown and estimated rework cost",
        "typical_question": "Show quality exposure on Aerospace orders since July 1st.",
        "primary_binding_key": "start_date",
    },
]

# Each intent maps to the Customer_Order perspective (6);
# delivery also maps to Customer (5), quality also maps to Quality (1)
INTENT_PERSPECTIVES = [
    {"intent_id": 12, "perspective_id": 6, "explanation": "customer_order_lifecycle within Customer_Order perspective"},
    {"intent_id": 13, "perspective_id": 6, "explanation": "customer_order_delivery within Customer_Order perspective"},
    {"intent_id": 13, "perspective_id": 5, "explanation": "customer_order_delivery also within Customer perspective"},
    {"intent_id": 14, "perspective_id": 6, "explanation": "customer_order_quality_exposure within Customer_Order perspective"},
    {"intent_id": 14, "perspective_id": 1, "explanation": "customer_order_quality_exposure also within Quality perspective"},
]

INTENT_QUERIES = [
    {
        "intent_id": 12,
        "query_category": "customer_order",
        "query_file": "customer_order.sql",
        "query_index": 1,
        "query_name": "Order lifecycle fulfillment status",
    },
    {
        "intent_id": 13,
        "query_category": "customer_order",
        "query_file": "customer_order.sql",
        "query_index": 2,
        "query_name": "Customer delivery performance",
    },
    {
        "intent_id": 14,
        "query_category": "customer_order",
        "query_file": "customer_order.sql",
        "query_index": 3,
        "query_name": "Customer order quality exposure",
    },
]


def run():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Perspective
    cur.execute("""
        INSERT OR IGNORE INTO schema_perspectives
            (perspective_id, perspective_name, description, stakeholder_role, priority_focus)
        VALUES (:perspective_id, :perspective_name, :description, :stakeholder_role, :priority_focus)
    """, PERSPECTIVE)
    print(f"  perspective: {cur.rowcount} inserted (0 = already present)")

    # 2. Intents
    for row in INTENTS:
        cur.execute("""
            INSERT OR IGNORE INTO schema_intents
                (intent_id, intent_name, intent_category, description, typical_question, primary_binding_key)
            VALUES (:intent_id, :intent_name, :intent_category, :description, :typical_question, :primary_binding_key)
        """, row)
        print(f"  intent {row['intent_name']}: {cur.rowcount} inserted")

    # 3. Intent ↔ Perspective links
    for row in INTENT_PERSPECTIVES:
        cur.execute("""
            INSERT OR IGNORE INTO schema_intent_perspectives
                (intent_id, perspective_id, intent_factor_weight, explanation)
            VALUES (:intent_id, :perspective_id, 1, :explanation)
        """, row)
        print(f"  intent_perspective {row['intent_id']}↔{row['perspective_id']}: {cur.rowcount} inserted")

    # 4. Intent ↔ Query wiring
    for row in INTENT_QUERIES:
        cur.execute("""
            INSERT OR IGNORE INTO schema_intent_queries
                (intent_id, query_category, query_file, query_index, query_name)
            VALUES (:intent_id, :query_category, :query_file, :query_index, :query_name)
        """, row)
        print(f"  intent_query '{row['query_name']}': {cur.rowcount} inserted")

    conn.commit()
    conn.close()
    print("\nDone. Customer_Order perspective wired successfully.")


if __name__ == "__main__":
    print(f"DB: {os.path.abspath(DB_PATH)}")
    run()
