"""Seed the SME-approved semantic elevations into SQLite (authoritative manifest).

This is the *content* that lights up the node-guarded ``elevates`` scaffolding in
``export_graph_metadata.py``. SQLite is the source of truth; running this then
re-running the exporter + loader produces the corresponding ``elevates`` edges.

Idempotent: every table carries a UNIQUE natural key
(schema_concepts.concept_name; schema_perspective_concepts(perspective_id,
concept_id); schema_concept_fields(table_name, field_name, concept_id)), so
re-running is a no-op via INSERT OR IGNORE / name lookups. This file holds the
full approved list across all batches — run it once to reproduce every elevation.

Curation rule: each elevation is a bounded categorical discriminator
(status / type / class / location) on a canonical business column — not a unique
id, date, free-text label, or continuous measure.
"""
import os
import sqlite3

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "hf-space-inventory-sqlgen", "app_schema", "manufacturing.db",
)

# concept_name -> (concept_type, domain, description). Concepts to ensure exist.
# Concepts NOT listed here (e.g. OrderAccountingState) are existing SME vocabulary
# that we only *reference* — we never recreate shipped concepts.
NEW_CONCEPTS = {
    "WarehouseLocation": (
        "classification", "operations",
        "Warehouse/site a stock move is distributed to (inventory traced by move)",
    ),
    "ThreeWayMatchState": (
        "state", "finance",
        "PO/receipt/invoice three-way match status used to validate AP invoices",
    ),
    "WorkOrderLifecycleState": (
        "state", "operations",
        "Work order lifecycle stage on the shop floor (Open->Released->In "
        "Process->Complete->Closed)",
    ),
    "PartSourcingClass": (
        "classification", "operations",
        "How a part is sourced: engineered/made vs bought vs raw vs hardware vs "
        "outside service (engineering make/buy intent)",
    ),
    "StockMovementDirection": (
        "classification", "operations",
        "Direction of an inventory transaction: stock receipt (in) vs issue (out)",
    ),
    "OperationExecutionState": (
        "state", "operations",
        "Execution state of a routing operation (queued -> started -> complete)",
    ),
    "QuantityBasisEngineering": (
        "metric", "operations",
        "Quantity read through the engineering lens: a per-unit, as-designed "
        "requirement basis (engineering normalizes material needs to a single unit)",
    ),
    "QuantityBasisManufacturing": (
        "metric", "operations",
        "Quantity read through the manufacturing lens: a production batch / lot "
        "size to build or fulfill (qty > 1)",
    ),
    "PurchaseOrderLifecycleState": (
        "state", "procurement",
        "Lifecycle state of a purchase order (open -> approved -> received -> closed)",
    ),
    "ReceivingInspectionState": (
        "state", "quality",
        "Inspection disposition of a received shipment (pending -> pass / fail)",
    ),
    "CertificationStatusState": (
        "state", "quality",
        "Validity state of a certification (active / expired / revoked / pending)",
    ),
    "CertificationType": (
        "classification", "quality",
        "Kind of certification held (material / process / quality-system / etc.)",
    ),
    "RequirementBasisEngineering": (
        "classification", "operations",
        "Requirement read through the engineering lens: an as-designed routing "
        "standard on a PART component (per-unit basis); component_type='PART'",
    ),
    "RequirementBasisManufacturing": (
        "classification", "operations",
        "Requirement read through the manufacturing lens: as-built actuals on a "
        "WORK_ORDER component (batch basis); component_type='WORK_ORDER'",
    ),
}

