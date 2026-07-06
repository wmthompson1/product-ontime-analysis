---
name: Filter/temporal date column binding is per-query, noun vs adjective
description: When building Selector filtering, the date facet must bind to the physical column of each query, which differs from the output alias and from real-source naming.
---

# Filter date column is not uniform — bind per query, physical not alias

When filtering is added to the Selector / SQL Semantics lens, the temporal
(date) facet must bind to the **physical column each query actually filters /
orders on**, which is NOT always the obvious or output-facing name.

**Concrete example — Uninvoiced Receipts:**
- Real source (private SQL Server `Live.dbo.*`) filters on `R.RECEIVED_DATE`
  (a *noun*: "received date").
- Synthetic SQLite twin's physical column on `receiving` is `receipt_date`
  (an *adjective/compound*: "receipt date").
- The twin bridges them with an output alias: `r.receipt_date AS received_date`,
  and sorts on the physical column: `ORDER BY … r.receipt_date`.

**Rule:** the date facet binds to the **physical** column of the query
(`receiving.receipt_date` here), never the output-alias noun (`received_date`)
and never a guessed uniform name. Extractors that read the SELECT alias (grain
shows `receipt_date`/`received_date` depending on aliasing) can disagree with
the actual filter column — trust the physical FROM/JOIN column + WHERE/ORDER BY.

**Why:** noun-vs-adjective naming differs between the real source and the
synthetic twin, and the filter column differs per query, so a single hardcoded
or alias-derived date column will bind wrong for some views.

**How to apply:** when wiring a date filter, resolve the physical column from
the query's AST (FROM/JOIN table + the column used in WHERE/ORDER BY), per
query — do not assume `received_date` vs `receipt_date` is consistent.
