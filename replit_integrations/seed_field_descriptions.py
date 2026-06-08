"""Seed SME-facing field descriptions into ``api_field_descriptions`` (SQLite).

This is the SME-meaningful overlay that should take PRECEDENCE over the internal,
abstract concept names (e.g. "QuantityBasisEngineering") wherever a meaning is
surfaced to a human. ``api_field_descriptions`` is the local stand-in for the
company DAB (data-abstraction / field-dictionary) source in the private repo:
here we author plain-language drafts; an SME (or the DAB feed) is the authority
and may overwrite them.

Scope: the business columns that currently carry an SME-approved elevation
(schema_concept_fields). Staging (``stg_``) columns are intentionally skipped —
they are not part of the curated business vocabulary.

Idempotent: ``api_field_descriptions`` has PK (table_name, column_name); this
upserts, so re-running refreshes the drafts without creating duplicates.
"""
import os
import sqlite3

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "hf-space-inventory-sqlgen", "app_schema", "manufacturing.db",
)

# Must match the app defaults (app.py SQL_MCP_SOURCE_DATABASE / _DEFAULT_SCHEMA)
# so the schema browser overlay and the SolderEngine lookup find these rows.
SOURCE_DATABASE = os.environ.get("SQL_MCP_SOURCE_DATABASE", "manufacturing")
SCHEMA_NAME = os.environ.get("SQL_MCP_DEFAULT_SCHEMA", "dbo")

# (table_name, column_name, display_name, description, example_value)
FIELD_DESCRIPTIONS = [
    ("requirement", "component_type", "Requirement Component Type",
     "Whether a resource requirement belongs to a PART (the as-designed routing "
     "standard — engineering, costed per unit) or a WORK_ORDER (as-built actuals "
     "— manufacturing, costed per batch). This is the engineering-vs-manufacturing "
     "differentiator.", "PART"),
    ("work_order", "quantity", "Build Quantity",
     "Number of units the work order releases to the floor (the lot / batch size). "
     "One unit reflects the engineering per-unit standard; greater than one is a "
     "manufacturing batch.", "50"),
    ("work_order", "status", "Work Order Status",
     "Shop-floor lifecycle stage of the work order: open, released, in process, "
     "complete, or closed.", "IN PROCESS"),
    ("operation", "status", "Operation Status",
     "Execution state of a routing step on the shop floor: queued, started / "
     "running, or complete.", "COMPLETE"),
    ("customer_order", "status", "Order Status",
     "Where a customer order sits in its lifecycle: entered, released, in process, "
     "shipped, invoiced, or closed. At 'shipped' the order is recognized as "
     "revenue.", "SHIPPED"),
    ("customer_order_line", "order_qty", "Order Quantity",
     "How many units the customer ordered on this line. Drives the production "
     "batch size; the per-unit engineering standard is multiplied by this "
     "quantity.", "25"),
    ("part", "part_class", "Part Class (Make / Buy)",
     "How a part is sourced: manufactured in-house, purchased, raw material, "
     "hardware, or outside service. Reflects engineering's make-vs-buy intent.",
     "MAKE"),
    ("inventory_transaction", "site_id", "Warehouse / Site",
     "The stockroom or plant site where this inventory move happened. Inventory is "
     "traced at the move, so this is where the material physically went.",
     "PLANT-1"),
    ("inventory_transaction", "type", "Transaction Type",
     "Direction of the stock movement: a receipt into stock (in) versus an issue "
     "out to a work order or shipment (out).", "ISSUE"),
    ("purchase_order", "status", "PO Status",
     "Lifecycle stage of a purchase order: open, approved, partially or fully "
     "received, or closed.", "RECEIVED"),
    ("invoice_header", "three_way_match_status", "Three-Way Match Status",
     "Result of matching a supplier invoice against its purchase order and "
     "receiving record before it can be paid: matched, on hold for price / "
     "quantity variance, or unmatched.", "MATCHED"),
    ("receiving", "inspection_status", "Receiving Inspection Status",
     "Quality disposition of a received shipment: pending inspection, passed, or "
     "failed / rejected.", "PASS"),
    ("certification", "status", "Certification Status",
     "Whether a certification is currently valid: active, expired, revoked, or "
     "pending renewal.", "ACTIVE"),
    ("certification", "cert_type", "Certification Type",
     "The kind of supplier / material certification on file — e.g. Certificate of "
     "Conformance, First Article Inspection, PPAP, FAA 8130-3, or Material Test "
     "Report.", "CoC"),
]


def main() -> int:
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"ERROR: manufacturing.db not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        for table, column, display, desc, example in FIELD_DESCRIPTIONS:
            cur.execute(
                """
                INSERT INTO api_field_descriptions
                    (source_database, schema_name, table_name, column_name,
                     display_name, description, example_value, updated_at)
                VALUES (?,?,?,?,?,?,?, CURRENT_TIMESTAMP)
                ON CONFLICT(source_database, schema_name, table_name, column_name)
                DO UPDATE SET
                    display_name  = excluded.display_name,
                    description   = excluded.description,
                    example_value = excluded.example_value,
                    updated_at    = CURRENT_TIMESTAMP
                """,
                (SOURCE_DATABASE, SCHEMA_NAME, table, column, display, desc,
                 example),
            )
            print(f"  field desc: {table}.{column} -> {display}")
        conn.commit()
    finally:
        conn.close()

    print(f"seeded {len(FIELD_DESCRIPTIONS)} field description(s) (idempotent; "
          f"stand-in for DAB).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
