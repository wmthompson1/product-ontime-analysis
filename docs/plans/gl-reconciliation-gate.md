# GL Reconciliation Gate in Post-Merge Suite

## What & Why
Add a standing verification script + test that proves the GL stays consistent with the operational tables, and wire it into the post-merge gate so future data or migration changes can't silently break the ledger. This replaces what control accounts would normally enforce — since the synthetic design deliberately has none, the gate is the integrity mechanism.

## Done looks like
- A check script asserts, fail-closed with named offenders: (a) every journal entry balances (debits = credits per entry), (b) WIP postings per open WO tie to `work_order` actual cost columns, (c) closed WOs carry zero WIP, (d) GL received-not-invoiced ties to received-unmatched PO lines, (e) every gl_transaction row references a real account and a real source document.
- A test file runs the check gate-style (invoked as `python file.py`, consistent with the suite's per-file invocation convention).
- `scripts/post-merge.sh` runs the new check.
- The check passes on a fresh-clone bootstrap DB.

## Out of scope
- Any fixes to posting logic (belongs to the posting tasks); this task assumes they're merged.
- Trial balance UI.

## Steps
1. **Check script** — implement the five assertions above as a standalone read-only script with clear per-failure output.
2. **Test wrapper** — add a test file exercising the check against the live DB, following existing test conventions in `hf-space-inventory-sqlgen/tests/`.
3. **Gate wiring** — add the check to `scripts/post-merge.sh` and confirm the full chain passes on a bootstrap-rebuilt DB.

## Relevant files
- `scripts/post-merge.sh`
- `hf-space-inventory-sqlgen/scripts/bootstrap_db.py`
- `hf-space-inventory-sqlgen/tests/`
