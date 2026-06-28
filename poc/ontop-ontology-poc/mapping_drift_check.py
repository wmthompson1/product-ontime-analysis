#!/usr/bin/env python3
"""
Ontology / OBDA mapping drift guard (offline, file-vs-file).
============================================================

The POC's ontology (``ontology/on_time_delivery.ttl``) and OBDA mapping
(``mapping/on_time_delivery.obda``) are hand-authored. The mapping reads physical
tables/columns (e.g. ``receiving.receipt_id``, ``purchase_order.required_date``,
``suppliers.performance_rating``) and binds them to ontology terms. If the
governed schema renames or drops one of those columns, the mapping silently
breaks and the virtual graph quietly disagrees with the SQL source of truth.

This check proves the mapping + ontology stay aligned with the governed schema
WITHOUT a database or network — it compares the hand-authored files against the
committed ``replit_integrations/graph_metadata.json`` snapshot only, mirroring
``field_description_coverage_check.py``. It validates three things:

  1. SCHEMA CLOSURE — every base table/column the mapping's source SQL reads
     (resolved through aliases, CASE expressions, and joins with SQLGlot) exists
     as a ``node_type == "column"`` node in the governed schema.
  2. VOCABULARY CLOSURE (mapping -> ontology) — every ontology term the mapping
     targets is declared in the ontology (no mapping to an undeclared term).
  3. VOCABULARY CLOSURE (ontology -> mapping) — every declared class / property
     is backed by at least one mapping, either directly or, for a parent
     property, via one of its mapped ``rdfs:subPropertyOf`` children (so the
     deliberately-unmapped shared parent ``:onTimeScore`` is not flagged).

Exit codes:
    0  — no drift (or skipped because an input is absent in --skip-on-missing)
    1  — drift detected (a clear diff is printed)
    2  — a required input was missing (and --skip-on-missing not set)

Run:

    python poc/ontop-ontology-poc/mapping_drift_check.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Set, Tuple

POC_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(POC_DIR, "..", ".."))

DEFAULT_MAPPING = os.path.join(POC_DIR, "mapping", "on_time_delivery.obda")
DEFAULT_ONTOLOGY = os.path.join(POC_DIR, "ontology", "on_time_delivery.ttl")
DEFAULT_GRAPH = os.path.join(REPO_ROOT, "replit_integrations", "graph_metadata.json")

# Every published showcase is guarded by default: each is a (label, mapping,
# ontology) triple checked independently against the same governed schema. Adding
# a new governed metric to the virtual graph means adding its pair here so the
# single post-merge invocation covers it too.
DEFAULT_SHOWCASES = [
    ("on-time delivery", DEFAULT_MAPPING, DEFAULT_ONTOLOGY),
    (
        "operational OEE",
        os.path.join(POC_DIR, "mapping", "operational_efficiency.obda"),
        os.path.join(POC_DIR, "ontology", "operational_efficiency.ttl"),
    ),
    (
        "customer order demand",
        os.path.join(POC_DIR, "mapping", "customer_order_demand.obda"),
        os.path.join(POC_DIR, "ontology", "customer_order_demand.ttl"),
    ),
]

# Ontology vocabulary terms live in the empty-prefix (``:``) ontime namespace.
# A vocabulary reference is ``:Name`` that is NOT an instance-IRI template (those
# carry a path, e.g. ``:delivery/{receipt_id}``) and NOT a prefixed term such as
# ``xsd:date`` (whose colon is preceded by the prefix). Capture accordingly.
_VOCAB_TERM_RE = re.compile(r"(?<![\w:]):([A-Za-z_][A-Za-z0-9_]*)\b(?!/)")


# --------------------------------------------------------------------------- #
# Governed schema (graph_metadata.json)                                        #
# --------------------------------------------------------------------------- #
def load_graph_schema(path: str) -> Tuple[Set[str], Set[Tuple[str, str]]]:
    """Return (table names, {(table, column)}) for every structural node in the
    committed graph snapshot."""
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    tables: Set[str] = set()
    columns: Set[Tuple[str, str]] = set()
    for node in doc.get("nodes", []):
        if node.get("node_type") == "table":
            tables.add(node["table_name"])
        elif node.get("node_type") == "column":
            columns.add((node["table_name"], node["column_name"]))
    return tables, columns


# --------------------------------------------------------------------------- #
# OBDA mapping (.obda)                                                         #
# --------------------------------------------------------------------------- #
def parse_obda(path: str) -> List[Dict[str, str]]:
    """Parse the ``[MappingDeclaration]`` block into a list of
    ``{"id", "target", "source"}`` records. ``target`` / ``source`` may span
    multiple lines (continuation lines do not start with a field keyword)."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    start = text.find("[[")
    end = text.find("]]", start + 2)
    body = text[start + 2 : end] if (start != -1 and end != -1) else text

    records: List[Dict[str, str]] = []
    current: Dict[str, str] | None = None
    field: str | None = None
    for raw in body.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        m = re.match(r"^(mappingId|target|source)\s+(.*)$", line.strip())
        if m:
            key, value = m.group(1), m.group(2)
            if key == "mappingId":
                if current:
                    records.append(current)
                current = {"id": value.strip(), "target": "", "source": ""}
                field = None
            elif current is not None:
                field = key
                current[key] = value.strip()
        elif current is not None and field:
            # continuation of the current target/source field
            current[field] = (current[field] + " " + line.strip()).strip()
    if current:
        records.append(current)
    return records


def vocab_terms_in_target(target: str) -> Set[str]:
    """Ontology terms a mapping target references (classes used with ``a`` and
    every property predicate), excluding instance-IRI templates."""
    return set(_VOCAB_TERM_RE.findall(target))


def table_columns_in_source(sql: str) -> Tuple[Set[Tuple[str, str]], Set[str]]:
    """Resolve the base ``(table, column)`` pairs a source SQL reads, seeing
    through aliases, CASE expressions, and joins. Returns
    ``(resolved_pairs, ambiguous_columns)`` where an ambiguous column is an
    unqualified column in a multi-table query that cannot be attributed."""
    import sqlglot
    from sqlglot import exp

    tree = sqlglot.parse_one(sql, read="sqlite")

    alias_to_table: Dict[str, str] = {}
    for tbl in tree.find_all(exp.Table):
        real = tbl.name
        alias_to_table[tbl.alias or tbl.name] = real
    distinct_tables = set(alias_to_table.values())

    pairs: Set[Tuple[str, str]] = set()
    ambiguous: Set[str] = set()
    for col in tree.find_all(exp.Column):
        name = col.name
        qualifier = col.table  # alias / table qualifier, "" when unqualified
        if qualifier:
            pairs.add((alias_to_table.get(qualifier, qualifier), name))
        elif len(distinct_tables) == 1:
            pairs.add((next(iter(distinct_tables)), name))
        else:
            ambiguous.add(name)
    return pairs, ambiguous


# --------------------------------------------------------------------------- #
# Ontology (.ttl)                                                              #
# --------------------------------------------------------------------------- #
def parse_ttl(path: str) -> Tuple[Set[str], Set[str], Dict[str, str]]:
    """Return (declared_classes, declared_properties, {child: parent}) from the
    Turtle ontology. A focused parse (no rdflib dependency): each term is
    declared with its subject at column 0 and its predicates indented beneath."""
    with open(path, encoding="utf-8") as fh:
        raw_lines = fh.readlines()

    # Drop blank and full-line comments, then group lines into per-subject blocks
    # (a new ``:Name`` at column 0 starts a block; indented lines continue it).
    blocks: Dict[str, str] = {}
    current: str | None = None
    buf: List[str] = []
    for raw in raw_lines:
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1] == ":":  # column-0 term subject
            if current is not None:
                blocks[current] = "\n".join(buf)
            m = re.match(r":([A-Za-z_][A-Za-z0-9_]*)", line)
            current = m.group(1) if m else None
            buf = [line]
        elif line[:1].isspace() and current is not None:
            buf.append(line)
        else:  # column-0 non-term line (@prefix, <ontology>) closes the block
            if current is not None:
                blocks[current] = "\n".join(buf)
                current = None
                buf = []
    if current is not None:
        blocks[current] = "\n".join(buf)

    classes: Set[str] = set()
    properties: Set[str] = set()
    subproperty_of: Dict[str, str] = {}
    for subject, body in blocks.items():
        if re.search(r"\ba\s+owl:Class\b", body):
            classes.add(subject)
        if re.search(r"\ba\s+owl:(ObjectProperty|DatatypeProperty)\b", body):
            properties.add(subject)
        m = re.search(r"rdfs:subPropertyOf\s+:([A-Za-z_][A-Za-z0-9_]*)", body)
        if m:
            subproperty_of[subject] = m.group(1)
    return classes, properties, subproperty_of


# --------------------------------------------------------------------------- #
# Drift check                                                                  #
# --------------------------------------------------------------------------- #
def check_drift(mapping_path: str, ontology_path: str, graph_path: str) -> int:
    graph_tables, graph_columns = load_graph_schema(graph_path)
    records = parse_obda(mapping_path)
    classes, properties, subproperty_of = parse_ttl(ontology_path)
    declared = classes | properties

    referenced_pairs: Set[Tuple[str, str]] = set()
    ambiguous_columns: Set[str] = set()
    mapping_terms: Set[str] = set()
    parse_errors: List[str] = []

    for rec in records:
        mapping_terms |= vocab_terms_in_target(rec["target"])
        try:
            pairs, ambiguous = table_columns_in_source(rec["source"])
        except Exception as exc:  # noqa: BLE001 - report any SQLGlot failure
            parse_errors.append(f"{rec['id']}: could not parse source SQL ({exc})")
            continue
        referenced_pairs |= pairs
        if ambiguous:
            for col in sorted(ambiguous):
                parse_errors.append(
                    f"{rec['id']}: unqualified column {col!r} is ambiguous across "
                    "multiple tables — qualify it so drift can be checked"
                )

    # 1. Schema closure: every referenced table/column is a governed column node.
    missing_columns = sorted(p for p in referenced_pairs if p not in graph_columns)
    referenced_tables = {t for t, _ in referenced_pairs}
    missing_tables = sorted(t for t in referenced_tables if t not in graph_tables)

    # 2. Vocabulary closure (mapping -> ontology).
    undeclared_terms = sorted(mapping_terms - declared)

    # 3. Vocabulary closure (ontology -> mapping), allowing parents covered by a
    #    mapped sub-property (sub-property entailment backs the parent property).
    covered_via_entailment = {
        parent for child, parent in subproperty_of.items() if child in mapping_terms
    }
    backed = mapping_terms | covered_via_entailment
    unbacked_terms = sorted(declared - backed)

    print(
        f"ontop drift check: {len(records)} mappings, "
        f"{len(referenced_pairs)} table/column refs, {len(declared)} ontology terms."
    )

    failed = False

    if parse_errors:
        failed = True
        print(f"FAIL: {len(parse_errors)} source-SQL parse problem(s):")
        for err in parse_errors:
            print(f"  - {err}")

    if missing_tables:
        failed = True
        print(f"FAIL: {len(missing_tables)} mapped table(s) absent from the governed schema:")
        for tbl in missing_tables:
            print(f"  - {tbl}")

    if missing_columns:
        failed = True
        print(f"FAIL: {len(missing_columns)} mapped column(s) absent from the governed schema:")
        for tbl, col in missing_columns:
            hint = "" if tbl in graph_tables else "  (table missing too)"
            print(f"  - {tbl}.{col}{hint}")

    if undeclared_terms:
        failed = True
        print(f"FAIL: {len(undeclared_terms)} mapping target term(s) not declared in the ontology:")
        for term in undeclared_terms:
            print(f"  - :{term}")

    if unbacked_terms:
        failed = True
        print(f"FAIL: {len(unbacked_terms)} ontology term(s) declared but not backed by any mapping:")
        for term in unbacked_terms:
            print(f"  - :{term}")

    if failed:
        print("[ontop_drift] FAIL — the mapping/ontology has drifted from the governed schema.")
        return 1

    print(
        "[ontop_drift] OK — mapping columns exist in the governed schema and the "
        "mapping and ontology vocabularies are closed."
    )
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", default=None, help="Path to a single .obda mapping to check (default: all showcases)")
    parser.add_argument("--ontology", default=None, help="Path to a single .ttl ontology to check (default: all showcases)")
    parser.add_argument("--graph", default=DEFAULT_GRAPH, help="Path to graph_metadata.json (default: %(default)s)")
    parser.add_argument(
        "--skip-on-missing",
        action="store_true",
        help="Exit 0 instead of erroring when an input file is absent.",
    )
    args = parser.parse_args(argv)

    # Default: guard EVERY published showcase. A single explicit --mapping/--ontology
    # narrows to one pair (back-compat; the unspecified side falls back to the
    # on-time-delivery default).
    if args.mapping or args.ontology:
        showcases = [(
            "custom",
            args.mapping or DEFAULT_MAPPING,
            args.ontology or DEFAULT_ONTOLOGY,
        )]
    else:
        showcases = DEFAULT_SHOWCASES

    if not os.path.exists(args.graph):
        msg = f"graph metadata not found: {args.graph}"
        if args.skip_on_missing:
            print(f"[ontop_drift] SKIP — {msg}")
            return 0
        print(f"[ontop_drift] ERROR — {msg}", file=sys.stderr)
        return 2

    rc = 0
    for label, mapping, ontology in showcases:
        missing = [
            f"{kind} not found: {path}"
            for kind, path in (("mapping", mapping), ("ontology", ontology))
            if not os.path.exists(path)
        ]
        if missing:
            for msg in missing:
                if args.skip_on_missing:
                    print(f"[ontop_drift] SKIP ({label}) — {msg}")
                else:
                    print(f"[ontop_drift] ERROR ({label}) — {msg}", file=sys.stderr)
            if not args.skip_on_missing:
                return 2
            continue

        print(f"--- showcase: {label} ---")
        rc |= check_drift(mapping, ontology, args.graph)

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
