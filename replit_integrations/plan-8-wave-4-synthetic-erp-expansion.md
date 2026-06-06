# Plan 8 · Wave 4 — Synthetic ERP Expansion (Traceability Spine)

- **Topic:** Extend `manufacturing.db` with synthetic ERP tables centered on manufacturing/warranty traceability
- **Created:** 2026-06-06
- **Status:** Approved in principle — design first, build by milestone on user go
- **Depends on:** `references` predicate in `export_graph_metadata.py` (Plan 8 · Wave 3, SCHEMA_VERSION 2)

## Objective

Add synthetic ERP tables that (a) deepen the `part_id` foreign-key hub, (b) introduce the
Infor VISUAL **traceability spine** for warranty / recall genealogy, and (c) carry **declared
FK constraints** so the existing `references` exporter mints the edges automatically from
`PRAGMA foreign_key_list` — no convention-guessing. This realizes plan-011's goal: extract a
declared FK hierarchy and drive topological ordering for synthetic data generation and
Text-to-SQL join discovery.

## Source grounding (real VISUAL DDLs in this repo)

| Synthetic table | Mirrors (source DDL) | Role |
|---|---|---|
| `inventory_transaction` | `Data_Models/.../INVENTORY_TRANS`, `class_type_matrix.md` | R/A/I × I/O movement ledger |
| `trace` | `ddl/dbo.TRACE.sql` | a traced lot/serial of a part |
| `trace_inventory_trace` | `ddl/dbo.TRACE_INV_TRANS.sql` | **intermediate bridge** trace lot ↔ transaction (qty-weighted) |
| `inv_trans_dist` | `ddl/dbo.INV_TRANS_DIST.sql` | **genealogy / depth driver** — IN-trans ↔ OUT-trans |
| `customer_order` / `customer_order_line` | `Data_Models/Receivables/CUSTOMER_ORDER.sql`, `CUST_ORDER_LINE.sql` | demand side |
| `payable_line` | `RECEIVABLE_LINE.sql` / `ddl/dbo.VR_PAYABLE_DET.sql` | AP detail (extends existing `invoice_header`) |
| `site` | referenced by `SITE` FKs throughout | dimension that anchors orphan `site_id` |

## Key decision (chosen)

1. **Single-column surrogate `<entity>_id` PKs + declared FK constraints.**
   Consistent with the existing synthetic tables (`wo_id`, `po_id`, `line_id`, `receipt_id`),
   which already simplify VISUAL's composite natural keys. Declared FKs make both the
   declared-FK exporter route **and** the PK-name convention matcher work.
   *Alternative considered:* mirror VISUAL composite natural keys faithfully (e.g.
   `TRACE` PK `(part_id, id)`). Rejected for synthetic simplicity + consistency.
2. **Include `inv_trans_dist` now** — it is the self-referential edge that makes the
   genealogy recursive and produces the 4–5 level depth.

## Table specifications (SQLite DDL, declared FKs)

```sql
CREATE TABLE IF NOT EXISTS site (
    site_id    TEXT PRIMARY KEY,
    site_name  TEXT NOT NULL,
    region     TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inventory_transaction (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    class      TEXT NOT NULL CHECK(class IN ('R','A','I')),   -- Released / Adjust / Issue
    type       TEXT NOT NULL CHECK(type  IN ('I','O')),       -- In / Out (effect on QOH)
    part_id    TEXT NOT NULL,
    wo_id      TEXT,
    po_id      TEXT,
    site_id    TEXT,
    quantity   REAL NOT NULL,
    trans_date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (part_id) REFERENCES part(part_id),
    FOREIGN KEY (wo_id)   REFERENCES work_order(wo_id),
    FOREIGN KEY (po_id)   REFERENCES purchase_order(po_id),
    FOREIGN KEY (site_id) REFERENCES site(site_id)
);

CREATE TABLE IF NOT EXISTS trace (
    trace_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    part_id         TEXT NOT NULL,
    lot_id          TEXT,
    serial_id       TEXT,
    in_qty          REAL DEFAULT 0,
    out_qty         REAL DEFAULT 0,
    production_date DATE,
    expiration_date DATE,
    site_id         TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (part_id) REFERENCES part(part_id),
    FOREIGN KEY (site_id) REFERENCES site(site_id)
);

CREATE TABLE IF NOT EXISTS trace_inventory_trace (
    trace_inv_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    part_id        TEXT NOT NULL,
    trace_id       INTEGER NOT NULL,
    transaction_id INTEGER NOT NULL,
    qty            REAL NOT NULL,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (part_id)        REFERENCES part(part_id),
    FOREIGN KEY (trace_id)       REFERENCES trace(trace_id),
    FOREIGN KEY (transaction_id) REFERENCES inventory_transaction(transaction_id)
);

CREATE TABLE IF NOT EXISTS inv_trans_dist (
    dist_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    in_trans_id  INTEGER NOT NULL,
    out_trans_id INTEGER NOT NULL,
    dist_qty     REAL NOT NULL,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (in_trans_id)  REFERENCES inventory_transaction(transaction_id),
    FOREIGN KEY (out_trans_id) REFERENCES inventory_transaction(transaction_id)
);

CREATE TABLE IF NOT EXISTS customer_order (
    order_id      TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    order_date    DATE NOT NULL,
    site_id       TEXT,
    status        TEXT DEFAULT 'Open' CHECK(status IN ('Open','Shipped','Closed','Cancelled')),
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (site_id) REFERENCES site(site_id)
);

CREATE TABLE IF NOT EXISTS customer_order_line (
    order_line_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id      TEXT NOT NULL,
    line_no       INTEGER NOT NULL,
    part_id       TEXT NOT NULL,
    site_id       TEXT,
    order_qty     REAL NOT NULL,
    unit_price    REAL DEFAULT 0,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES customer_order(order_id),
    FOREIGN KEY (part_id)  REFERENCES part(part_id),
    FOREIGN KEY (site_id)  REFERENCES site(site_id)
);

CREATE TABLE IF NOT EXISTS payable_line (
    payable_line_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id      TEXT NOT NULL,
    line_no         INTEGER NOT NULL,
    po_id           TEXT,
    part_id         TEXT,
    qty             REAL,
    amount          REAL NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id) REFERENCES invoice_header(invoice_id),
    FOREIGN KEY (po_id)      REFERENCES purchase_order(po_id),
    FOREIGN KEY (part_id)    REFERENCES part(part_id)
);
```

