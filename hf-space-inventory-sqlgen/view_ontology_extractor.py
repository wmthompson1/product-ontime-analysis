"""
view_ontology_extractor.py
---------------------------
Reads the ontological structure embedded in each ground-truth SQL view and
makes it a first-class, governed metadata object.

The ground-truth SQL IS the view.  It tells the complete story: the joins
are the relationships, the CTEs provide the hierarchy scaffolding, the WHERE
predicates encode the set-membership rules, and the ORDER/GROUP BY defines
the grain.  SQLGlot is the parser that makes that embedded ontology legible
without executing anything.

Nothing in this module executes SQL against a database.  It operates entirely
on SQL text — metadata in, metadata out.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import sqlglot
from sqlglot import exp

SEMANTICS_VERSION = "mrp_views_v1"

MRP_VIEW_BINDING_KEYS: List[str] = [
    "inventory_atp_20260703_000004",
    "inventory_allocated_20260703_000005",
    "inventory_safetystock_20260703_000006",
    "inventory_leadtimedemand_20260703_000007",
    "inventory_minimumstock_20260703_000008",
    "inventory_maximumstock_20260703_000009",
    "inventory_eoq_20260703_000010",
]

CREATE_SQL_VIEW_ONTOLOGY = """
CREATE TABLE IF NOT EXISTS sql_view_ontology (
    concept_anchor        TEXT PRIMARY KEY,
    binding_key           TEXT NOT NULL,
    view_file             TEXT NOT NULL,
    physical_tables_json  TEXT NOT NULL,
    cte_names_json        TEXT NOT NULL,
    joins_json            TEXT NOT NULL,
    state_predicates_json TEXT NOT NULL,
    grain_columns_json    TEXT NOT NULL,
    time_phased           INTEGER NOT NULL DEFAULT 0,
    temporal_keys_json    TEXT NOT NULL,
    selected_columns_json TEXT NOT NULL,
    semantics_version     TEXT NOT NULL,
    extracted_at          TEXT NOT NULL
)
"""


@dataclass
class JoinRelationship:
    """One JOIN relationship extracted from a view's SQL."""
    left_table: str
    right_table: str
    join_type: str           # INNER | LEFT | CROSS | RIGHT | FULL
    on_condition: str        # full ON expression as SQL string, "" for CROSS
    left_key: Optional[str] = None
    right_key: Optional[str] = None


@dataclass
class ViewOntology:
    """The ontological structure embedded in one ground-truth SQL view."""
    concept_anchor: str
    binding_key: str
    view_file: str
    physical_tables: List[str]
    cte_names: List[str]
    joins: List[dict]
    state_predicates: List[str]
    grain_columns: List[str]
    time_phased: bool
    temporal_keys: List[str]
    selected_columns: List[str]
    semantics_version: str
    extracted_at: str


def _expr_table_name(expr) -> str:
    if isinstance(expr, exp.Table):
        return expr.name or ""
    if isinstance(expr, exp.Subquery):
        return expr.alias or "subquery"
    if hasattr(expr, "name") and expr.name:
        return expr.name
    return ""


def _extract_equi_keys(on_expr) -> tuple:
    if on_expr is None:
        return None, None
    if isinstance(on_expr, exp.EQ):
        left, right = on_expr.this, on_expr.expression
        if isinstance(left, exp.Column) and isinstance(right, exp.Column):
            return left.name, right.name
    return None, None


