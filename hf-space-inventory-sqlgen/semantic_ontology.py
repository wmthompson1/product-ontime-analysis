"""
semantic_ontology.py
--------------------
Read-only reader for the concept-layer story of a ground-truth query anchor,
pulled from the governed SQLite `sql_graph_nodes` / `sql_graph_edges` tables
(the source of truth the frozen `graph_metadata.json` is serialized from —
that file is never touched here).

Given a manifest `concept_anchor` (e.g. ``SAFETYSTOCK``), this resolves the
matching concept NODE (concept names are CamelCase in the graph; the manifest
anchor is the uppercased form), then walks the ``resolves_to`` edges INTO the
concept to build the variable → column → table lineage, and surfaces the
concept's `computation_template` when it is a metric (duck typing: a metric
is simply a concept with a non-empty template).

Everything degrades gracefully: a missing DB, missing tables, or an anchor
with no semantic-layer presence returns ``None`` — the caller renders a clear
message instead of an error. Nothing here writes anything, anywhere.
"""

from __future__ import annotations

import os
import sqlite3
from typing import List, Optional


def _column_node_parts(node_key: str) -> tuple:
    """Split a column-node key ``table:column:structural:...`` -> (table, col).

    Keys use the fixed 6-slot composite scheme; the first two slots are the
    physical table and column names for structural column nodes.
    """
    parts = (node_key or "").split(":")
    if len(parts) >= 2:
        return parts[0], parts[1]
    return node_key, ""


def get_semantic_ontology(db_path: str, concept_anchor: str) -> Optional[dict]:
    """Return the concept-layer story for one anchor, or None when absent.

    Result shape:
        {
          "concept_name": str, "concept_key": str,
          "description": str, "domain": str, "perspective": str,
          "computation_template": str ("" when not a metric),
          "is_metric": bool,
          "lineage": [
            {"variable": str, "table": str, "column": str,
             "column_description": str, "weight": int|None,
             "field_component": int|None},
            ...
          ],
        }
    """
    if not concept_anchor or not db_path or not os.path.exists(db_path):
        return None
    try:
        conn = sqlite3.connect(db_path)
    except Exception:
        return None
    try:
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                """
                SELECT _key, _id, concept_name, description, domain,
                       perspective, computation_template
                FROM sql_graph_nodes
                WHERE node_type = 'concept'
                  AND UPPER(concept_name) = UPPER(?)
                """,
                (concept_anchor,),
            ).fetchone()
        except sqlite3.Error:
            return None
        if row is None:
            return None

        template = (row["computation_template"] or "").strip()
        result = {
            "concept_name": row["concept_name"],
            "concept_key": row["_key"],
            "description": row["description"] or "",
            "domain": row["domain"] or "",
            "perspective": row["perspective"] or "",
            "computation_template": template,
            "is_metric": bool(template),
            "stakeholder_perspectives": [],
            "lineage": [],
            "table_context": [],
        }

        # Stakeholder perspectives (schema_perspective_concepts) — the
        # DIFFERENTIATED layer (e.g. General_Ledger / Payables / Receivables)
        # that refines the coarse standard domain frozen on the graph node.
        try:
            result["stakeholder_perspectives"] = [
                r[0] for r in conn.execute(
                    """
                    SELECT p.perspective_name
                    FROM schema_perspective_concepts pc
                    JOIN schema_perspectives p
                         ON p.perspective_id = pc.perspective_id
                    JOIN schema_concepts sc ON sc.concept_id = pc.concept_id
                    WHERE sc.concept_name = ?
                    ORDER BY p.perspective_name
                    """,
                    (row["concept_name"],),
                ).fetchall()
            ]
        except sqlite3.Error:
            pass

        # resolves_to edges run column -> concept; match on the concept's _id.
        try:
            edges = conn.execute(
                """
                SELECT e._from, e.variable_name, e.weight, e.field_component
                FROM sql_graph_edges e
                WHERE e.edge_type = 'resolves_to' AND e._to = ?
                ORDER BY e.field_component, e.variable_name, e._from
                """,
                (row["_id"],),
            ).fetchall()
        except sqlite3.Error:
            edges = []

        lineage: List[dict] = []
        for e in edges:
            # _from is '<prefix>/<node_key>' — take the key after the slash.
            from_key = (e["_from"] or "").rsplit("/", 1)[-1]
            table, column = _column_node_parts(from_key)
            col_desc = ""
            try:
                col_row = conn.execute(
                    """
                    SELECT description FROM sql_graph_nodes
                    WHERE node_type = 'column' AND table_name = ? AND column_name = ?
                    """,
                    (table, column),
                ).fetchone()
                if col_row:
                    col_desc = col_row["description"] or ""
            except sqlite3.Error:
                pass
            if not col_desc:
                # Overlay-only by design: plain-language field descriptions
                # live in api_field_descriptions, never on the graph node.
                try:
                    ov = conn.execute(
                        """
                        SELECT description FROM api_field_descriptions
                        WHERE table_name = ? AND column_name = ?
                        """,
                        (table, column),
                    ).fetchone()
                    if ov:
                        col_desc = ov["description"] or ""
                except sqlite3.Error:
                    pass
            lineage.append(
                {
                    "variable": e["variable_name"] or "",
                    "table": table,
                    "column": column,
                    "column_description": col_desc,
                    "weight": e["weight"],
                    "field_component": e["field_component"],
                }
            )
        result["lineage"] = lineage

        # Table-level meta-context (overlay) for every lineage table.
        seen_tables = []
        for b in lineage:
            if b["table"] and b["table"] not in seen_tables:
                seen_tables.append(b["table"])
        for t in seen_tables:
            try:
                tr = conn.execute(
                    "SELECT description FROM api_table_descriptions "
                    "WHERE table_name = ?",
                    (t,),
                ).fetchone()
            except sqlite3.Error:
                tr = None
            if tr and (tr["description"] or "").strip():
                result["table_context"].append(
                    {"table": t, "description": tr["description"].strip()}
                )

        # SKOS-first overlay: resolve the committed SKOS story for the
        # lineage tables (ledger scheme + corpus vocabulary via bindings).
        result["skos"] = get_skos_overlay(seen_tables)
        return result
    finally:
        conn.close()


