# Fresh-Clone Bootstrap — Faker Dependency Fix

*Saved from chat: 2026-07-05*

Yes — that's my bootstrap script failing closed exactly as designed, and it caught a real gap: the migration chain imported `Faker`, which is only listed in the root `requirements.txt`, not the HF-space one. So a fresh clone that installs just the HF-space requirements hits that error.

Fixed at the source rather than adding the dependency:

**What changed**
- `Faker` was used for exactly one thing — a random-looking invoice number. I removed the dependency entirely and replaced it with a deterministic invoice number derived from each PO's id (stable across runs, which fits the project's determinism rule better than Faker's call-order-dependent sequence).
- Nothing else in the bootstrap chain has a hidden dependency — I audited every script's imports against what a minimal install provides. The one `arango` reference is lazy, inside a function, in a script that isn't part of the chain.

**Verified**
- Ran the edited migration on the live DB — clean.
- Full fresh-clone bootstrap in a clean simulation — "MRP OK" in 2.8s.
- Ran it again with `faker` deliberately blocked from importing (emulating a machine without it) — completes cleanly.
- Data-sensitive gate tests (labor chain reconciliation, MRP schedule) still pass, and no test asserts on the old invoice-number values.

**On a fresh clone:** pull the latest and re-run:

```bash
cd hf-space-inventory-sqlgen && python scripts/bootstrap_db.py
```

Every step is idempotent, so it picks up right where it failed.