def _extract_joins_from_selects(ast) -> List[JoinRelationship]:
    results: List[JoinRelationship] = []
    seen: set = set()
    for select in ast.find_all(exp.Select):
        from_clause = select.args.get("from_")  # SQLGlot uses "from_" — "from" is a Python keyword
        if not from_clause:
            continue
        left_name = _expr_table_name(from_clause.this)
        if not left_name:
            continue
        for join in select.args.get("joins") or []:
            right_name = _expr_table_name(join.this)
            if not right_name:
                continue
            side = (join.args.get("side") or "").upper()
            kind = (join.args.get("kind") or "").upper()
            kind = " ".join(filter(None, [side, kind])) or "INNER"
            on_expr = join.args.get("on")
            on_str = on_expr.sql(dialect="sqlite") if on_expr else ""
            lk, rk = _extract_equi_keys(on_expr)
            # Dedup on the full relationship, INCLUDING the ON predicate: two
            # joins between the same table pair but with different ON conditions
            # (e.g. self-joins with different aliases/keys) are distinct
            # relationships and must both survive. Only byte-identical repeats
            # (the same join re-seen across nested SELECT scopes) collapse.
            key = (left_name, right_name, kind, on_str)
            if key not in seen:
                seen.add(key)
                results.append(JoinRelationship(
                    left_table=left_name,
                    right_table=right_name,
                    join_type=kind,
                    on_condition=on_str,
                    left_key=lk,
                    right_key=rk,
                ))
    return results


def _extract_state_predicates(ast) -> List[str]:
    seen: set = set()
    predicates: List[str] = []
    for where in ast.find_all(exp.Where):
        pred = where.this.sql(dialect="sqlite")
        if pred and pred not in seen:
            seen.add(pred)
            predicates.append(pred)
    return predicates


def _extract_grain(main_select) -> List[str]:
    cols: List[str] = []
    seen: set = set()
    for clause_key in ("group", "order"):
        clause = main_select.args.get(clause_key)
        if not clause:
            continue
        for col in clause.find_all(exp.Column):
            name = col.name
            if name and name not in seen:
                seen.add(name)
                cols.append(name)
    return cols


def _extract_selected_columns(main_select) -> List[str]:
    cols: List[str] = []
    for expr in main_select.expressions:
        if isinstance(expr, exp.Star):
            cols.append("*")
        elif isinstance(expr, exp.Alias):
            cols.append(expr.alias)
        elif isinstance(expr, exp.Column):
            cols.append(expr.name)
        elif hasattr(expr, "alias") and expr.alias:
            cols.append(expr.alias)
        else:
            cols.append(expr.sql(dialect="sqlite")[:80])
    return cols


def _detect_time_phasing(cte_names: List[str], ast) -> tuple:
    time_phased = any(
        "bucket" in n.lower() or "horizon" in n.lower()
        for n in cte_names
    )
    if not time_phased:
        time_phased = ast.find(exp.Window) is not None

    main_select = ast if isinstance(ast, exp.Select) else ast.find(exp.Select)
    temporal_keys: List[str] = []
    if main_select:
        for expr in main_select.expressions:
            alias = ""
            if isinstance(expr, exp.Alias):
                alias = expr.alias
            elif isinstance(expr, exp.Column):
                alias = expr.name
            elif hasattr(expr, "alias") and expr.alias:
                alias = expr.alias
            if alias and any(k in alias.lower() for k in ("bucket", "idx", "period")):
                temporal_keys.append(alias)
    return time_phased, temporal_keys


def extract_view_ontology(
    sql_text: str,
    binding_key: str,
    concept_anchor: str,
    view_file: str,
) -> ViewOntology:
    """Parse a ground-truth SQL view and return its embedded ViewOntology.

    Pure AST analysis via SQLGlot — nothing is executed against a database.
    """
    ast = sqlglot.parse(sql_text, read="sqlite")[0]

    cte_names = [cte.alias for cte in ast.find_all(exp.CTE) if cte.alias]
    cte_set = set(cte_names)

    seen_tables: set = set()
    physical_tables: List[str] = []
    for table in ast.find_all(exp.Table):
        name = table.name
        if name and name not in cte_set and name not in seen_tables:
            seen_tables.add(name)
            physical_tables.append(name)

    joins = _extract_joins_from_selects(ast)
    state_predicates = _extract_state_predicates(ast)

    main_select = ast if isinstance(ast, exp.Select) else ast.find(exp.Select)
    grain_columns = _extract_grain(main_select) if main_select else []
    selected_columns = _extract_selected_columns(main_select) if main_select else []
    time_phased, temporal_keys = _detect_time_phasing(cte_names, ast)

    return ViewOntology(
        concept_anchor=concept_anchor,
        binding_key=binding_key,
        view_file=view_file,
        physical_tables=physical_tables,
        cte_names=cte_names,
        joins=[asdict(j) for j in joins],
        state_predicates=state_predicates,
        grain_columns=grain_columns,
        time_phased=time_phased,
        temporal_keys=temporal_keys,
        selected_columns=selected_columns,
        semantics_version=SEMANTICS_VERSION,
        extracted_at=datetime.now(timezone.utc).isoformat(),
    )


