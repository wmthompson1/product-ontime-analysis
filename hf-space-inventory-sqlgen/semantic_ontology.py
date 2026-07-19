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
        return result
    finally:
        conn.close()


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

    lines = [f"### {onto['concept_name']}  —  concept node"]
    lines.append(f"`{onto['concept_key']}`\n")
    if onto["description"]:
        lines.append(f"{onto['description']}\n")

    facts = []
    if onto["domain"]:
        facts.append(f"**Standard domain:** `{onto['domain']}` _(coarse, frozen on the graph node)_")
    if onto["perspective"]:
        facts.append(f"**Graph perspective:** `{onto['perspective']}`")
    facts.append(
        "**Metric:** yes — carries a computation template"
        if onto["is_metric"]
        else "**Metric:** no — entity concept (no computation template)"
    )
    lines.append("  ·  ".join(facts) + "\n")

    sp = onto.get("stakeholder_perspectives") or []
    if sp:
        lines.append(
            "**Stakeholder perspectives:** "
            + " · ".join(f"`{p}`" for p in sp)
            + "  \n_The differentiated placement layer "
            "(`schema_perspective_concepts`) — finer-grained than the "
            "standard domain above._\n"
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

    lines.append(
        "\n---\n_Read-only view of the governed `sql_graph_nodes` / "
        "`sql_graph_edges` tables (the source `graph_metadata.json` is "
        "serialized from). Nothing is executed against the business data._"
    )
    return "\n".join(lines)
