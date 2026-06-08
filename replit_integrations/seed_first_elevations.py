"""Seed the first batch of SME-approved semantic elevations into SQLite.

This is the *content* that lights up the node-guarded ``elevates`` scaffolding in
``export_graph_metadata.py``. SQLite is the source of truth; running this then
re-running the exporter + loader produces the corresponding ``elevates`` edges.

Idempotent: every table carries a UNIQUE natural key
(schema_concepts.concept_name, schema_perspective_concepts(perspective_id,
concept_id), schema_concept_fields(table_name, field_name, concept_id)), so
re-running is a no-op via INSERT OR IGNORE / name lookups.

First batch (each is a bounded discriminator on a canonical business column):
  * inventory_transaction.site_id -> Inventory_Transactions / WarehouseLocation
      inventory is traced by stock *moves*; site_id traces the move to a warehouse
  * invoice_header.three_way_match_status -> Payables / ThreeWayMatchState
      AP PO/receipt/invoice match state
  * customer_order.status -> Receivables / OrderAccountingState (existing concept)
      customer orders are traced at *shipment*, which is the AR revenue-recognition
      trigger -> the existing "revenue recognition" order-state concept fits
"""
import os
import sqlite3

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "hf-space-inventory-sqlgen", "app_schema", "manufacturing.db",
)

# concept_name -> (concept_type, domain, description). Concepts to ensure exist.
# OrderAccountingState is intentionally absent: it already ships in the schema
# and we only *reference* it (we never recreate existing SME vocabulary).
NEW_CONCEPTS = {
    "WarehouseLocation": (
        "classification", "operations",
        "Warehouse/site a stock move is distributed to (inventory traced by move)",
    ),
    "ThreeWayMatchState": (
        "state", "finance",
        "PO/receipt/invoice three-way match status used to validate AP invoices",
    ),
}

# (perspective_name, concept_name, table, column, weight, context_hint)
ELEVATIONS = [
    ("Inventory_Transactions", "WarehouseLocation",
     "inventory_transaction", "site_id", 3,
     "Inventory move traced to its warehouse site"),
    ("Payables", "ThreeWayMatchState",
     "invoice_header", "three_way_match_status", 3,
     "AP three-way match validation state"),
    ("Receivables", "OrderAccountingState",
     "customer_order", "status", 3,
     "Order status at shipment = revenue recognition (AR lens)"),
]


def _concept_id(cur, name: str) -> int:
    row = cur.execute(
        "SELECT concept_id FROM schema_concepts WHERE concept_name = ?", (name,)
    ).fetchone()
    if row is None:
        raise SystemExit(f"ERROR: concept '{name}' not found and not in NEW_CONCEPTS")
    return row[0]


def _perspective_id(cur, name: str) -> int:
    row = cur.execute(
        "SELECT perspective_id FROM schema_perspectives WHERE perspective_name = ?",
        (name,),
    ).fetchone()
    if row is None:
        raise SystemExit(f"ERROR: perspective '{name}' not found")
    return row[0]


def main() -> int:
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"ERROR: manufacturing.db not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        for name, (ctype, domain, desc) in NEW_CONCEPTS.items():
            cur.execute(
                "INSERT OR IGNORE INTO schema_concepts "
                "(concept_name, concept_type, description, domain) VALUES (?,?,?,?)",
                (name, ctype, domain, desc),
            )

        edges_planned = 0
        for persp, concept, table, column, weight, hint in ELEVATIONS:
            pid = _perspective_id(cur, persp)
            cid = _concept_id(cur, concept)
            cur.execute(
                "INSERT OR IGNORE INTO schema_perspective_concepts "
                "(perspective_id, concept_id, relationship_type, priority_weight) "
                "VALUES (?,?, 'USES_DEFINITION', ?)",
                (pid, cid, weight),
            )
            cur.execute(
                "INSERT OR IGNORE INTO schema_concept_fields "
                "(table_name, field_name, concept_id, is_primary_meaning, context_hint) "
                "VALUES (?,?,?,1,?)",
                (table, column, cid, hint),
            )
            edges_planned += 1
            print(f"  elevation: {persp:24} {table}.{column} -> {concept}")

        conn.commit()
    finally:
        conn.close()

    print(f"seeded {len(NEW_CONCEPTS)} concept(s), {edges_planned} elevation(s) "
          f"(idempotent). Re-run export_graph_metadata.py to emit elevates edges.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