### `suppliers` PK sub-step
`suppliers` has no declared PK, so AP/invoice FKs cannot anchor to it. SQLite cannot add a PK
via `ALTER TABLE`; rebuild the table with `PRIMARY KEY (supplier_id)` and copy rows. This
unlocks declared FKs for `supplier_id` (5 columns) in a later wave.

## `references`-edge impact

New declared FKs the exporter will mint on re-run (read from `PRAGMA foreign_key_list`):

| Table | New `references` edges |
|---|---|
| `inventory_transaction` | 4 (part, work_order, purchase_order, site) |
| `trace` | 2 (part, site) |
| `trace_inventory_trace` | 3 (part, trace, inventory_transaction) |
| `inv_trans_dist` | 2 (inventory_transaction × 2) |
| `customer_order` | 1 (site) |
| `customer_order_line` | 3 (customer_order, part, site) |
| `payable_line` | 3 (invoice_header, purchase_order, part) |
| **Total** | **18 new `references` edges** |

The `part_id` hub grows from **5 → 10** child tables. Existing `purchase_order.site_id` and
`work_order.site_id` remain convention-only until declared FKs are added to those existing
tables (optional follow-on wave).

## The 4–5 level warranty trace

```
customer_order_line → (ship) inventory_transaction
   → trace_inventory_trace → trace            [finished-good lot]   (L1–2)
      → (WO-receipt) inventory_transaction                          (L3)
         → inv_trans_dist → (raw-issue) inventory_transaction       (L4)
            → trace_inventory_trace → trace → receiving → supplier  (L5)
```

AQL traversal must bound depth and cap results:

```aql
FOR v, e, p IN 1..5 OUTBOUND @startVertex references
  LIMIT 250
  RETURN p
```

> Foreign-key hierarchies in this domain reach 4–5 levels; always use `1..5` depth and
> `LIMIT 250` on genealogy traversals to keep result sets bounded.

## Conventions to follow (existing synthetic-DB ecosystem)

- `CREATE TABLE IF NOT EXISTS`; snake_case; `TEXT` IDs for entities, `INTEGER AUTOINCREMENT`
  for lines/transactions.
- Always include `created_at DATETIME DEFAULT CURRENT_TIMESTAMP`.
- `CHECK` constraints for status / class / type enums.
- Seed with `INSERT OR IGNORE` and `random.seed(42)` for reproducibility.
- Register every new table in `schema_nodes` (name + description) so the Schema Browser,
  MCP tools, and `graph_sync.py` discover it.

## Milestones (build on user go, one at a time)

- **M1 — Migration:** create the 8 tables with declared FKs + add `suppliers.supplier_id` PK
  + register all in `schema_nodes`. (Pattern: `migrations/add_purchasing_wip_tables.py` +
  `migrations/add_erp_tables_to_schema_nodes.py`.)
- **M2 — Seeder:** extend `scripts/seed_erp_synthetic.py` to populate the new tables in
  topological order, reproducibly, with realistic R/A/I flows and lot genealogy via
  `inv_trans_dist`.
- **M3 — Export & verify:** re-run `export_graph_metadata.py` → `references` edges auto-mint;
  bump `SCHEMA_VERSION` → 3; verify the depth-5 traversal; freeze `graph_metadata.v3.json`.

## Open / override points

- Confirm surrogate keys vs. faithful VISUAL composite keys (default: surrogate).
- Confirm `inv_trans_dist` included now (default: yes).
- Decide whether to also add declared FKs to existing tables (`*.site_id`, `*.supplier_id`)
  in this wave or a later one (default: later).
