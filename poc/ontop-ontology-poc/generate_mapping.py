#!/usr/bin/env python3
"""
Ontop OBDA mapping generator (offline, file -> file, deterministic).
====================================================================

The On-Time Delivery showcase's OBDA mapping
(``mapping/on_time_delivery.obda``) used to be hand-authored, so a rename or
drop in the governed schema could silently desync it. This script regenerates
that mapping (and the mechanically-derivable ontology vocabulary terms) from the
governed source of truth instead, so the published virtual graph is DERIVED, not
hand-maintained.

Two inputs:

  1. ``mapping/on_time_delivery_manifest.json`` — the stable PUBLISHING decisions
     that are not present in the governed schema (ontology term names + namespace,
     the hand-governed quality business rule, the supplier-id CAST, the
     required_date filter, and the entity / optionality modelling).
  2. ``replit_integrations/graph_metadata.json`` — the governed schema. Every
     VOLATILE physical fact is resolved from here: that each referenced table /
     column exists, each column's datatype (-> xsd type), the foreign-key join
     columns, and the on-time metric's ``computation_template`` + its
     ``variable_name`` bindings (the per-delivery CASE is the template with the
     outer ``AVG(...)`` stripped and ``{variable}`` placeholders substituted to
     ``alias.column``). If any of those facts is missing, generation FAILS LOUDLY
     — that is the whole point: a schema change can no longer silently desync the
     mapping.

The output is byte-identical to the committed hand-authored mapping, which is
what makes the switch provably lossless (see ``mapping_generation_check.py``).

Outputs (written in place by default):
  * ``mapping/on_time_delivery.obda``                  — the OBDA mapping
  * ``ontology/on_time_delivery.generated.vocab.ttl``  — the mechanically
    derivable vocabulary terms (classes + property label/domain/range). The
    runtime ontology (``ontology/on_time_delivery.ttl``) additionally declares
    the subPropertyOf hierarchy and the prose rationale, which are hand-authored
    governance and intentionally OUT OF SCOPE for generation.

Run:

    python poc/ontop-ontology-poc/generate_mapping.py            # regenerate
    python poc/ontop-ontology-poc/generate_mapping.py --check    # verify only
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

POC_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(POC_DIR, "..", ".."))

DEFAULT_MANIFEST = os.path.join(POC_DIR, "mapping", "on_time_delivery_manifest.json")
DEFAULT_OBDA = os.path.join(POC_DIR, "mapping", "on_time_delivery.obda")
DEFAULT_VOCAB = os.path.join(POC_DIR, "ontology", "on_time_delivery.generated.vocab.ttl")
DEFAULT_GRAPH = os.path.join(REPO_ROOT, "replit_integrations", "graph_metadata.json")

# OBDA fields are aligned to a fixed keyword column (left-justified width 16).
_KW_WIDTH = 16

_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


class GenError(Exception):
    """A governed-schema fact the manifest relies on is missing or malformed."""


# --------------------------------------------------------------------------- #
# Governed schema resolver (graph_metadata.json)                              #
# --------------------------------------------------------------------------- #
class Graph:
    """Read-only view over the committed governed-schema snapshot."""

    def __init__(self, doc: dict):
        nodes = doc.get("nodes", [])
        self.nodes_by_key: Dict[str, dict] = {n["_key"]: n for n in nodes}
        self.tables: Set[str] = {
            n["table_name"] for n in nodes if n.get("node_type") == "table"
        }
        self.columns: Dict[Tuple[str, str], dict] = {
            (n["table_name"], n["column_name"]): n
            for n in nodes
            if n.get("node_type") == "column"
        }
        self.concepts: Dict[str, dict] = {
            n["concept_name"]: n for n in nodes if n.get("node_type") == "concept"
        }
        self.edges: List[dict] = doc.get("edges", [])

    def _node_tc(self, ref: str) -> Tuple[Optional[str], Optional[str]]:
        node = self.nodes_by_key.get(ref.split("/", 1)[-1])
        if not node:
            return (None, None)
        return (node.get("table_name"), node.get("column_name"))

    def require_table(self, table: str) -> None:
        if table not in self.tables:
            raise GenError(f"table {table!r} is absent from the governed schema")

    def require_column(self, table: str, column: str) -> None:
        if (table, column) not in self.columns:
            raise GenError(
                f"column {table}.{column} is absent from the governed schema"
            )

    def column_type(self, table: str, column: str) -> str:
        self.require_column(table, column)
        col_type = self.columns[(table, column)].get("column_type")
        if not col_type:
            raise GenError(f"column {table}.{column} has no column_type")
        return col_type

    def find_fk(
        self, child_table: str, parent_table: str, child_col: Optional[str] = None
    ) -> Optional[Tuple[str, str]]:
        """Return (child_column, parent_column) of a structural ``references``
        edge from child_table to parent_table (optionally pinned to child_col)."""
        for edge in self.edges:
            if edge.get("edge_type") != "references":
                continue
            ct, cc = self._node_tc(edge["_from"])
            pt = edge.get("references_table")
            pc = edge.get("references_column")
            if ct == child_table and pt == parent_table:
                if child_col is None or cc == child_col:
                    return (cc, pc)
        return None

    def concept(self, name: str) -> dict:
        node = self.concepts.get(name)
        if not node:
            raise GenError(f"concept {name!r} is absent from the governed schema")
        return node

    def metric_bindings(self, concept_key: str) -> Dict[str, Tuple[str, str]]:
        """variable_name -> (table, column) for a concept's resolves_to bindings.
        Duplicate bindings across perspectives are allowed; a conflict fails."""
        binds: Dict[str, Tuple[str, str]] = {}
        for edge in self.edges:
            if edge.get("edge_type") != "resolves_to" or not edge.get("variable_name"):
                continue
            if edge["_to"].split("/", 1)[-1] != concept_key:
                continue
            table, column = self._node_tc(edge["_from"])
            var = edge["variable_name"]
            if var in binds and binds[var] != (table, column):
                raise GenError(
                    f"conflicting binding for {{{var}}} on concept {concept_key}: "
                    f"{binds[var]} vs {(table, column)}"
                )
            binds[var] = (table, column)
        return binds


# --------------------------------------------------------------------------- #
# Small helpers                                                                #
# --------------------------------------------------------------------------- #
def _xsd_for_type(manifest: dict, col_type: str) -> str:
    type_map = manifest["literal_type_map"]
    if col_type not in type_map:
        raise GenError(
            f"column type {col_type!r} has no xsd mapping in manifest.literal_type_map"
        )
    return type_map[col_type]


def _literal_suffix(xsd: str, col_type: str = "TEXT") -> str:
    """xsd:string literals on TEXT columns carry no ``^^`` annotation (Ontop
    infers string from the JDBC TEXT type); every other case is annotated
    explicitly — including xsd:string on non-TEXT columns (e.g. SQLite
    DATETIME), whose JDBC type Ontop cannot map to an RDF datatype on its
    own (UnknownDatatypeException with inferDefaultDatatype disabled)."""
    return "" if (xsd == "xsd:string" and col_type == "TEXT") else f"^^{xsd}"


def _key_select_expr(cls: dict) -> str:
    """SELECT term for a class key column, applying its declared CAST if any."""
    key = cls["key_column"]
    cast = cls.get("key_cast")
    return f"CAST({key} AS {cast}) AS {key}" if cast else key


def _alias_for(table: str, taken: Set[str]) -> str:
    """Deterministic, collision-free SQL alias: shortest unique lowercase prefix
    of the table name, falling back to first-letter + index."""
    lower = table.lower()
    for n in range(1, len(lower) + 1):
        cand = lower[:n]
        if cand not in taken:
            return cand
    i = 2
    while f"{lower[:1]}{i}" in taken:
        i += 1
    return f"{lower[:1]}{i}"


def _validate_expr_columns(graph: Graph, expr: str, table: str) -> None:
    """Every column referenced in a single-table SQL fragment must exist."""
    import sqlglot
    from sqlglot import exp

    try:
        tree = sqlglot.parse_one(expr, read="sqlite")
    except Exception as exc:  # noqa: BLE001
        raise GenError(f"could not parse SQL fragment {expr!r}: {exc}") from exc
    for col in tree.find_all(exp.Column):
        graph.require_column(table, col.name)


def _strip_aggregate(template: str, agg_name: str = "AVG") -> str:
    """Return the inner expression of ``AGG(<expr>)``, keeping ``{placeholders}``
    intact. The shape is validated with SQLGlot (placeholders swapped for a dummy
    column first, since braces are not valid SQL) so a template that is no longer
    ``AVG`` of a single CASE fails loudly rather than producing wrong SQL."""
    import sqlglot
    from sqlglot import exp

    text = template.strip()
    probe = _PLACEHOLDER_RE.sub("dummy_col", text)
    try:
        tree = sqlglot.parse_one(probe, read="sqlite")
    except Exception as exc:  # noqa: BLE001
        raise GenError(f"could not parse computation_template {template!r}: {exc}") from exc
    if not isinstance(tree, exp.Avg):
        raise GenError(
            f"computation_template root is not {agg_name}(...): {template!r}"
        )
    if not isinstance(tree.this, exp.Case):
        raise GenError(
            f"computation_template {agg_name}(...) does not wrap a single CASE: {template!r}"
        )

    prefix = agg_name + "("
    if not (text.upper().startswith(prefix) and text.endswith(")")):
        raise GenError(f"computation_template is not a literal {agg_name}(...): {template!r}")
    inner = text[len(prefix):-1].strip()

    inner_probe = _PLACEHOLDER_RE.sub("dummy_col", inner)
    if not isinstance(sqlglot.parse_one(inner_probe, read="sqlite"), exp.Case):
        raise GenError(f"stripped computation_template is not a CASE: {template!r}")
    return inner


# --------------------------------------------------------------------------- #
# Per-mapping renderers                                                        #
# --------------------------------------------------------------------------- #
def _render_entity(manifest: dict, graph: Graph, m: dict) -> Tuple[str, str]:
    classes = manifest["classes"]
    cls = classes[m["class"]]
    table = cls["table"]
    graph.require_table(table)
    graph.require_column(table, cls["key_column"])

    select_cols: List[str] = [_key_select_expr(cls)]
    target_parts: List[str] = [f'{cls["iri_template"]} a :{m["class"]}']

    for dp in m.get("datatype_properties", []):
        column = dp["column"]
        col_type = graph.column_type(table, column)
        xsd = _xsd_for_type(manifest, col_type)
        select_cols.append(column)
        target_parts.append(
            f':{dp["term"]} {{{column}}}{_literal_suffix(xsd, col_type)}'
        )

    for op in m.get("object_properties", []):
        fk_col = op["fk_column"]
        graph.require_column(table, fk_col)
        target_cls = classes[op["target_class"]]
        fk = graph.find_fk(table, target_cls["table"], fk_col)
        if fk is None:
            raise GenError(
                f"{m['id']}: no references edge {table}.{fk_col} -> "
                f"{target_cls['table']} in the governed schema"
            )
        if fk[1] != target_cls["key_column"]:
            raise GenError(
                f"{m['id']}: references edge {table}.{fk_col} points at "
                f"{target_cls['table']}.{fk[1]}, not the {op['target_class']} key "
                f"{target_cls['key_column']}"
            )
        # The target IRI template is written in terms of the TARGET class key.
        # When the child FK column is named differently (e.g. gl_events.job_id
        # -> work_order.wo_id) alias it so the template placeholder resolves.
        if fk_col == target_cls["key_column"]:
            select_cols.append(fk_col)
        else:
            select_cols.append(f'{fk_col} AS {target_cls["key_column"]}')
        target_parts.append(f':{op["term"]} {target_cls["iri_template"]}')

    source = f"SELECT {', '.join(select_cols)} FROM {table}"
    where = m.get("where")
    if where:
        _validate_expr_columns(graph, where, table)
        source += f" WHERE {where}"

    target = " ; ".join(target_parts) + " ."
    return target, source


def _render_metric(manifest: dict, graph: Graph, m: dict) -> Tuple[str, str]:
    classes = manifest["classes"]
    cls = classes[m["subject_class"]]
    subj_table = cls["table"]
    graph.require_table(subj_table)
    graph.require_column(subj_table, cls["key_column"])

    concept = graph.concept(m["concept"])
    template = concept.get("computation_template")
    if not template:
        raise GenError(f"{m['id']}: concept {m['concept']} has no computation_template")
    inner = _strip_aggregate(template)

    placeholders = set(_PLACEHOLDER_RE.findall(template))
    binds = graph.metric_bindings(concept["_key"])
    missing = placeholders - set(binds)
    if missing:
        raise GenError(
            f"{m['id']}: concept {m['concept']} is missing bindings for "
            f"{sorted('{' + v + '}' for v in missing)}"
        )
    for var in placeholders:
        graph.require_column(*binds[var])

    binding_tables = {binds[v][0] for v in placeholders}
    involved = [subj_table] + sorted(binding_tables - {subj_table})
    aliases: Dict[str, str] = {}
    taken: Set[str] = set()
    for table in involved:
        alias = _alias_for(table, taken)
        aliases[table] = alias
        taken.add(alias)

    expr = inner
    for var in placeholders:
        table, column = binds[var]
        expr = expr.replace("{" + var + "}", f"{aliases[table]}.{column}")
    if "{" in expr or "}" in expr:
        raise GenError(f"{m['id']}: unsubstituted placeholder in {expr!r}")

    key = cls["key_column"]
    select = (
        f"{aliases[subj_table]}.{key} AS {key}, {expr} AS {m['score_alias']}"
    )
    from_clause = f"{subj_table} {aliases[subj_table]}"
    for table in involved[1:]:
        forward = graph.find_fk(subj_table, table)
        if forward is not None:
            cc, pc = forward
            on = f"{aliases[subj_table]}.{cc} = {aliases[table]}.{pc}"
        else:
            backward = graph.find_fk(table, subj_table)
            if backward is None:
                raise GenError(
                    f"{m['id']}: no references edge joining {subj_table} and {table}"
                )
            cc, pc = backward
            on = f"{aliases[table]}.{cc} = {aliases[subj_table]}.{pc}"
        from_clause += f" JOIN {table} {aliases[table]} ON {on}"

    source = f"SELECT {select} FROM {from_clause}"
    suffix = _literal_suffix(m["score_datatype"])
    target = f'{cls["iri_template"]} :{m["property"]} {{{m["score_alias"]}}}{suffix} .'
    return target, source


def _render_expression(manifest: dict, graph: Graph, m: dict) -> Tuple[str, str]:
    classes = manifest["classes"]
    cls = classes[m["subject_class"]]
    table = m["table"]
    graph.require_table(table)
    if cls["table"] != table:
        raise GenError(
            f"{m['id']}: subject_class {m['subject_class']} is on table "
            f"{cls['table']}, not {table}"
        )
    graph.require_column(table, cls["key_column"])
    _validate_expr_columns(graph, m["expression"], table)

    source = (
        f"SELECT {cls['key_column']}, {m['expression']} "
        f"AS {m['score_alias']} FROM {table}"
    )
    suffix = _literal_suffix(m["score_datatype"])
    target = f'{cls["iri_template"]} :{m["property"]} {{{m["score_alias"]}}}{suffix} .'
    return target, source


def _render_relationship(manifest: dict, graph: Graph, m: dict) -> Tuple[str, str]:
    classes = manifest["classes"]
    subj = classes[m["subject_class"]]
    obj = classes[m["object_class"]]
    table = m["table"]
    graph.require_table(table)
    graph.require_column(table, subj["key_column"])
    graph.require_column(table, obj["key_column"])

    subj_key_expr = _key_select_expr(subj)
    source = f"SELECT {subj_key_expr}, {obj['key_column']} FROM {table}"
    target = f'{subj["iri_template"]} :{m["property"]} {obj["iri_template"]} .'
    return target, source


_RENDERERS = {
    "entity": _render_entity,
    "metric": _render_metric,
    "expression": _render_expression,
    "relationship": _render_relationship,
}


# --------------------------------------------------------------------------- #
# OBDA + vocabulary rendering                                                  #
# --------------------------------------------------------------------------- #
def render_obda(manifest: dict, graph: Graph) -> str:
    """Render the full ``.obda`` text from the manifest + governed schema."""
    lines: List[str] = ["[PrefixDeclaration]"]
    for label, iri in manifest["prefixes"]:
        lines.append(f"{label:<{_KW_WIDTH}}{iri}")
    lines.append("")
    lines.append("[MappingDeclaration] @collection [[")
    lines.append("")
    for m in manifest["mappings"]:
        renderer = _RENDERERS.get(m["kind"])
        if renderer is None:
            raise GenError(f"{m['id']}: unknown mapping kind {m['kind']!r}")
        target, source = renderer(manifest, graph, m)
        lines.append(f"{'mappingId':<{_KW_WIDTH}}{m['id']}")
        lines.append(f"{'target':<{_KW_WIDTH}}{target}")
        lines.append(f"{'source':<{_KW_WIDTH}}{source}")
        lines.append("")
    lines.append("]]")
    return "\n".join(lines) + "\n"


def collect_vocab(manifest: dict, graph: Graph) -> Tuple[List[dict], List[dict]]:
    """Return (classes, properties) descriptors for the mechanically-derivable
    vocabulary. Domain/range follow directly from the mapping kind:
      * entity datatype property -> domain = class, range = column's xsd type
      * entity object property   -> domain = class, range = target class
      * metric / expression      -> domain = subject class, range = score type
      * relationship             -> NO domain (minted from a fact table), range = object class
    """
    classes_meta = manifest["classes"]
    used_classes: List[str] = []
    props: List[dict] = []
    seen_props: Set[str] = set()

    def add_class(name: str) -> None:
        if name not in used_classes:
            used_classes.append(name)

    def add_prop(prop: dict) -> None:
        if prop["term"] in seen_props:
            return
        seen_props.add(prop["term"])
        props.append(prop)

    for m in manifest["mappings"]:
        kind = m["kind"]
        if kind == "entity":
            cls = m["class"]
            add_class(cls)
            table = classes_meta[cls]["table"]
            for dp in m.get("datatype_properties", []):
                xsd = _xsd_for_type(manifest, graph.column_type(table, dp["column"]))
                add_prop({
                    "term": dp["term"], "label": dp["label"], "kind": "datatype",
                    "domain": cls, "range": xsd,
                })
            for op in m.get("object_properties", []):
                add_class(op["target_class"])
                add_prop({
                    "term": op["term"], "label": op["label"], "kind": "object",
                    "domain": cls, "range": op["target_class"], "range_is_class": True,
                })
        elif kind in ("metric", "expression"):
            cls = m["subject_class"]
            add_class(cls)
            add_prop({
                "term": m["property"], "label": m["label"], "kind": "datatype",
                "domain": cls, "range": m["score_datatype"],
            })
        elif kind == "relationship":
            add_class(m["subject_class"])
            add_class(m["object_class"])
            add_prop({
                "term": m["property"], "label": m["label"], "kind": "object",
                "domain": None, "range": m["object_class"], "range_is_class": True,
            })
        else:
            raise GenError(f"{m['id']}: unknown mapping kind {kind!r}")

    classes = [{"term": c, "label": classes_meta[c]["label"]} for c in used_classes]
    return classes, props


def render_vocab_ttl(manifest: dict, graph: Graph) -> str:
    classes, props = collect_vocab(manifest, graph)
    out: List[str] = [
        "# AUTO-GENERATED by generate_mapping.py — DO NOT EDIT BY HAND.",
        "# Mechanically-derivable vocabulary for the On-Time Delivery showcase:",
        "# classes and property label/domain/range, derived from the manifest +",
        "# the governed schema (replit_integrations/graph_metadata.json).",
        "# The runtime ontology (on_time_delivery.ttl) additionally declares the",
        "# subPropertyOf hierarchy and the prose rationale, which are hand-authored",
        "# governance and intentionally out of scope for generation.",
        "# Regenerate: python poc/ontop-ontology-poc/generate_mapping.py",
    ]
    for label, iri in manifest["prefixes"]:
        if label in (":", "owl:", "rdfs:", "xsd:"):
            out.append(f"@prefix {label:<6}<{iri}> .")
    out.append("")

    for cls in classes:
        out.append(f':{cls["term"]} a owl:Class ;')
        out.append(f'    rdfs:label "{cls["label"]}" .')
        out.append("")

    for prop in props:
        decl = "owl:ObjectProperty" if prop["kind"] == "object" else "owl:DatatypeProperty"
        out.append(f':{prop["term"]} a {decl} ;')
        out.append(f'    rdfs:label "{prop["label"]}" ;')
        if prop.get("domain"):
            out.append(f'    rdfs:domain :{prop["domain"]} ;')
        if prop.get("range_is_class"):
            out.append(f'    rdfs:range  :{prop["range"]} .')
        else:
            out.append(f'    rdfs:range  {prop["range"]} .')
        out.append("")

    return "\n".join(out).rstrip("\n") + "\n"


def generated_terms(manifest: dict, graph: Graph) -> Set[str]:
    """The set of ontology term names the generator produces (classes + props)."""
    classes, props = collect_vocab(manifest, graph)
    return {c["term"] for c in classes} | {p["term"] for p in props}


# --------------------------------------------------------------------------- #
# Loading                                                                      #
# --------------------------------------------------------------------------- #
def load_manifest(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_graph(path: str) -> Graph:
    with open(path, encoding="utf-8") as fh:
        return Graph(json.load(fh))


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--graph", default=DEFAULT_GRAPH)
    parser.add_argument("--obda-out", default=DEFAULT_OBDA)
    parser.add_argument("--vocab-out", default=DEFAULT_VOCAB)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write; print whether the on-disk files already match.",
    )
    args = parser.parse_args(argv)

    try:
        manifest = load_manifest(args.manifest)
        graph = load_graph(args.graph)
        obda_text = render_obda(manifest, graph)
        vocab_text = render_vocab_ttl(manifest, graph)
    except GenError as exc:
        print(f"[generate_mapping] ERROR — {exc}", file=sys.stderr)
        return 2

    if args.check:
        ok = True
        for label, path, text in (
            ("OBDA mapping", args.obda_out, obda_text),
            ("vocabulary", args.vocab_out, vocab_text),
        ):
            current = ""
            if os.path.exists(path):
                with open(path, encoding="utf-8") as fh:
                    current = fh.read()
            status = "up to date" if current == text else "OUT OF DATE"
            if current != text:
                ok = False
            print(f"[generate_mapping] {label}: {status} ({path})")
        return 0 if ok else 1

    with open(args.obda_out, "w", encoding="utf-8") as fh:
        fh.write(obda_text)
    with open(args.vocab_out, "w", encoding="utf-8") as fh:
        fh.write(vocab_text)
    print(
        f"[generate_mapping] wrote {len(manifest['mappings'])} mappings -> "
        f"{args.obda_out}"
    )
    print(f"[generate_mapping] wrote vocabulary terms -> {args.vocab_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
