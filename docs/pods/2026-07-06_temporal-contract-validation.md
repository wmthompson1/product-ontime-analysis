# Temporal-Parameter Contract Validation + owl:complementOf Zero-Weight Rule

_Saved 2026-07-06 — "Metadata + contract only" milestone_

Both deliverables are metadata/contract only — no live execution, no dynamic SQL
generation, no UI inputs, no spread to other MRP snippets.

## 1. Passive temporal-parameter contract validation (`solder_engine.py`)

- New `validate_temporal_contract()` — pure SQLGlot AST, nothing executed, no
  values bound. Every `:named` placeholder must be a recognized member of the
  machine-readable Temporal Parameter Contract from `view_ontology_extractor`.
- Wired into both serve paths (`resolve_by_binding_key` and `assemble_query`)
  with `fail_condition = "temporal_contract_validation_failed"`.
- Validation is **per-occurrence** (not per token name), accepting only a
  column-bearing comparison or the exact positive `:param IS NULL` guard arm —
  so a token reused in an invalid context (`LIMIT`, function arg, `IS NOT NULL`)
  fails closed. Only `payables_uninvoicedreceipts` carries placeholders and it
  passes; all other snippets have none and pass trivially. No pattern spread,
  no UI/date inputs.

## 2. `owl:complementOf` zero-weight rule (`inventory_transactions.ttl`)

- Formally flags `trace.lot_id` — which is *not* a column of the
  `inventory_transaction` ledger — as zero semantic weight, i.e. the complement
  of the elevated ledger-fact set. Captures the "we ignore it" rationale.
- Authored in a dedicated `wgt:` namespace so the regex drift gate (which
  governs only the `:` showcase vocabulary) leaves it untouched; no OBDA
  mapping change.

## Review & verification

- Ran the architect twice — fixed both findings (per-occurrence check; then
  constraining the null guard to the positive `IS NULL` form).
- All gates green: temporal-contract 6/6, extractor 49, fingerprint 83,
  coverage 28, execute (26 snippets), SQL↔file parity, ontop drift
  (7 showcases), mapping-generation; app boots (HTTP 200).

## Key files

- `hf-space-inventory-sqlgen/solder_engine.py` (`validate_temporal_contract` + 2 call sites)
- `hf-space-inventory-sqlgen/view_ontology_extractor.py` (`_extract_temporal_parameters`, `extract_view_ontology`)
- `hf-space-inventory-sqlgen/tests/test_temporal_contract_validation.py` (6 tests)
- `poc/ontop-ontology-poc/ontology/inventory_transactions.ttl` (owl:complementOf rule)
- `poc/ontop-ontology-poc/mapping_drift_check.py` (parse_ttl gate constraint)
