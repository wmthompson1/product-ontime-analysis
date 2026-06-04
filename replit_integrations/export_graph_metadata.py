#!/usr/bin/env python3
"""
export_graph_metadata.py — Export the semantic graph from SQLite to two parity artifacts.

Reads the semantic-layer tables in manufacturing.db (the source of truth that is
kept in parity with the ArangoDB ``manufacturing_graph``) and writes:

  1. graph_triples.tsv   — a flat (subject, predicate, object, weight) triple list
  2. graph_metadata.json — a node/edge graph document with per-collection counts

Both files are written next to this script in the replit_integrations/ folder.

Run from the repo root:
    python replit_integrations/export_graph_metadata.py

Or as a module:
    python -m replit_integrations.export_graph_metadata

The triples and the JSON describe the same graph; the JSON ``counts`` block is the
parity fingerprint you can compare against ArangoDB collection counts.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)

DB_PATH = os.path.join(
    _REPO_ROOT, "hf-space-inventory-sqlgen", "app_schema", "manufacturing.db"
)
TRIPLES_PATH = os.path.join(_HERE, "graph_triples.tsv")
JSON_PATH = os.path.join(_HERE, "graph_metadata.json")


# ---------------------------------------------------------------------------
# Triple extraction — one query per semantic predicate
# ---------------------------------------------------------------------------

def _fetch_triples(conn: sqlite3.Connection) -> tuple[list[dict], dict]:
    """Pull every semantic relationship out of SQLite as (subject, predicate, object, weight).

    Returns the triple list plus an integrity report describing rows that
    referenced ids missing from their parent table (preserved, not dropped).
    """
    triples: list[dict] = []
    integrity = {"unresolved_concept_refs": 0}

    # Perspective --USES_DEFINITION--> Concept  (schema_perspective_concepts)
    # LEFT JOIN so bridge rows whose concept_id is missing from schema_concepts
    # are preserved (with a placeholder label) rather than silently dropped.
    rows = conn.execute(
        """
        SELECT sp.perspective_name, spc.relationship_type,
               sc.concept_name, spc.concept_id, spc.priority_weight
        FROM schema_perspective_concepts spc
        JOIN schema_perspectives sp  ON sp.perspective_id = spc.perspective_id
        LEFT JOIN schema_concepts sc ON sc.concept_id     = spc.concept_id
        ORDER BY sp.perspective_name, spc.concept_id
        """
    ).fetchall()
    for subj, pred, concept_name, concept_id, weight in rows:
        resolved = concept_name is not None
        if not resolved:
            integrity["unresolved_concept_refs"] += 1
        triples.append(
            {"subject": subj, "subject_type": "perspective", "predicate": pred,
             "object": concept_name if resolved else f"concept#{concept_id}",
             "object_type": "concept", "weight": weight, "resolved": resolved}
        )

    # Perspective --OPERATES_WITHIN--> Intent  (schema_intent_perspectives)
    rows = conn.execute(
        """
        SELECT sp.perspective_name, si.intent_name, sip.intent_factor_weight
        FROM schema_intent_perspectives sip
        JOIN schema_perspectives sp ON sp.perspective_id = sip.perspective_id
        JOIN schema_intents si       ON si.intent_id       = sip.intent_id
        ORDER BY sp.perspective_name, si.intent_name
        """
    ).fetchall()
    for subj, obj, weight in rows:
        triples.append(
            {"subject": subj, "subject_type": "perspective", "predicate": "OPERATES_WITHIN",
             "object": obj, "object_type": "intent", "weight": weight}
        )

    # Intent --ELEVATES--> Concept  (schema_intent_concepts; weight is the binary gate)
    rows = conn.execute(
        """
        SELECT si.intent_name, sc.concept_name, sic.intent_factor_weight
        FROM schema_intent_concepts sic
        JOIN schema_intents si  ON si.intent_id  = sic.intent_id
        JOIN schema_concepts sc ON sc.concept_id = sic.concept_id
        ORDER BY si.intent_name, sic.intent_factor_weight DESC, sc.concept_name
        """
    ).fetchall()
    for subj, obj, weight in rows:
        triples.append(
            {"subject": subj, "subject_type": "intent", "predicate": "ELEVATES",
             "object": obj, "object_type": "concept", "weight": weight}
        )

    # Concept --REFINES--> parent Concept  (schema_concepts self-reference)
    rows = conn.execute(
        """
        SELECT c.concept_name, p.concept_name
        FROM schema_concepts c
        JOIN schema_concepts p ON p.concept_id = c.parent_concept_id
        WHERE c.parent_concept_id IS NOT NULL
        ORDER BY c.concept_name
        """
    ).fetchall()
    for subj, obj in rows:
        triples.append(
            {"subject": subj, "subject_type": "concept", "predicate": "REFINES",
             "object": obj, "object_type": "concept", "weight": 1}
        )

    # Concept --CAN_MEAN--> table.field  (schema_concept_fields)
    rows = conn.execute(
        """
        SELECT sc.concept_name, scf.table_name, scf.field_name, scf.is_primary_meaning
        FROM schema_concept_fields scf
        JOIN schema_concepts sc ON sc.concept_id = scf.concept_id
        ORDER BY sc.concept_name, scf.table_name, scf.field_name
        """
    ).fetchall()
    for concept, table, field, is_primary in rows:
        triples.append(
            {"subject": concept, "subject_type": "concept", "predicate": "CAN_MEAN",
             "object": f"{table}.{field}", "object_type": "column", "weight": is_primary}
        )

    # Table --FOREIGN_KEY--> Table  (schema_edges)
    # DISTINCT: schema_edges stores one physical row per join occurrence, so the
    # same logical FK relationship repeats many times. Collapse to unique edges.
    rows = conn.execute(
        """
        SELECT DISTINCT from_table, relationship_type, to_table, weight, join_column
        FROM schema_edges
        ORDER BY from_table, to_table, join_column
        """
    ).fetchall()
    for subj, pred, obj, weight, join_col in rows:
        triples.append(
            {"subject": subj, "subject_type": "table", "predicate": pred or "FOREIGN_KEY",
             "object": obj, "object_type": "table", "weight": weight, "join_column": join_col}
        )

    return _dedupe_triples(triples), integrity


def _dedupe_triples(triples: list[dict]) -> list[dict]:
    """Drop exact-duplicate triples, keyed on the full semantic tuple."""
    seen: set[tuple] = set()
    unique: list[dict] = []
    for t in triples:
        key = (
            t["subject_type"], t["subject"], t["predicate"],
            t["object_type"], t["object"], t["weight"], t.get("join_column"),
        )
        if key not in seen:
            seen.add(key)
            unique.append(t)
    return unique


# ---------------------------------------------------------------------------
# Graph document assembly
# ---------------------------------------------------------------------------

def _build_graph_document(triples: list[dict], integrity: dict) -> dict:
    """Turn the flat triple list into a {nodes, edges, counts} graph document."""
    nodes: dict[str, dict] = {}

    def _add_node(name: str, node_type: str, *, resolved: bool = True) -> None:
        node_id = f"{node_type}::{name}"
        if node_id not in nodes:
            node = {"id": node_id, "label": name, "type": node_type}
            if not resolved:
                node["unresolved"] = True
            nodes[node_id] = node

    edges: list[dict] = []
    for t in triples:
        _add_node(t["subject"], t["subject_type"])
        _add_node(t["object"], t["object_type"], resolved=t.get("resolved", True))
        edge = {
            "from": f"{t['subject_type']}::{t['subject']}",
            "to": f"{t['object_type']}::{t['object']}",
            "predicate": t["predicate"],
            "weight": t["weight"],
        }
        if t.get("join_column") is not None:
            edge["join_column"] = t["join_column"]
        edges.append(edge)

    node_counts: dict[str, int] = {}
    for n in nodes.values():
        node_counts[n["type"]] = node_counts.get(n["type"], 0) + 1

    predicate_counts: dict[str, int] = {}
    for e in edges:
        predicate_counts[e["predicate"]] = predicate_counts.get(e["predicate"], 0) + 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "sqlite:hf-space-inventory-sqlgen/app_schema/manufacturing.db",
        "description": "Semantic graph exported from SQLite (parity view of ArangoDB manufacturing_graph).",
        "counts": {
            "nodes_total": len(nodes),
            "edges_total": len(edges),
            "nodes_by_type": dict(sorted(node_counts.items())),
            "edges_by_predicate": dict(sorted(predicate_counts.items())),
        },
        "integrity": integrity,
        "nodes": sorted(nodes.values(), key=lambda n: (n["type"], n["label"])),
        "edges": edges,
    }


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def _write_triples(triples: list[dict], path: str) -> None:
    lines = ["subject\tpredicate\tobject\tweight\tsubject_type\tobject_type"]
    for t in triples:
        lines.append(
            "\t".join(
                [
                    str(t["subject"]),
                    str(t["predicate"]),
                    str(t["object"]),
                    str(t["weight"]),
                    t["subject_type"],
                    t["object_type"],
                ]
            )
        )
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _write_json(doc: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    if not os.path.exists(DB_PATH):
        print(f"ERROR: manufacturing.db not found at {DB_PATH}", file=sys.stderr)
        return 1

    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            triples, integrity = _fetch_triples(conn)
        finally:
            conn.close()
    except sqlite3.Error as exc:
        print(f"ERROR: failed to read semantic tables from SQLite: {exc}", file=sys.stderr)
        return 1

    doc = _build_graph_document(triples, integrity)

    try:
        _write_triples(triples, TRIPLES_PATH)
        _write_json(doc, JSON_PATH)
    except OSError as exc:
        print(f"ERROR: failed to write export artifacts: {exc}", file=sys.stderr)
        return 1

    print("Semantic graph exported from SQLite")
    print(f"  triples : {TRIPLES_PATH}  ({len(triples)} rows)")
    print(f"  graph   : {JSON_PATH}")
    print(f"  nodes   : {doc['counts']['nodes_total']}  by type {doc['counts']['nodes_by_type']}")
    print(f"  edges   : {doc['counts']['edges_total']}  by predicate {doc['counts']['edges_by_predicate']}")
    if integrity.get("unresolved_concept_refs"):
        print(
            f"  WARN    : {integrity['unresolved_concept_refs']} perspective-concept "
            "rows reference concept ids missing from schema_concepts "
            "(preserved with concept#<id> placeholders)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
