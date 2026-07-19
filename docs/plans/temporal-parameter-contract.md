# Temporal Parameter Contract

## What & Why
Teach the Solder pattern to support user-controlled date filtering **without ever rewriting SQL text**. The mechanism: SME-approved snippets expose static, tokenized named parameters (`:start_date`, `:end_date`, `:supplier_id`) baked into the snippet itself, each wrapped in a NULL-guard (`:x IS NULL OR ...`) so the default (unbound) behavior is unchanged. This phase is **metadata + contract only**: the SQL Semantics lens must recognize those tokens and *declare* how each one filters — distinguishing a **Horizon window** (transaction-window filter on a base-table date column) from a **Netting snapshot** (point-in-time cutoff applied inside the exception subqueries) — and which physical column each token guards. No live execution and no date sliders in this phase.

Core invariant: the structural fingerprint (base tables + canonical join edges) must stay byte-identical. Verified that `:named` tokens parse as SQLGlot placeholder nodes and leave `base_table_set` and `join_edges` unchanged, so tokenizing does not violate the non-generative core.

## Done looks like
- The Uninvoiced Receipts ground-truth snippet carries tokenized, NULL-guarded date/supplier parameters, and its structural fingerprint is unchanged from before.
- The 🧾 SQL Semantics lens contract gains a **Temporal Contract** section that lists each detected parameter, the physical column it guards, and its classification (Horizon window vs Netting snapshot).
- The graph/orientation record for that binding key carries a temporal trait (e.g. `time: range-bounded` / `point-in-time`) reflecting the same classification.
- The existing snippet-execution acceptance gate still passes: snippets with placeholders are executed with default NULL bindings and return the same rows as before.
- All existing parity/coverage gates in `scripts/post-merge.sh` remain green.

## Out of scope
- Live execution of parameterized queries and any date-range UI inputs / sliders (explicitly a later phase).
- Any change to the real-source T-SQL reference benchmarks; the synthetic target stays SQLite (`receiving.receipt_date` is the physical column, output-aliased `received_date`; `R.RECEIVED_DATE` is reference-only).
- Applying temporal parameters to snippets other than Uninvoiced Receipts.
- Registering a brand-new snippet/view: harden the EXISTING snippet in place so the fingerprint and graph freeze are preserved.

## Steps
1. **Harden the existing snippet with tokenized params.** Add NULL-guarded `:start_date` / `:end_date` on the physical `receiving.receipt_date` (Horizon window), a `:end_date` cutoff on the payables `invoice_date` inside both exception subqueries (Netting snapshot), and a `:supplier_id` guard. Use only columns that exist in the SQLite twin — do not introduce the nonexistent `received_date` physical column or a duplicate alias from the user's draft. Confirm the structural fingerprint is unchanged.
2. **Detect and classify parameters in the extractor.** Extend the view-ontology extraction to find placeholder tokens, resolve the physical column each one guards, and classify each as Horizon (filter on a base-table date column in the main WHERE/ORDER BY) vs Netting snapshot (cutoff inside a subquery/exception predicate). Surface this as structured temporal metadata on the view ontology.
3. **Render the Temporal Contract in the lens.** Add a Temporal Contract block to the "STRUCTURAL RELATIONAL ONTOLOGY CONTRACT — SQL" output showing each parameter, its guarded physical column, and its Horizon/Netting classification. Read-only, no execution.
4. **Enrich the graph/orientation trait.** Record the temporal trait (range-bounded vs point-in-time) on the binding key's orientation record so the graph declares that this key supports temporal constraints, consistent with the lens classification.
5. **Keep the execution gate green.** Update the approved-snippet execution test path so any placeholders are bound to default NULL values at execute time, proving the tokenized snippet still runs and returns the same result set. Re-run the relevant parity/coverage gates.

## Relevant files
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/payables_uninvoicedreceipts_20260706_000003.sql`
- `hf-space-inventory-sqlgen/view_ontology_extractor.py:209-244`
- `hf-space-inventory-sqlgen/structural_fingerprint.py`
- `hf-space-inventory-sqlgen/solder_engine.py:120-179,240-350`
- `hf-space-inventory-sqlgen/app.py:6585-7007`
- `hf-space-inventory-sqlgen/app/database_executor.py:92-95`
- `hf-space-inventory-sqlgen/tests/test_approved_snippets_execute.py:112`
