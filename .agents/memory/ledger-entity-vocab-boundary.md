---
name: Ledger ontology entity-vs-practice vocabulary boundary
description: Where "Job" is allowed vs where "WorkOrder" is required in the ledger OWL/binding layers.
---

# Ledger entity vocabulary: :WorkOrder, not :Job

Any OWL/binding term that grounds 1:1 on a physical governed table must use the
table's vocabulary: the ledger entity class is `:WorkOrder` (individuals
`:UnreleasedWorkOrderState` etc., class `:WorkOrderLifecycleState`, binding
`ledger:WorkOrder -> work_order (wo_id)`).

**Why:** user-ratified (2026-07-19 review): the ontology must reflect the
governed schema exactly or NLQ/OBDA drift ("job" vs "work order" questions);
an earlier draft used ERP-generic ":Job" and was corrected.

**How to apply:** "job" survives ONLY as the costing-practice term — the
Job-Costing Ledger scheme name, `:JobCompletionEvent`/`:JobCompletion`,
`:forJob`, `gl_job_cost_detail`, module `job_lifecycle.py`. Never reintroduce a
`:Job` entity class. Gates asserting the vocabulary: `test_job_lifecycle.py`
and `ledger_events_vocab_check.py` — both must be updated in lockstep with any
ontology term rename, and the diagram SVG is regenerated from the .dot via
graphviz `dot -Tsvg`.
