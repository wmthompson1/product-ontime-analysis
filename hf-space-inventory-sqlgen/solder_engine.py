"""
SolderEngine - Semantic Transpilation Engine
=============================================
Takes APPROVED SQL snippets from the Reviewer Manifest and assembles
final executable queries using SQLGlot AST manipulation, guided by
perspective elevation weights from the semantic graph.

The Solder Pattern:
  1. Path Resolution: Find APPROVED binding for requested Concept
  2. Elevation Check: Use ELEVATES/SUPPRESSES weights to select snippet
  3. AST Manipulation: Parse SQL via SQLGlot, rename aliases, handle joins
  4. Final Generation: Output sanitized, optimized SQL for target dialect
"""

import os
import json
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "app_schema")
SQLITE_DB_PATH = os.path.join(SCHEMA_DIR, "manufacturing.db")
GROUND_TRUTH_DIR = os.path.join(SCHEMA_DIR, "ground_truth")
MANIFEST_PATH = os.path.join(GROUND_TRUTH_DIR, "reviewer_manifest.json")


@dataclass
class SolderBinding:
    binding_key: str
    perspective: str
    concept_anchor: str
    logic_type: str
    sql_snippet_path: str
    sme_justification: str
    validation_status: str
    sql_text: str = ""


@dataclass
class ElevationEdge:
    intent_name: str
    concept_name: str
    weight: float
    explanation: str
    perspective_name: str = ""
    table_name: str = ""
    field_name: str = ""
    context_hint: str = ""