# (perspective_name, concept_name, table, column, weight, context_hint)
ELEVATIONS = [
    # --- batch 1 ---
    ("Inventory_Transactions", "WarehouseLocation",
     "inventory_transaction", "site_id", 3,
     "Inventory move traced to its warehouse site"),
    ("Payables", "ThreeWayMatchState",
     "invoice_header", "three_way_match_status", 3,
     "AP three-way match validation state"),
    ("Receivables", "OrderAccountingState",
     "customer_order", "status", 3,
     "Order status at shipment = revenue recognition (AR lens)"),
    # --- batch 2 ---
    ("Work_Orders", "WorkOrderLifecycleState",
     "work_order", "status", 3,
     "Work order shop-floor lifecycle stage"),
    ("Parts", "PartSourcingClass",
     "part", "part_class", 3,
     "Make/buy/raw sourcing class (engineering design intent)"),
    ("Inventory_Transactions", "StockMovementDirection",
     "inventory_transaction", "type", 3,
     "Stock in vs out direction of the move"),
    ("Manufacturing", "OperationExecutionState",
     "operation", "status", 3,
     "Routing operation execution state"),
    # --- batch 3: same quantity column, two perspective lenses ---
    # No engineering quantity column exists (no BOM table); the engineering vs
    # manufacturing contrast is modeled as dual meaning on the batch-quantity
    # columns. order_qty / work_order.quantity are the multiplier that bridges a
    # per-unit (engineering, =1) requirement to a batch (manufacturing, >1).
    ("Engineering", "QuantityBasisEngineering",
     "work_order", "quantity", 3,
     "Per-unit design basis; batch = N x per-unit requirement"),
    ("Manufacturing", "QuantityBasisManufacturing",
     "work_order", "quantity", 3,
     "Production batch / lot size (qty > 1)"),
    ("Engineering", "QuantityBasisEngineering",
     "customer_order_line", "order_qty", 3,
     "Per-unit design basis multiplier for the ordered line"),
    ("Manufacturing", "QuantityBasisManufacturing",
     "customer_order_line", "order_qty", 3,
     "Ordered quantity driving the manufacturing batch (qty > 1)"),
    # --- batch 4: procurement + quality status/type discriminators ---
    ("Payables", "PurchaseOrderLifecycleState",
     "purchase_order", "status", 3,
     "Purchase order lifecycle state"),
    ("Quality", "ReceivingInspectionState",
     "receiving", "inspection_status", 3,
     "Inspection disposition of a received shipment"),
    ("Quality", "CertificationStatusState",
     "certification", "status", 3,
     "Validity state of a certification"),
    ("Quality", "CertificationType",
     "certification", "cert_type", 3,
     "Kind of certification held"),
    # --- batch 5: requirement.component_type — the value-level engineering vs
    # manufacturing differentiator. Unlike the quantity dual-lens (batch 3),
    # here the column VALUE selects the perspective: PART routes to Engineering,
    # WORK_ORDER routes to Manufacturing. The value condition is carried in the
    # context_hint (the model's "when this meaning applies" slot).
    ("Engineering", "RequirementBasisEngineering",
     "requirement", "component_type", 3,
     "component_type = 'PART' — as-designed routing standard (per-unit, engineering)"),
    ("Manufacturing", "RequirementBasisManufacturing",
     "requirement", "component_type", 3,
     "component_type = 'WORK_ORDER' — as-built actuals (batch, manufacturing)"),
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
        # Additive guard: older databases predate ``component_index``. Add it in
        # place so this manifest stays self-contained (idempotent).
        cur.execute("PRAGMA table_info(schema_concept_fields)")
        if "component_index" not in {row[1] for row in cur.fetchall()}:
            cur.execute(
                "ALTER TABLE schema_concept_fields "
                "ADD COLUMN component_index INTEGER NOT NULL DEFAULT 1"
            )

        for name, (ctype, domain, desc) in NEW_CONCEPTS.items():
            cur.execute(
                "INSERT OR IGNORE INTO schema_concepts "
                "(concept_name, concept_type, description, domain) VALUES (?,?,?,?)",
                (name, ctype, domain, desc),
            )

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
            print(f"  elevation: {persp:24} {table}.{column} -> {concept}")

        # Number each field's definitions deterministically: per (table, field)
        # the primary meaning is 1 and each further definition increments. This
        # is the authoritative ``component_index`` the exporter carries into the
        # graph as ``field_component`` — authored in SQLite, never inferred at
        # runtime. Ordered by concept_id so re-running is idempotent (same DB =
        # same numbering). Requires SQLite >= 3.25 for window functions.
        cur.execute(
            """
            WITH numbered AS (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY table_name, field_name
                           ORDER BY concept_id
                       ) AS rn
                FROM schema_concept_fields
            )
            UPDATE schema_concept_fields
               SET component_index = (SELECT rn FROM numbered
                                       WHERE numbered.id = schema_concept_fields.id)
            """
        )

        conn.commit()
    finally:
        conn.close()

    print(f"seeded {len(NEW_CONCEPTS)} concept(s), {len(ELEVATIONS)} elevation(s) "
          f"(idempotent). Re-run export_graph_metadata.py to emit elevates edges.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