def get_skos_overlay(lineage_tables: List[str]) -> Optional[dict]:
    """Resolve the SKOS story for a set of physical lineage tables.

    Walks the committed, fail-closed stores only — nothing is inferred:
      * ledger_bindings: table -> SKOS concept URI (gl_* ledger tables) and
        entity class -> table (e.g. ledger:WorkOrder -> work_order),
      * skos_ledger: the full SKOS records (labels, definition, notation,
        broader chain, narrower members),
      * corpus_vocab: corpus concepts whose skos:closeMatch points at a
        resolved ledger URI (entity terms, lifecycle chain, collections,
        forbidden-synonym governance).

    Returns None when no table has SKOS coverage, or when any committed
    scheme fails to load (the pane then degrades honestly).
    """
    if not lineage_tables:
        return None
    try:
        from skos_ledger import get_ledger_concept_store
        from ledger_bindings import get_ledger_binding_store
        from corpus_vocab import get_corpus_vocab_store
        skos = get_ledger_concept_store()
        bindings = get_ledger_binding_store()
        corpus = get_corpus_vocab_store()
    except Exception:
        return None

    concepts = []
    resolved_uris = set()
    for table in lineage_tables:
        uri = bindings.concept_for_table(table)
        if not uri:
            continue
        c = skos.get(uri)
        if c is None:
            continue
        resolved_uris.add(uri)
        chain = [a.pref_label for a in skos.ancestors(uri)]
        narrower = []
        for n_uri in c.narrower:
            n = skos.get(n_uri)
            if n is None:
                continue
            entry = {
                "pref_label": n.pref_label,
                "definition": n.definition,
                "notation": n.notation,
            }
            if n.notation:
                entry["event_class"] = bindings.class_for_event_type(
                    n.notation
                )
            narrower.append(entry)
        concepts.append(
            {
                "table": table,
                "uri": uri,
                "pref_label": c.pref_label,
                "definition": c.definition,
                "alt_labels": list(c.alt_labels),
                "notation": c.notation,
                "broader_chain": chain,
                "narrower": narrower,
            }
        )

    # Entity grounding: non-ledger tables bound by an OWL entity class
    # (e.g. work_order <- ledger:WorkOrder) pull in the corpus vocabulary
    # via skos:closeMatch — the committed links, never string matching.
    entity_uris = set()
    for table in lineage_tables:
        for b in bindings.entity_bindings:
            if b.table_name == table:
                entity_uris.add(b.entity_class_uri)

    corpus_concepts = []
    lifecycle = []
    forbidden = {}
    if entity_uris:
        for cc in corpus.all_concepts():
            if not any(m in entity_uris for m in cc.close_match):
                continue
            colls = [
                col.pref_label for col in corpus.collections_of(cc.uri)
            ]
            corpus_concepts.append(
                {
                    "uri": cc.uri,
                    "pref_label": cc.pref_label,
                    "definition": cc.definition,
                    "scope_note": cc.scope_note,
                    "hidden_labels": list(cc.hidden_labels),
                    "collections": colls,
                }
            )
        if corpus_concepts:
            # Lifecycle chain (stored work_order.status vocabulary) and the
            # machine-readable forbidden-synonym governance travel with the
            # entity term.
            try:
                chain = corpus.progression_from("corpus:UnreleasedState")
                lifecycle = [
                    {"pref_label": s.pref_label, "notation": s.notation}
                    for s in chain
                ]
            except Exception:
                lifecycle = []
            forbidden = corpus.forbidden_synonyms()

    if not concepts and not corpus_concepts:
        return None
    return {
        "scheme_label": skos.scheme_label,
        "scheme_uri": skos.scheme_uri,
        "concepts": concepts,
        "corpus_scheme_label": corpus.scheme_label,
        "corpus_concepts": corpus_concepts,
        "lifecycle": lifecycle,
        "forbidden_synonyms": forbidden,
    }