@dataclass
class SolderResult:
    original_sql: str
    soldered_sql: str
    dialect: str
    binding_key: str
    perspective: str
    concept: str
    logic_type: str
    elevation_weight: float
    ast_operations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class SolderEngine:

    def __init__(self, db_path: str = None, manifest_path: str = None):
        self.db_path = db_path or SQLITE_DB_PATH
        self.manifest_path = manifest_path or MANIFEST_PATH

    def load_approved_bindings(self) -> List[SolderBinding]:
        if not os.path.exists(self.manifest_path):
            return []

        try:
            with open(self.manifest_path, "r") as f:
                manifest = json.load(f)
        except Exception:
            return []

        bindings = []
        for entry in manifest.get("bindings", []):
            if entry.get("validation_status") != "APPROVED":
                continue

            sql_text = ""
            sql_path = entry.get("sql_snippet_path", "")
            if sql_path and os.path.exists(sql_path):
                try:
                    with open(sql_path, "r") as f:
                        lines = f.readlines()
                    sql_lines = [l for l in lines if not l.startswith("--")]
                    sql_text = "".join(sql_lines).strip()
                except Exception:
                    pass

            bindings.append(SolderBinding(
                binding_key=entry.get("binding_key", ""),
                perspective=entry.get("perspective", ""),
                concept_anchor=entry.get("concept_anchor", ""),
                logic_type=entry.get("logic_type", "DIRECT"),
                sql_snippet_path=sql_path,
                sme_justification=entry.get("sme_justification", ""),
                validation_status=entry.get("validation_status", ""),
                sql_text=sql_text
            ))

        return bindings

    def get_elevation_edges(self, intent_name: str) -> List[ElevationEdge]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("""
                SELECT 
                    i.intent_name,
                    c.concept_name,
                    ic.intent_factor_weight,
                    ic.explanation,
                    p.perspective_name,
                    cf.table_name,
                    cf.field_name,
                    cf.context_hint
                FROM schema_intent_concepts ic
                JOIN schema_intents i ON ic.intent_id = i.intent_id
                JOIN schema_concepts c ON ic.concept_id = c.concept_id
                LEFT JOIN schema_intent_perspectives ip 
                    ON i.intent_id = ip.intent_id AND ip.intent_factor_weight = 1.0
                LEFT JOIN schema_perspectives p ON ip.perspective_id = p.perspective_id
                LEFT JOIN schema_concept_fields cf ON c.concept_id = cf.concept_id
                WHERE i.intent_name = ?
                ORDER BY ic.intent_factor_weight DESC
            """, (intent_name,)).fetchall()

            edges = []
            for r in rows:
                edges.append(ElevationEdge(
                    intent_name=r["intent_name"],
                    concept_name=r["concept_name"],
                    weight=r["intent_factor_weight"],
                    explanation=r["explanation"] or "",
                    perspective_name=r["perspective_name"] or "",
                    table_name=r["table_name"] or "",
                    field_name=r["field_name"] or "",
                    context_hint=r["context_hint"] or ""
                ))
            return edges
        finally:
            conn.close()

    def get_available_intents(self) -> List[Dict[str, str]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("""
                SELECT intent_name, intent_category, description, typical_question
                FROM schema_intents ORDER BY intent_category, intent_name
            """).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def find_binding_for_concept(self, concept: str, perspective: str = None) -> Optional[SolderBinding]:
        bindings = self.load_approved_bindings()
        concept_upper = concept.upper()

        has_perspective = perspective and perspective.strip()

        if has_perspective:
            exact_with_perspective = [
                b for b in bindings
                if b.concept_anchor == concept_upper
                and b.perspective.lower() == perspective.lower()
            ]
            if exact_with_perspective:
                return exact_with_perspective[-1]

        exact_any_perspective = [
            b for b in bindings
            if b.concept_anchor == concept_upper
        ]
        if exact_any_perspective:
            return exact_any_perspective[-1]

        partial_matches = [
            b for b in bindings
            if concept_upper in b.concept_anchor or b.concept_anchor in concept_upper
        ]
        if partial_matches:
            return partial_matches[-1]

        return None

    def parse_sql_ast(self, sql: str, dialect: str = "sqlite") -> Optional[exp.Expression]:
        try:
            parsed = sqlglot.parse(sql, read=dialect)
            if parsed and parsed[0]:
                return parsed[0]
        except Exception:
            pass
        return None

    def apply_alias_rename(self, ast: exp.Expression, old_alias: str, new_alias: str) -> Tuple[exp.Expression, str]:
        def rename_node(node):
            if isinstance(node, exp.Column) and node.table == old_alias:
                return exp.Column(
                    this=node.this,
                    table=exp.to_identifier(new_alias)
                )
            if isinstance(node, exp.TableAlias) and node.this and node.this.name == old_alias:
                return exp.TableAlias(this=exp.to_identifier(new_alias))
            if isinstance(node, exp.Subquery) and node.alias == old_alias:
                node.set("alias", exp.TableAlias(this=exp.to_identifier(new_alias)))
                return node
            return node

        transformed = ast.transform(rename_node)
        return transformed, f"Renamed alias '{old_alias}' -> '{new_alias}' (columns + table definitions)"

    def apply_table_qualification(self, ast: exp.Expression, table_name: str) -> Tuple[exp.Expression, str]:
        transformed = ast.transform(
            lambda node: exp.Column(
                this=node.this,
                table=exp.to_identifier(table_name)
            ) if isinstance(node, exp.Column) and not node.table else node
        )
        return transformed, f"Qualified unaliased columns with table '{table_name}'"

    def apply_where_injection(self, ast: exp.Expression, condition_sql: str) -> Tuple[exp.Expression, str]:
        try:
            condition = sqlglot.parse_one(f"SELECT * WHERE {condition_sql}", read="sqlite")
            where_clause = condition.find(exp.Where)
            if where_clause and isinstance(ast, exp.Select):
                existing_where = ast.find(exp.Where)
                if existing_where:
                    new_condition = exp.And(
                        this=existing_where.this,
                        expression=where_clause.this
                    )
                    ast.set("where", exp.Where(this=new_condition))
                    return ast, f"Injected AND condition: {condition_sql}"
                else:
                    ast.set("where", where_clause)
                    return ast, f"Added WHERE clause: {condition_sql}"
        except Exception:
            pass
        return ast, f"Warning: Could not inject condition: {condition_sql}"

    def transpile(self, sql: str, from_dialect: str = "sqlite", to_dialect: str = "tsql") -> str:
        try:
            result = sqlglot.transpile(sql, read=from_dialect, write=to_dialect)
            if result:
                return result[0]
        except Exception:
            pass
        return sql

    def solder(self, intent_name: str, target_concept: str = None,
               target_dialect: str = "sqlite",
               context_overrides: Dict[str, str] = None) -> SolderResult:

        elevation_edges = self.get_elevation_edges(intent_name)

        if not elevation_edges:
            return SolderResult(
                original_sql="",
                soldered_sql="-- No elevation edges found for intent: " + intent_name,
                dialect=target_dialect,
                binding_key="",
                perspective="",
                concept="",
                logic_type="",
                elevation_weight=0.0,
                warnings=[f"No elevation data found for intent '{intent_name}'"]
            )

        elevated = [e for e in elevation_edges if e.weight == 1.0]
        suppressed = [e for e in elevation_edges if e.weight == 0.0]

        if target_concept:
            target_edges = [e for e in elevated if e.concept_name.upper() == target_concept.upper()]
            if not target_edges:
                target_edges = [e for e in elevated if target_concept.upper() in e.concept_name.upper()]
            if target_edges:
                elevated = target_edges

        if not elevated:
            return SolderResult(
                original_sql="",
                soldered_sql=f"-- No ELEVATED concepts for intent '{intent_name}'",
                dialect=target_dialect,
                binding_key="",
                perspective="",
                concept="",
                logic_type="",
                elevation_weight=0.0,
                warnings=["No elevated concepts found"]
            )

        primary_edge = elevated[0]
        perspective = primary_edge.perspective_name
        concept = primary_edge.concept_name

        binding = self.find_binding_for_concept(concept, perspective)

        ast_operations = []
        warnings = []

        if binding and binding.sql_text:
            original_sql = binding.sql_text
            ast = self.parse_sql_ast(original_sql)

            if ast:
                if context_overrides:
                    for old_alias, new_alias in context_overrides.items():
                        ast, op = self.apply_alias_rename(ast, old_alias, new_alias)
                        ast_operations.append(op)

                if primary_edge.table_name:
                    ast, op = self.apply_table_qualification(ast, primary_edge.table_name)
                    ast_operations.append(op)

                ast_operations.append(f"Elevation: {concept} (weight={primary_edge.weight})")
                ast_operations.append(f"Perspective: {perspective}")
                ast_operations.append(f"Context hint: {primary_edge.context_hint}")

                if binding.logic_type == "SPATIAL_ALIAS":
                    ast_operations.append("Logic type: SPATIAL_ALIAS (coordinate/bin mapping - verify spatial accuracy)")
                    warnings.append("SPATIAL_ALIAS detected: SME-defined spatial logic requires manual coordinate verification")

                for s in suppressed:
                    ast_operations.append(f"Suppressed: {s.concept_name} (weight={s.weight}) - {s.explanation}")

                if target_dialect != "sqlite":
                    soldered_sql = self.transpile(ast.sql(dialect="sqlite"), "sqlite", target_dialect)
                    ast_operations.append(f"Transpiled: sqlite -> {target_dialect}")
                else:
                    soldered_sql = ast.sql(dialect="sqlite", pretty=True)
            else:
                soldered_sql = original_sql
                warnings.append("Could not parse SQL into AST; returning raw SQL")

            return SolderResult(
                original_sql=original_sql,
                soldered_sql=soldered_sql,
                dialect=target_dialect,
                binding_key=binding.binding_key,
                perspective=perspective,
                concept=concept,
                logic_type=binding.logic_type,
                elevation_weight=primary_edge.weight,
                ast_operations=ast_operations,
                warnings=warnings
            )

        base_sql = self._generate_base_query(primary_edge)
        ast_operations.append("Generated base query from elevation metadata (no approved snippet)")
        ast_operations.append(f"Elevation: {concept} (weight={primary_edge.weight})")
        ast_operations.append(f"Perspective: {perspective}")

        for s in suppressed:
            ast_operations.append(f"Suppressed: {s.concept_name} (weight={s.weight})")

        if target_dialect != "sqlite":
            soldered_sql = self.transpile(base_sql, "sqlite", target_dialect)
            ast_operations.append(f"Transpiled: sqlite -> {target_dialect}")
        else:
            soldered_sql = base_sql

        return SolderResult(
            original_sql=base_sql,
            soldered_sql=soldered_sql,
            dialect=target_dialect,
            binding_key="(auto-generated)",
            perspective=perspective,
            concept=concept,
            logic_type="DIRECT",
            elevation_weight=primary_edge.weight,
            ast_operations=ast_operations,
            warnings=["No approved SME snippet found; using auto-generated base query"]
        )

    def _generate_base_query(self, edge: ElevationEdge) -> str:
        if edge.table_name and edge.field_name:
            return f"SELECT {edge.field_name} FROM {edge.table_name}"
        return f"-- Cannot generate query: missing table/field metadata for {edge.concept_name}"

    def get_solder_report(self, intent_name: str, target_dialect: str = "sqlite") -> str:
        edges = self.get_elevation_edges(intent_name)

        if not edges:
            return f"No elevation data found for intent '{intent_name}'."

        elevated = [e for e in edges if e.weight == 1.0]
        suppressed = [e for e in edges if e.weight == 0.0]
        neutral = [e for e in edges if e.weight not in (0.0, 1.0)]

        report = f"## Solder Report: `{intent_name}`\n\n"

        if elevated:
            report += "### ELEVATED Concepts (weight = 1.0)\n"
            for e in elevated:
                binding = self.find_binding_for_concept(e.concept_name, e.perspective_name)
                status = f"Approved: `{binding.binding_key}`" if binding else "No approved snippet"
                report += f"- **{e.concept_name}** via `{e.perspective_name}`\n"
                report += f"  - Field: `{e.table_name}.{e.field_name}`\n"
                report += f"  - Hint: {e.context_hint}\n"
                report += f"  - SME Snippet: {status}\n"
                report += f"  - *{e.explanation}*\n\n"

        if suppressed:
            report += "### SUPPRESSED Concepts (weight = 0.0)\n"
            for s in suppressed:
                report += f"- ~~{s.concept_name}~~ - {s.explanation}\n"
            report += "\n"

        if neutral:
            report += "### NEUTRAL Concepts\n"
            for n in neutral:
                report += f"- {n.concept_name} (weight={n.weight}) - {n.explanation}\n"
            report += "\n"

        approved_bindings = self.load_approved_bindings()
        if approved_bindings:
            report += f"### Manifest: {len(approved_bindings)} approved snippets available\n"
            for b in approved_bindings:
                report += f"- `{b.binding_key}` ({b.perspective} / {b.concept_anchor}) - {b.logic_type}\n"

        return report
