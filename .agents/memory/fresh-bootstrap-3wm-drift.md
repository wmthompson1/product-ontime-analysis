---
name: Fresh-clone bootstrap 3WM verify failure
description: Clean-room bootstrap_db.py fails at complete_three_way_match ("Paid invoices stuck in Pending (got 3)") — pre-existing, independent of later migrations.
---

A fully fresh clean-room rebuild (`scripts/bootstrap_db.py` on a deleted DB, repo copied to a sibling-preserving layout `<root>/hf-space-inventory-sqlgen` + `<root>/replit_integrations` — the ERP seeder resolves paths from REPO_ROOT, so the folder names must be preserved) fails at `migrations/complete_three_way_match.py` with `VERIFY FAIL: Paid invoices stuck in Pending (got 3)` (observed 2026-07-14).

**Why it matters:** this happens BEFORE later steps in the chain, so any migration appended after it never runs in a clean room; the live DB doesn't hit this because its payables history differs from the freshly seeded one.

**How to apply:** when verifying a new bootstrap-chain migration clean-room, expect this upstream failure; prove the new migration on the clean-room DB by running it directly at the failure point. Fixing the 3WM clean-room drift is separate work.
