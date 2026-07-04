#!/usr/bin/env python3
"""Backfill structural fingerprints onto every APPROVED manifest entry.

A structural fingerprint is the SME-visible, signed-off *set of base tables* a
snippet touches (see ``structural_fingerprint.py``). This migration adds a
``structural_fingerprint`` block to each APPROVED entry in
``reviewer_manifest.json`` whose ``.sql`` file is readable, by extracting the
base-table set with the shared SQLGlot extractor (SQLite dialect, CTE names
excluded). It never authors, infers, or mutates SQL — it only reads the SQL the
SME already approved and records what tables it reaches.

Idempotent:
  * A fresh entry gets a fingerprint stamped with ``signed_off_by='seed_backfill'``.
  * An entry whose stored fingerprint already matches the current .sql is left
    byte-identical (audit fields preserved) — re-running is a no-op.
  * An entry whose stored fingerprint DIFFERS from the current .sql is reported
    as drift and, unless ``--force`` is given, left untouched (a real fingerprint
    change is an SME sign-off event, handled by the registration flow — not a
    silent backfill overwrite).

Run from the repo root or this directory:
    python hf-space-inventory-sqlgen/migrations/backfill_structural_fingerprints.py
    python hf-space-inventory-sqlgen/migrations/backfill_structural_fingerprints.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_HF_DIR = os.path.dirname(_HERE)
if _HF_DIR not in sys.path:
    sys.path.insert(0, _HF_DIR)

import structural_fingerprint as sfp  # noqa: E402

MANIFEST_PATH = os.path.join(
    _HF_DIR, "app_schema", "ground_truth", "reviewer_manifest.json"
)


def _resolve_snippet_path(file_path: str, manifest_dir: str) -> str | None:
    """Resolve a manifest ``file_path`` to a readable snippet, mirroring the
    engine's resolution order (manifest dir basename, hf dir, repo root)."""
    if not file_path:
        return None
    if os.path.isabs(file_path) and os.path.exists(file_path):
        return file_path
    candidate = os.path.join(manifest_dir, os.path.basename(file_path))
    if os.path.exists(candidate):
        return candidate
    hf_candidate = os.path.join(_HF_DIR, file_path)
    if os.path.exists(hf_candidate):
        return hf_candidate
    repo_root = os.path.dirname(_HF_DIR)
    repo_candidate = os.path.join(repo_root, file_path)
    if os.path.exists(repo_candidate):
        return repo_candidate
    if os.path.exists(file_path):
        return file_path
    return None


def backfill(manifest_path: str = MANIFEST_PATH, dry_run: bool = False,
             force: bool = False) -> dict:
    """Backfill fingerprints. Returns a summary dict; writes the manifest unless
    ``dry_run``. See module docstring for idempotency semantics."""
    with open(manifest_path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    snippets = manifest.get("approved_snippets", {})
    manifest_dir = os.path.dirname(os.path.abspath(manifest_path))

    summary = {
        "added": [], "unchanged": [], "drift": [], "skipped_no_file": [],
        "skipped_not_approved": [], "parse_error": [],
    }
    changed = False

    for binding_key, entry in snippets.items():
        if entry.get("validation_status") != "APPROVED":
            summary["skipped_not_approved"].append(binding_key)
            continue

        resolved = _resolve_snippet_path(entry.get("file_path", ""), manifest_dir)
        if not resolved:
            summary["skipped_no_file"].append(binding_key)
            continue

        with open(resolved, "r", encoding="utf-8") as fh:
            sql_text = fh.read().strip()

        try:
            base_tables = sfp.base_table_set(sql_text, strict=True)
        except sfp.FingerprintParseError:
            summary["parse_error"].append(binding_key)
            continue

        existing = entry.get("structural_fingerprint")
        if existing and list(existing.get("base_tables") or []) == base_tables:
            summary["unchanged"].append(binding_key)
            continue

        if existing and not force:
            summary["drift"].append(binding_key)
            continue

        now = datetime.now(timezone.utc).isoformat()
        entry["structural_fingerprint"] = {
            "base_tables": base_tables,
            "extractor": sfp.EXTRACTOR_ID,
            "dialect": sfp.FINGERPRINT_DIALECT,
            "signed_off_by": "seed_backfill",
            "signed_off_at": now,
        }
        changed = True
        (summary["drift"] if existing else summary["added"]).append(binding_key)

    if changed and not dry_run:
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)
            fh.write("\n")

    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", default=MANIFEST_PATH)
    ap.add_argument("--dry-run", action="store_true",
                    help="report changes without writing the manifest")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing fingerprint whose base-table set drifted")
    args = ap.parse_args()

    summary = backfill(args.manifest, dry_run=args.dry_run, force=args.force)

    print("Structural fingerprint backfill" + (" (dry run)" if args.dry_run else ""))
    print(f"  added     : {len(summary['added'])}  {summary['added']}")
    print(f"  unchanged : {len(summary['unchanged'])}")
    print(f"  drift     : {len(summary['drift'])}  {summary['drift']}")
    print(f"  no file   : {len(summary['skipped_no_file'])}")
    print(f"  not appr. : {len(summary['skipped_not_approved'])}")
    print(f"  parse err : {len(summary['parse_error'])}  {summary['parse_error']}")
    if summary["drift"] and not args.force:
        print("  NOTE: drift entries left untouched; re-run with --force to overwrite.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