def render_semantic_ontology_markdown(
    onto: Optional[dict], concept_anchor: str
) -> str:
    """Markdown pane for the Semantic Ontology tab (graceful degradation)."""
    if not concept_anchor:
        return "Select a ground-truth query above."
    if onto is None:
        return (
            f"**`{concept_anchor}`** has no semantic-layer presence yet — no "
            "concept node with this name exists in the governed "
            "`sql_graph_nodes` table.\n\n"
            "_This is expected for anchors that have not been elevated into "
            "the semantic layer. The Join Topology and SQL tabs still tell "
            "the structural story._"
        )

    lines = [f"### {onto['concept_name']}"]
    if onto["description"]:
        lines.append(f"{onto['description']}\n")

    # ── SKOS story leads ─────────────────────────────────────────────────
    skos = onto.get("skos")
    if skos:
        lines.append(f"#### SKOS concepts — _{skos['scheme_label']}_")
        lines.append(
            "_Resolved from the committed `ledger_skos.jsonld` scheme via "
            "the governed binding map (`ledger_binding_map.json`) — each "
            "lineage table below is bound to exactly one SKOS concept._\n"
        )
        for c in skos["concepts"]:
            title = f"**{c['pref_label']}**"
            if c["alt_labels"]:
                title += " (" + ", ".join(c["alt_labels"]) + ")"
            title += f" ← `{c['table']}`"
            lines.append(f"- {title}")
            lines.append(f"  `{c['uri']}`")
            if c["broader_chain"]:
                lines.append(
                    "  _broader:_ " + " → ".join(c["broader_chain"])
                )
            if c["notation"]:
                lines.append(f"  _notation:_ `{c['notation']}`")
            lines.append(f"  {c['definition']}")
            if c["narrower"]:
                lines.append("  _narrower:_")
                for n in c["narrower"]:
                    tag = f"**{n['pref_label']}**"
                    if n.get("notation"):
                        tag += f" `{n['notation']}`"
                    if n.get("event_class"):
                        tag += f" → `{n['event_class']}`"
                    lines.append(f"    - {tag} — {n['definition']}")
        lines.append("")

        if skos["corpus_concepts"]:
            lines.append(
                f"#### Corpus vocabulary — _{skos['corpus_scheme_label']}_"
            )
            for cc in skos["corpus_concepts"]:
                lines.append(f"- **{cc['pref_label']}**  `{cc['uri']}`")
                lines.append(f"  {cc['definition']}")
                if cc["scope_note"]:
                    lines.append(f"  _Scope:_ {cc['scope_note']}")
                if cc["collections"]:
                    lines.append(
                        "  _Collections:_ "
                        + " · ".join(f"`{x}`" for x in cc["collections"])
                    )
            if skos["lifecycle"]:
                lines.append(
                    "  _Lifecycle progression:_ "
                    + " → ".join(
                        f"**{s['pref_label']}** (`{s['notation']}`)"
                        if s["notation"] else f"**{s['pref_label']}**"
                        for s in skos["lifecycle"]
                    )
                )
            if skos["forbidden_synonyms"]:
                gov = " · ".join(
                    f"~~{syn}~~ → use **{pref}**"
                    for syn, pref in sorted(
                        skos["forbidden_synonyms"].items()
                    )
                )
                lines.append(f"  _Forbidden synonyms:_ {gov}")
            lines.append("")
    else:
        lines.append(
            "_No SKOS coverage — none of this concept's lineage tables is "
            "bound in the governed ledger binding map. The frozen-graph "
            "facts below still tell the structural story._\n"
        )

    sp = onto.get("stakeholder_perspectives") or []
    if sp:
        lines.append(
            "**Stakeholder perspectives:** "
            + " · ".join(f"`{p}`" for p in sp)
            + "  \n_The differentiated placement layer "
            "(`schema_perspective_concepts`)._\n"
        )

    if onto["is_metric"]:
        lines.append("#### Computation template (dialect-agnostic)")
        lines.append(f"```\n{onto['computation_template']}\n```\n")

    if onto["lineage"]:
        lines.append(
            f"#### `resolves_to` lineage — variable → column → table "
            f"({len(onto['lineage'])} bindings)"
        )
        lines.append("| Variable | Physical column | Table | Meaning |")
        lines.append("|---|---|---|---|")
        for b in onto["lineage"]:
            var = f"`{{{b['variable']}}}`" if b["variable"] else "—"
            lines.append(
                f"| {var} | `{b['column']}` | `{b['table']}` | "
                f"{b['column_description'] or ''} |"
            )
        lines.append("")
    else:
        lines.append(
            "_No `resolves_to` bindings — this concept has no column-level "
            "lineage in the semantic layer yet._"
        )

    tc = onto.get("table_context") or []
    if tc:
        lines.append("#### Table meta-context")
        for t in tc:
            lines.append(f"- **`{t['table']}`** — {t['description']}")
        lines.append("")

    # ── Frozen graph facts — compact, supporting only ────────────────────
    facts = [f"concept key `{onto['concept_key']}`"]
    if onto["domain"]:
        facts.append(f"standard domain `{onto['domain']}` (coarse, frozen)")
    if onto["perspective"]:
        facts.append(f"graph perspective `{onto['perspective']}`")
    facts.append(
        "metric: yes (computation template)"
        if onto["is_metric"] else "metric: no (entity concept)"
    )
    lines.append("#### Frozen graph facts")
    lines.append(
        "_Supporting detail from the governed graph node:_ "
        + "  ·  ".join(facts)
        + "\n"
    )

    lines.append(
        "\n---\n_Read-only view of the governed `sql_graph_nodes` / "
        "`sql_graph_edges` tables (the source `graph_metadata.json` is "
        "serialized from). Nothing is executed against the business data._"
    )
    return "\n".join(lines)
