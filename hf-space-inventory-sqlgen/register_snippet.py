"""Register an SME-approved SQL snippet into the living manifest.

This is the write-side companion to the structural-fingerprint validation added
in ``structural_fingerprint.py`` / ``solder_engine.py``. Registering a snippet:

  1. Extracts its structural fingerprint (base-table set) with the shared
     SQLGlot extractor — the SME signs off on WHICH tables the logic reaches,
     never on the SQL text or style.
  2. Assigns or reuses a binding key (idempotent by snippet file basename).
  3. Writes the snippet file into ``ground_truth/sql_snippets/`` and an APPROVED
     manifest entry carrying the fingerprint + an audit trail.
  4. Optionally refreshes the routing indexes and re-exports the canonical graph
     so the new binding node + base-table topology land in the graph.

The registered fingerprint is the source of truth the runtime validates against:
after registration, an SME may freely rename/reorder CTEs, reorder joins, or
change windowing/bucketing — the snippet keeps serving as long as its base-table
SET is unchanged. Changing the base-table set is a re-registration event.

Fail-closed: a snippet whose SQL cannot be parsed is rejected here (it could
never be validated at runtime), so it never enters the manifest.

Usage (module):
    from register_snippet import register_snippet
    result = register_snippet(
        sql_text=..., perspective="Operations", concept_anchor="OEE",
        logic_type="DIRECT", sme_justification="...", signed_off_by="jdoe",
    )

Usage (CLI):
    python register_snippet.py --sql-file path/to/snippet.sql \\
        --perspective Operations --concept-anchor OEE \\
        --logic-type DIRECT --justification "..." --signed-off-by jdoe \\
        [--binding-key explicit_key] [--refresh-routing] [--reexport-graph]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import structural_fingerprint as sfp  # noqa: E402
from binding_key_utils import make_binding_key  # noqa: E402

MANIFEST_PATH = os.path.join(_HERE, "app_schema", "ground_truth", "reviewer_manifest.json")
SNIPPETS_DIR = os.path.join(_HERE, "app_schema", "ground_truth", "sql_snippets")
# file_path recorded in the manifest is repo-relative from hf-space-inventory-sqlgen.
SNIPPETS_REL = os.path.join("app_schema", "ground_truth", "sql_snippets")


class RegistrationError(Exception):
    """Raised when a snippet cannot be registered (fail closed, no write)."""


def _load_manifest(path: str) -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {"approved_snippets": {}, "last_updated": None}


def _find_existing_key(manifest: dict, perspective: str, concept_anchor: str) -> str | None:
    """Return the binding key of an entry with the same (perspective, concept_anchor).

    Idempotency anchor for the mint path: re-registering the same logical snippet
    (same concept under the same perspective) reuses its key and updates in place
    instead of minting a duplicate binding.
    """
    for key, entry in manifest.get("approved_snippets", {}).items():
        if (entry.get("perspective") == perspective
                and entry.get("concept_anchor") == concept_anchor):
            return key
    return None


def _assign_binding_key(manifest: dict, base_tables: list[str], perspective: str) -> str:
    """Mint a fresh binding key that does not collide with an existing entry.

    Uses the Solder Pattern key convention (src=first base table, tgt=last),
    bumping the sequence number until the key is unique.
    """
    src = base_tables[0]
    tgt = base_tables[-1]
    existing = set(manifest.get("approved_snippets", {}))
    seq = 1
    while True:
        key = make_binding_key(src, tgt, seq, perspective)
        if key not in existing:
            return key
        seq += 1


def register_snippet(
    *,
    sql_text: str,
    perspective: str,
    concept_anchor: str,
    logic_type: str = "DIRECT",
    sme_justification: str = "",
    signed_off_by: str = "unknown",
    binding_key: str | None = None,
    category: str = "",
    manifest_path: str = MANIFEST_PATH,
    snippets_dir: str = SNIPPETS_DIR,
    write: bool = True,
) -> dict:
    """Register (or re-register) an SME-approved snippet. Returns a summary dict.

    Fail-closed: rejects a snippet whose SQL cannot be parsed, or one that reaches
    no base table at all (nothing to fingerprint). Idempotent by snippet file
    basename — re-registering the same file reuses its key and rewrites its entry.
    """
    sql_text = (sql_text or "").strip()
    if not sql_text:
        raise RegistrationError("empty snippet: nothing to register")

    try:
        base_tables = sfp.base_table_set(sql_text, strict=True)
    except sfp.FingerprintParseError as exc:
        raise RegistrationError(f"snippet failed to parse, cannot register: {exc}")
    if not base_tables:
        raise RegistrationError("snippet reaches no base table; nothing to fingerprint")

    # v2 (graph-aware) fingerprint: also capture the snippet's canonical join
    # edges (+ any unresolved joins) so the runtime enforces join drift/recognition
    # — a hard cutover, so every newly registered snippet is join-aware.
    join_edge_tuples, unresolved_joins = sfp.join_edges_from_sql(sql_text)
    join_edges = [sfp.edge_to_dict(e) for e in join_edge_tuples]

    manifest = _load_manifest(manifest_path)
    snippets = manifest.setdefault("approved_snippets", {})

    # Resolve the binding key: explicit key wins; else reuse the entry for the
    # same (perspective, concept_anchor) if one exists (idempotent re-register);
    # else mint a fresh, collision-free key.
    if binding_key is None:
        binding_key = (
            _find_existing_key(manifest, perspective, concept_anchor)
            or _assign_binding_key(manifest, base_tables, perspective)
        )
    reused = binding_key in snippets

    now = datetime.now(timezone.utc).isoformat()
    snippet_basename = f"{binding_key}.sql"
    file_rel = os.path.join(SNIPPETS_REL, snippet_basename)
    file_abs = os.path.join(snippets_dir, snippet_basename)

    prior = snippets.get(binding_key, {})
    entry = {
        "binding_key": binding_key,
        "category": category or prior.get("category", ""),
        "perspective": perspective,
        "concept_anchor": concept_anchor,
        "logic_type": logic_type or "DIRECT",
        "file_path": file_rel,
        "sme_justification": sme_justification or prior.get("sme_justification", ""),
        "validation_status": "APPROVED",
        "created_at": prior.get("created_at", now),
        "approved_at": now,
        "approved_by": signed_off_by,
        "structural_fingerprint": {
            "base_tables": base_tables,
            "join_edges": join_edges,
            "unresolved_joins": unresolved_joins,
            "extractor": sfp.EXTRACTOR_ID_V2,
            "dialect": sfp.FINGERPRINT_DIALECT,
            "signed_off_by": signed_off_by,
            "signed_off_at": now,
        },
    }

    if write:
        os.makedirs(snippets_dir, exist_ok=True)
        with open(file_abs, "w", encoding="utf-8") as fh:
            fh.write(sql_text.rstrip() + "\n")
        snippets[binding_key] = entry
        manifest["last_updated"] = now
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)
            fh.write("\n")

    return {
        "binding_key": binding_key,
        "base_tables": base_tables,
        "join_edges": join_edges,
        "unresolved_joins": unresolved_joins,
        "reused_existing": reused,
        "file_path": file_rel,
        "written": write,
    }


def refresh_routing(verbose: bool = False) -> None:
    """Rebuild the routing indexes so the new snippet is discoverable by concept."""
    from solder_engine import SolderEngine

    eng = SolderEngine()
    eng.build_table_usage_index(verbose=verbose)
    eng.build_perspective_affinity_index(verbose=verbose)


def reexport_graph() -> int:
    """Re-export the canonical graph so the new binding lands in the topology."""
    repo_root = os.path.dirname(_HERE)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    from replit_integrations import export_graph_metadata as exporter

    return exporter.main()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sql-file", required=True, help="path to the snippet .sql file")
    ap.add_argument("--perspective", required=True)
    ap.add_argument("--concept-anchor", required=True)
    ap.add_argument("--logic-type", default="DIRECT")
    ap.add_argument("--justification", default="")
    ap.add_argument("--signed-off-by", default="unknown")
    ap.add_argument("--category", default="")
    ap.add_argument("--binding-key", default=None,
                    help="explicit binding key (default: minted / reused by basename)")
    ap.add_argument("--refresh-routing", action="store_true",
                    help="rebuild table-usage + perspective-affinity indexes after write")
    ap.add_argument("--reexport-graph", action="store_true",
                    help="re-export the canonical graph after write")
    ap.add_argument("--dry-run", action="store_true", help="do not write anything")
    args = ap.parse_args()

    with open(args.sql_file, "r", encoding="utf-8") as fh:
        sql_text = fh.read()

    try:
        result = register_snippet(
            sql_text=sql_text,
            perspective=args.perspective,
            concept_anchor=args.concept_anchor,
            logic_type=args.logic_type,
            sme_justification=args.justification,
            signed_off_by=args.signed_off_by,
            binding_key=args.binding_key,
            category=args.category,
            write=not args.dry_run,
        )
    except RegistrationError as exc:
        print(f"REJECTED (fail closed): {exc}", file=sys.stderr)
        return 1

    print("Snippet registration" + (" (dry run)" if args.dry_run else ""))
    print(f"  binding_key : {result['binding_key']}"
          f"{' (reused)' if result['reused_existing'] else ' (new)'}")
    print(f"  base_tables : {result['base_tables']}")
    print(f"  join_edges  : {len(result['join_edges'])} "
          f"({len(result['unresolved_joins'])} unresolved)")
    print(f"  file_path   : {result['file_path']}")

    if not args.dry_run and args.refresh_routing:
        refresh_routing()
        print("  routing     : rebuilt")
    if not args.dry_run and args.reexport_graph:
        rc = reexport_graph()
        print(f"  graph       : re-export rc={rc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
