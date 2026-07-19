# Implement receivable and receivable_line tables

## What & Why
Create the physical AR side of the ledger: `receivable` (customer invoice headers) and `receivable_line` (invoice lines), mirroring the proven `payables` / `payable_line` design with the arrows reversed (customer_order instead of purchase_order). Today the Receivables perspective reads only `customer_order.status` — there is no invoice-level grain, so aging, open-AR, and dollars-billed questions have no physical home. This also lays the base the upcoming packslip / dollars-shipped research will link into.

Grain contract (per `docs/pods/2026-07-14_receivables-invoice-grain.md`): one row in `receivable` = one AR invoice; one row in `receivable_line` = one invoice line carrying provenance back to the commercial commitment (`order_line_id`). Physical-event provenance (`shipment_line_id`) is deliberately deferred until packslip tables exist — leave a nullable placeholder column so the later migration is additive.

## Done looks like
- Fresh bootstrap (`scripts/bootstrap_db.py`) and the existing live DB both end up with `receivable` and `receivable_line` populated deterministically from the existing customer-order book (Shipped/Closed orders invoiced; Open orders unbilled), respecting demo-scale bands.
- Invoice headers reconcile to their lines (header amount == SUM(line amounts)), line amounts derive from `customer_order_line.order_qty × unit_price` (partial billing allowed but deterministic), and `invoice_id` is unique — all asserted by a fail-closed gate.
- The tables appear in the Schema Browser with table meta-context and per-column plain-language descriptions; all existing parity gates (SQL↔file graph parity, field-description coverage, legacy-perspective grep gates) pass.
- A gate-style regression test file covers: grain uniqueness, header↔line reconciliation, provenance integrity (every line resolves to a real order line), status vocabulary, and the deliberate boundary that Open orders have no invoices.

## Out of scope
- Packslip / shipment tables and `shipment_line_id` population (separate future task after the user's research).
- New governed invoice-level SQL views, palette entries, or intent wiring (the existing intent-19 order-grain queries in `receivables.sql` stay untouched; invoice-level views are follow-up work).
- Dollars-shipped vs forecast comparison.
- Live ArangoDB graph sync (sql_aql parity is a known pre-existing failure; the authoritative gate is SQL↔file).

## Steps
1. **Schema seed DDL + structural metadata** — Add `receivable` and `receivable_line` CREATE TABLE statements to the schema seed, mirroring the payables pair (header: order_id, customer_name denormalized or via join, invoice_number UNIQUE, invoice_date, due_date, amount_dollars, status Open/Paid/Disputed/Void, payment_date; line: invoice_id, line_no, order_id, order_line_id, part_id, qty, amount, nullable shipment_line_id placeholder). Add matching `schema_nodes` / `schema_edges` rows (structural FKs declared, enforcement stays off) following the payables precedent. Remember the seed re-applies via INSERT OR IGNORE on every startup — seed rows must be final.
2. **Deterministic backfill migration** — New idempotent migration that invoices the existing order book: Closed and Shipped orders get invoices (Closed → mostly Paid, Shipped → Open with data-derived due dates anchored to the data-derived AS_OF, never wall-clock), Open orders get none. Amounts derived strictly from order lines (no randomness). Fail-closed verify: uniqueness, header==SUM(lines), every line resolves to a real customer_order_line, no invoices on Open orders.
3. **Graph + description overlays** — Add table/column nodes and edges to the sql_graph source tables, re-freeze graph_metadata with a SCHEMA_VERSION bump, and add rows to `table_descriptions.csv` and `field_descriptions.csv` so the coverage gate (every graph column node described exactly once) passes. Note the columnar quoting quirk: SQLite reserves `notnull`.
4. **Bootstrap wiring + regression gate** — Wire the migration into the bootstrap STEPS at the right point (after the demand/prune chain so it sees the final order book; keep existing order fixed). Add a gate-style test file (run standalone, not batched) covering the assertions in "Done looks like", and run the affected existing suites individually (selector, three-way match, binding-key hash, ontology mosaic) plus the SQL↔file parity and description-coverage checks.

Critical constraints: SQLite is the only synthetic dialect; all seeding deterministic and grounded in existing order data; verify DB changes via sqlite3 dumps (WAL mode, gitignored DB); migration must be idempotent and safe on both fresh-bootstrap and live DBs.

## Relevant files
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql:188-201`
- `hf-space-inventory-sqlgen/migrations/add_supplier_payables_wiring.py`
- `hf-space-inventory-sqlgen/migrations/add_receivables_wiring.py`
- `hf-space-inventory-sqlgen/migrations/complete_three_way_match.py`
- `hf-space-inventory-sqlgen/migrations/add_receiving_line_and_commodities.py`
- `hf-space-inventory-sqlgen/scripts/bootstrap_db.py:39-90`
- `hf-space-inventory-sqlgen/tests/test_twm_spine_parity.py`
- `field_descriptions.csv`
- `table_descriptions.csv`
- `replit_integrations/sql_graph_parity_check.py`
- `replit_integrations/field_description_coverage_check.py`
- `docs/pods/2026-07-14_receivables-invoice-grain.md`
