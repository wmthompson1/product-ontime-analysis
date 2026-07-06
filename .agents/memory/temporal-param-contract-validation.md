---
name: Temporal parameter contract validation
description: How SolderEngine passively validates baked-in :named parameters against the Temporal Parameter Contract at serve time.
---

# Temporal parameter contract validation

`SolderEngine.validate_temporal_contract(sql_text, binding_key)` is a passive,
fail-closed check run on both serve paths (`resolve_by_binding_key` and
`assemble_query`, fail_condition `temporal_contract_validation_failed`). Pure
SQLGlot AST — nothing is executed, no value is bound.

## Rule
Every tokenized (`:named`) placeholder occurrence must be a recognized member of
the machine-readable Temporal Parameter Contract that `view_ontology_extractor`
emits. Validate **per OCCURRENCE, not per token name** — otherwise a token used
once in a valid guard and again in an invalid context (e.g. `LIMIT :end_date`)
slips through because the name is "recognized" elsewhere.

An occurrence is valid only if it climbs to either:
1. a comparison (EQ/NEQ/LT/LTE/GT/GTE) that carries a physical column, or
2. the exact positive `:param IS NULL` guard arm (`exp.Is` with `exp.Null`
   right side, not wrapped in `exp.Not`).

Anything else (LIMIT, function arg, `:a = :b` with no column, `IS NOT NULL`,
`IS TRUE`) is drift → fail closed. The extractor contract is still used as an
authoritative token cross-check.

**Why:** The SME-approved idiom is exactly `(:param IS NULL OR <col> <op> :param)`.
A token-set-only check (and an over-broad `exp.Is` accept) were both caught in
review as fail-closed holes — the null guard must be constrained to the positive
`IS NULL` shape.

**How to apply:** mirror the extractor's climb (`_extract_temporal_parameters`)
when touching this validator so the two definitions of "recognized" don't drift.
Only one approved snippet (`payables_uninvoicedreceipts`) currently carries
placeholders; all others have none and pass trivially.
