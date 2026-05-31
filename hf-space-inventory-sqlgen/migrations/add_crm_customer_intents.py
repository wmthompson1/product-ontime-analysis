"""
Migration: Add CRM customer intents and ground truth query wiring.

Run once:
    cd hf-space-inventory-sqlgen
    python migrations/add_crm_customer_intents.py

Safe to re-run — uses INSERT OR IGNORE on all rows.

Category:    crm
Perspectives: Customer (5), Customer_Order (6)
SQL file:    app_schema/queries/crm_customer.sql
"""

import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app_schema", "manufacturing.db")

INTENTS = [
    {
        "intent_id": 15,
        "intent_name": "crm_customer_profile",
        "intent_category": "crm",
        "description": "Customer master + primary shipping address — the CRM_Join structural edge resolved for display",
        "typical_question": "Show me the customer profile and shipping address for account 42.",
        "primary_binding_key": "customer_id",
    },
    {
        "intent_id": 16,
        "intent_name": "crm_customer_revenue",
        "intent_category": "crm",
        "description": "Revenue per customer for a date range — joins customer, customer_address, and sales",
        "typical_question": "Show me revenue by customer from July 1st. Which customers drove the most sales?",
        "primary_binding_key": "start_date",
    },
    {
        "intent_id": 17,
        "intent_name": "crm_customer_address_lookup",
        "intent_category": "crm",
        "description": "Address-first territory lookup — find customers by city or state",
        "typical_question": "Which customers are in California? Show me all ship-to addresses in the Southwest.",
        "primary_binding_key": "state",
    },
]

# crm_customer_profile → Customer (5) only
# crm_customer_revenue → Customer (5) + Customer_Order (6) — revenue bridges both
# crm_customer_address_lookup → Customer (5) only
INTENT_PERSPECTIVES = [
    {"intent_id": 15, "perspective_id": 5, "explanation": "crm_customer_profile within Customer perspective"},
    {"intent_id": 16, "perspective_id": 5, "explanation": "crm_customer_revenue within Customer perspective"},
    {"intent_id": 16, "perspective_id": 6, "explanation": "crm_customer_revenue also within Customer_Order perspective — revenue bridges CRM and order fulfillment"},
    {"intent_id": 17, "perspective_id": 5, "explanation": "crm_customer_address_lookup within Customer perspective"},
]

INTENT_QUERIES = [
    {
        "intent_id": 15,
        "query_category": "crm",
        "query_file": "crm_customer.sql",
        "query_index": 1,
        "query_name": "Customer profile with shipping address",
    },
    {
        "intent_id": 16,
        "query_category": "crm",
        "query_file": "crm_customer.sql",
        "query_index": 2,
        "query_name": "Revenue by customer with address enrichment",
    },
    {
        "intent_id": 17,
        "query_category": "crm",
        "query_file": "crm_customer.sql",
        "query_index": 3,
        "query_name": "Customer address territory lookup",
    },
]


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for row in INTENTS:
        cur.execute("""
            INSERT OR IGNORE INTO schema_intents
                (intent_id, intent_name, intent_category, description, typical_question, primary_binding_key)
            VALUES (:intent_id, :intent_name, :intent_category, :description, :typical_question, :primary_binding_key)
        """, row)
        print(f"  intent {row['intent_name']}: {cur.rowcount} inserted")

    for row in INTENT_PERSPECTIVES:
        cur.execute("""
            INSERT OR IGNORE INTO schema_intent_perspectives
                (intent_id, perspective_id, intent_factor_weight, explanation)
            VALUES (:intent_id, :perspective_id, 1, :explanation)
        """, row)
        print(f"  intent_perspective {row['intent_id']}↔{row['perspective_id']}: {cur.rowcount} inserted")

    for row in INTENT_QUERIES:
        cur.execute("""
            INSERT OR IGNORE INTO schema_intent_queries
                (intent_id, query_category, query_file, query_index, query_name)
            VALUES (:intent_id, :query_category, :query_file, :query_index, :query_name)
        """, row)
        print(f"  intent_query '{row['query_name']}': {cur.rowcount} inserted")

    conn.commit()
    conn.close()
    print("\nDone. CRM customer intents wired successfully.")


if __name__ == "__main__":
    print(f"DB: {os.path.abspath(DB_PATH)}")
    run()
