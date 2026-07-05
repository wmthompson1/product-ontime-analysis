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
    ("work_order", "desired_rls_date", "Desired Release Date",
     "The date the planner wants the job released to the floor — on or before its "
     "first step begins — so material and capacity are lined up when work starts.",
     "2025-04-09"),
    ("work_order", "sched_start_date", "Scheduled Start Date",
     "When the job is planned to begin: the start of its earliest routing step. "
     "Read from the operation schedule, so it reflects when the first step is set "
     "to begin on the floor.", "2025-04-09"),
    ("work_order", "sched_finish_date", "Scheduled Finish Date",
     "When the job is planned to be finished: the finish of its last routing step. "
     "Read from the operation schedule, so it reflects the planned completion of "
     "the whole job.", "2025-04-21"),
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
    ("payables", "three_way_match_status", "Three-Way Match Status",
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
    # SQL Server user-defined field (no SQLite twin column): the human-label
    # mapping the SQLMesh orchestrator resolves to the physical column USER_DEF_1.
    ("user_def_fields", "USER_DEF_1", "Legacy Manufacturer Code",
     "Pre-migration manufacturer / vendor code carried in an ERP user-defined "
     "field (USER_DEF_1). Used to reconcile parts against the legacy system "
     "during the data migration; masked deterministically before staging.",
     "MFR-00417"),
]


def _seed_curated() -> int:
    """Upsert the SME-curated field descriptions. Returns the count seeded."""
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
    return len(FIELD_DESCRIPTIONS)


def _curated_lookup() -> dict:
    """{(table, column): (display, description, example)} from FIELD_DESCRIPTIONS."""
    return {
        (t, c): (display, desc, example)
        for (t, c, display, desc, example) in FIELD_DESCRIPTIONS
    }


def _build_graph_csv(use_ai: bool, verbose: bool = True) -> dict:
    """Author/refresh the committed field_descriptions.csv for graph columns.

    The CSV is the SME-editable, version-controlled source of truth that boots
    into ``api_field_descriptions``. Per column, the description is chosen by a
    strict priority so re-running never clobbers human edits:

        1. an existing non-empty row in field_descriptions.csv  (SME edits win)
        2. the SME-curated FIELD_DESCRIPTIONS entry             (verbatim)
        3. a fresh draft — AI+KB when --ai is set, else the deterministic,
           no-cost draft.

    Returns counts by source. AI spend (when --ai) happens here, once.
    """
    from field_description_pipeline import (
        DEFAULT_CSV_PATH,
        draft_field_description,
        graph_column_keys,
        read_descriptions_csv,
        write_descriptions_csv,
    )

    graph_keys = graph_column_keys()
    curated = _curated_lookup()
    existing = {
        (r["table_name"], r["column_name"]): r for r in read_descriptions_csv()
    }

    rows = []
    counts = {"existing": 0, "curated": 0, "drafted": 0}
    # Checkpoint to the CSV every N AI drafts so a long, interrupted run is
    # resumable: a re-run treats already-written rows as "existing" (priority 1)
    # and only drafts the remainder.
    checkpoint_every = 15
    since_checkpoint = 0
    for table, column in graph_keys:
        prior = existing.get((table, column))
        if prior and prior.get("description"):
            rows.append(prior)
            counts["existing"] += 1
            continue

        if (table, column) in curated:
            display, desc, example = curated[(table, column)]
            rows.append({
                "table_name": table, "column_name": column,
                "display_name": display, "description": desc,
                "example_value": example,
            })
            counts["curated"] += 1
            continue

        draft = draft_field_description(
            table, column, use_ai=use_ai, db_path=DB_PATH, use_kb=use_ai,
        )
        rows.append({
            "table_name": table, "column_name": column,
            "display_name": draft.get("display_name", ""),
            "description": draft.get("description", ""),
            "example_value": draft.get("example_value", ""),
        })
        counts["drafted"] += 1
        since_checkpoint += 1
        if verbose:
            src = draft.get("_source", "?")
            kb = " +kb" if draft.get("_kb_used") else ""
            print(f"  drafted [{src}{kb}]: {table}.{column} -> "
                  f"{draft.get('display_name')}", flush=True)
        if use_ai and since_checkpoint >= checkpoint_every:
            write_descriptions_csv(rows)
            since_checkpoint = 0
            print(f"  ... checkpoint: {len(rows)} rows written", flush=True)

    written = write_descriptions_csv(rows)
    print(f"wrote {written} rows to {DEFAULT_CSV_PATH} "
          f"(existing={counts['existing']}, curated={counts['curated']}, "
          f"drafted={counts['drafted']}).")
    return counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed SME-curated field descriptions; optionally draft the rest.",
    )
    parser.add_argument(
        "--fill-missing", action="store_true",
        help="After seeding the curated set, draft + upsert a description for "
             "every other business column that has none (idempotent; curated "
             "rows are preserved).",
    )
    parser.add_argument(
        "--build-graph-csv", action="store_true",
        help="Author/refresh the committed field_descriptions.csv covering every "
             "canonical-graph column node (existing CSV rows and curated entries "
             "are preserved; only missing columns are drafted). Does NOT require "
             "the DB unless drafting deterministically from data samples.",
    )
    parser.add_argument(
        "--ai", action="store_true",
        help="Use the OpenAI draft path (requires OPENAI_API_KEY) for "
             "--fill-missing / --build-graph-csv. Default is the deterministic, "
             "no-cost draft. With --build-graph-csv the AI prompt also consults "
             "the KB/guide selectively.",
    )
    args = parser.parse_args(argv)

    if args.build_graph_csv:
        mode = "AI+KB" if args.ai else "deterministic"
        print(f"building graph field_descriptions.csv ({mode} drafts)...")
        _build_graph_csv(use_ai=args.ai, verbose=True)
        return 0

    if not os.path.exists(DB_PATH):
        raise SystemExit(f"ERROR: manufacturing.db not found at {DB_PATH}")

    seeded = _seed_curated()
    print(f"seeded {seeded} curated field description(s) (idempotent; stand-in for DAB).")

    if args.fill_missing:
        from field_description_pipeline import fill_missing
        mode = "AI" if args.ai else "deterministic"
        print(f"filling missing descriptions ({mode} drafts)...")
        filled = fill_missing(db_path=DB_PATH, use_ai=args.ai, verbose=True)
        print(f"drafted {filled} previously-undescribed business column(s).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