def extract_all_mrp_views(manifest_path: str, base_dir: str) -> List[ViewOntology]:
    """Extract ViewOntology for all 7 MRP views listed in the manifest."""
    with open(manifest_path) as f:
        manifest = json.load(f)
    snippets = manifest.get("approved_snippets", {})

    results: List[ViewOntology] = []
    for binding_key in MRP_VIEW_BINDING_KEYS:
        entry = snippets.get(binding_key)
        if not entry:
            continue
        concept_anchor = entry.get("concept_anchor", binding_key.upper())
        view_file = entry.get("file_path", "")
        sql_path = Path(base_dir) / view_file
        if not sql_path.exists():
            print(f"[view_ontology_extractor] View file not found: {sql_path}")
            continue
        sql_text = sql_path.read_text(encoding="utf-8")
        try:
            vo = extract_view_ontology(sql_text, binding_key, concept_anchor, view_file)
            results.append(vo)
        except Exception as exc:
            print(f"[view_ontology_extractor] Failed to extract {binding_key}: {exc}")
    return results


def create_view_ontology_table(conn: sqlite3.Connection) -> None:
    """Create sql_view_ontology if it does not already exist."""
    conn.execute(CREATE_SQL_VIEW_ONTOLOGY)
    conn.commit()


def seed_view_ontology_table(
    conn: sqlite3.Connection,
    view_ontologies: List[ViewOntology],
) -> int:
    """INSERT OR REPLACE all ViewOntology records. Idempotent on every boot."""
    cur = conn.cursor()
    for vo in view_ontologies:
        cur.execute(
            """
            INSERT OR REPLACE INTO sql_view_ontology (
                concept_anchor, binding_key, view_file,
                physical_tables_json, cte_names_json, joins_json,
                state_predicates_json, grain_columns_json,
                time_phased, temporal_keys_json, selected_columns_json,
                semantics_version, extracted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                vo.concept_anchor, vo.binding_key, vo.view_file,
                json.dumps(vo.physical_tables),
                json.dumps(vo.cte_names),
                json.dumps(vo.joins),
                json.dumps(vo.state_predicates),
                json.dumps(vo.grain_columns),
                1 if vo.time_phased else 0,
                json.dumps(vo.temporal_keys),
                json.dumps(vo.selected_columns),
                vo.semantics_version,
                vo.extracted_at,
            ),
        )
    conn.commit()
    return len(view_ontologies)


def get_view_ontology(conn: sqlite3.Connection, concept_anchor: str) -> Optional[dict]:
    """Return one ViewOntology as a decoded dict, or None if not found."""
    cur = conn.execute(
        "SELECT * FROM sql_view_ontology WHERE concept_anchor = ?",
        (concept_anchor,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    record = dict(zip([d[0] for d in cur.description], row))
    for key in (
        "physical_tables_json", "cte_names_json", "joins_json",
        "state_predicates_json", "grain_columns_json",
        "temporal_keys_json", "selected_columns_json",
    ):
        record[key] = json.loads(record[key])
    record["time_phased"] = bool(record["time_phased"])
    return record


def list_view_ontologies(conn: sqlite3.Connection) -> List[dict]:
    """Return all seeded view ontologies as decoded dicts (summary fields only)."""
    cur = conn.execute(
        "SELECT concept_anchor, binding_key, time_phased, "
        "physical_tables_json, semantics_version "
        "FROM sql_view_ontology ORDER BY concept_anchor"
    )
    rows = []
    for row in cur.fetchall():
        r = dict(zip([d[0] for d in cur.description], row))
        r["physical_tables_json"] = json.loads(r["physical_tables_json"])
        r["time_phased"] = bool(r["time_phased"])
        rows.append(r)
    return rows
