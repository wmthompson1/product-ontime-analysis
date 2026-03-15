"""
ArangoDB Graph Sync
====================
Synchronizes the SQLite semantic layer (intents, perspectives, concepts,
elevation weights, binding keys) into ArangoDB as a named graph.

Graph structure:
  Vertex collections: intents, perspectives, concepts, bindings
  Edge collections:   operates_within, elevates, uses_definition, bound_to

Graph name: semantic_graph

Traversal pattern:
  (:Intent) -[:OPERATES_WITHIN]-> (:Perspective)
  (:Intent) -[:ELEVATES {weight}]-> (:Concept)
  (:Perspective) -[:USES_DEFINITION]-> (:Concept)
  (:Intent) -[:BOUND_TO]-> (:Binding)
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "app_schema", "manufacturing.db")
MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "app_schema", "ground_truth", "reviewer_manifest.json")

GRAPH_NAME = "semantic_graph"

VERTEX_COLLECTIONS = ["intents", "perspectives", "concepts", "bindings"]
EDGE_COLLECTIONS = ["operates_within", "elevates", "uses_definition", "bound_to"]

EDGE_DEFINITIONS = [
    {
        "edge_collection": "operates_within",
        "from_vertex_collections": ["intents"],
        "to_vertex_collections": ["perspectives"],
    },
    {
        "edge_collection": "elevates",
        "from_vertex_collections": ["intents"],
        "to_vertex_collections": ["concepts"],
    },
    {
        "edge_collection": "uses_definition",
        "from_vertex_collections": ["perspectives"],
        "to_vertex_collections": ["concepts"],
    },
    {
        "edge_collection": "bound_to",
        "from_vertex_collections": ["intents"],
        "to_vertex_collections": ["bindings"],
    },
]


@dataclass
class SyncReport:
    timestamp: str = ""
    vertices_synced: Dict[str, int] = field(default_factory=dict)
    vertices_new: Dict[str, int] = field(default_factory=dict)
    vertices_updated: Dict[str, int] = field(default_factory=dict)
    edges_synced: Dict[str, int] = field(default_factory=dict)
    edges_new: Dict[str, int] = field(default_factory=dict)
    edges_updated: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    dry_run: bool = False

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def total_vertices(self) -> int:
        return sum(self.vertices_synced.values())

    @property
    def total_edges(self) -> int:
        return sum(self.edges_synced.values())

    def summary(self) -> str:
        mode = "DRY RUN" if self.dry_run else "LIVE SYNC"
        lines = [f"Graph Sync Report ({self.timestamp})"]
        lines.append(f"Mode: {mode}")
        lines.append(f"Status: {'SUCCESS' if self.success else 'FAILED'}")
        lines.append("")
        lines.append(f"Vertices (total synced: {self.total_vertices}):")
        for coll in self.vertices_synced:
            synced = self.vertices_synced.get(coll, 0)
            new = self.vertices_new.get(coll, 0)
            updated = self.vertices_updated.get(coll, 0)
            if self.dry_run:
                lines.append(f"  {coll}: {synced} to sync")
            else:
                lines.append(f"  {coll}: {synced} synced ({new} new, {updated} updated)")
        lines.append("")
        lines.append(f"Edges (total synced: {self.total_edges}):")
        for coll in self.edges_synced:
            synced = self.edges_synced.get(coll, 0)
            new = self.edges_new.get(coll, 0)
            updated = self.edges_updated.get(coll, 0)
            if self.dry_run:
                lines.append(f"  {coll}: {synced} to sync")
            else:
                lines.append(f"  {coll}: {synced} synced ({new} new, {updated} updated)")
        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            for w in self.warnings:
                lines.append(f"  - {w}")
        if self.errors:
            lines.append("")
            lines.append("Errors:")
            for e in self.errors:
                lines.append(f"  - {e}")
        return "\n".join(lines)


def get_arango_client():
    from arango import ArangoClient

    raw_host = (
        os.environ.get("ARANGO_HOST")
        or os.environ.get("DATABASE_HOST", "http://localhost:8529")
    ).strip()
    if "arangodb.cloud" in raw_host and ":" not in raw_host.split("//", 1)[-1]:
        raw_host = f"{raw_host}:8529"
    client = ArangoClient(hosts=raw_host)
    return client


def get_arango_db(client):
    db_name = os.environ.get("ARANGO_DB")
    username = os.environ.get("ARANGO_USER", "root")
    password = os.environ.get("ARANGO_ROOT_PASSWORD", "")

    sys_db = client.db("_system", username=username, password=password)
    if not sys_db.has_database(db_name):
        sys_db.create_database(db_name)

    db = client.db(db_name, username=username, password=password)
    return db


def ensure_graph(db) -> None:
    if db.has_graph(GRAPH_NAME):
        graph = db.graph(GRAPH_NAME)
        existing_edge_defs = {ed["edge_collection"] for ed in graph.edge_definitions()}
        for ed in EDGE_DEFINITIONS:
            if ed["edge_collection"] not in existing_edge_defs:
                graph.create_edge_definition(**ed)
        return

    db.create_graph(
        GRAPH_NAME,
        edge_definitions=EDGE_DEFINITIONS,
    )


def load_sqlite_data(db_path: str = SQLITE_DB_PATH) -> Dict[str, Any]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    intents = [dict(r) for r in conn.execute("""
        SELECT intent_id, intent_name, intent_category, description,
               typical_question, primary_binding_key
        FROM schema_intents ORDER BY intent_name
    """).fetchall()]

    perspectives = [dict(r) for r in conn.execute("""
        SELECT perspective_id, perspective_name, description,
               stakeholder_role, priority_focus
        FROM schema_perspectives ORDER BY perspective_name
    """).fetchall()]

    concepts = [dict(r) for r in conn.execute("""
        SELECT concept_id, concept_name, concept_type, description, domain
        FROM schema_concepts ORDER BY concept_name
    """).fetchall()]

    intent_perspectives = [dict(r) for r in conn.execute("""
        SELECT si.intent_name, sp.perspective_name, sip.intent_factor_weight, sip.explanation
        FROM schema_intent_perspectives sip
        JOIN schema_intents si ON sip.intent_id = si.intent_id
        JOIN schema_perspectives sp ON sip.perspective_id = sp.perspective_id
    """).fetchall()]

    intent_concepts = [dict(r) for r in conn.execute("""
        SELECT si.intent_name, sc.concept_name, sic.intent_factor_weight, sic.explanation
        FROM schema_intent_concepts sic
        JOIN schema_intents si ON sic.intent_id = si.intent_id
        JOIN schema_concepts sc ON sic.concept_id = sc.concept_id
    """).fetchall()]

    perspective_concepts = [dict(r) for r in conn.execute("""
        SELECT sp.perspective_name, sc.concept_name,
               spc.relationship_type, spc.priority_weight
        FROM schema_perspective_concepts spc
        JOIN schema_perspectives sp ON spc.perspective_id = sp.perspective_id
        JOIN schema_concepts sc ON spc.concept_id = sc.concept_id
    """).fetchall()]

    conn.close()

    return {
        "intents": intents,
        "perspectives": perspectives,
        "concepts": concepts,
        "intent_perspectives": intent_perspectives,
        "intent_concepts": intent_concepts,
        "perspective_concepts": perspective_concepts,
    }


def load_manifest(manifest_path: str = MANIFEST_PATH) -> Dict[str, Any]:
    if not os.path.exists(manifest_path):
        return {}
    with open(manifest_path, "r") as f:
        return json.load(f)


def _upsert_vertex(collection, key: str, doc: Dict[str, Any]) -> bool:
    doc["_key"] = key
    if collection.has(key):
        collection.update(doc)
        return False
    else:
        collection.insert(doc)
        return True


def _upsert_edge(collection, from_id: str, to_id: str, key: str, doc: Dict[str, Any]) -> bool:
    doc["_key"] = key
    doc["_from"] = from_id
    doc["_to"] = to_id
    if collection.has(key):
        collection.update(doc)
        return False
    else:
        collection.insert(doc)
        return True


def sync_graph(db_path: str = SQLITE_DB_PATH,
               manifest_path: str = MANIFEST_PATH,
               dry_run: bool = False) -> SyncReport:
    report = SyncReport(timestamp=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))

    try:
        data = load_sqlite_data(db_path)
        manifest = load_manifest(manifest_path)
    except Exception as e:
        report.errors.append(f"Failed to load source data: {e}")
        return report

    if dry_run:
        report.dry_run = True
        report.vertices_synced = {
            "intents": len(data["intents"]),
            "perspectives": len(data["perspectives"]),
            "concepts": len(data["concepts"]),
            "bindings": len(manifest.get("approved_snippets", {})),
        }
        report.edges_synced = {
            "operates_within": len(data["intent_perspectives"]),
            "elevates": len(data["intent_concepts"]),
            "uses_definition": len(data["perspective_concepts"]),
            "bound_to": sum(1 for i in data["intents"] if i.get("primary_binding_key")),
        }
        report.warnings.append("DRY RUN — no changes written to ArangoDB")
        return report

    try:
        client = get_arango_client()
        db = get_arango_db(client)
        ensure_graph(db)
    except Exception as e:
        report.errors.append(f"ArangoDB connection failed: {e}")
        return report

    graph = db.graph(GRAPH_NAME)

    v_synced = {"intents": 0, "perspectives": 0, "concepts": 0, "bindings": 0}
    v_new = {"intents": 0, "perspectives": 0, "concepts": 0, "bindings": 0}
    v_updated = {"intents": 0, "perspectives": 0, "concepts": 0, "bindings": 0}

    intent_coll = graph.vertex_collection("intents")
    for intent in data["intents"]:
        key = intent["intent_name"]
        doc = {
            "intent_name": intent["intent_name"],
            "intent_category": intent["intent_category"],
            "description": intent.get("description", ""),
            "typical_question": intent.get("typical_question", ""),
            "primary_binding_key": intent.get("primary_binding_key", ""),
            "synced_at": report.timestamp,
        }
        try:
            is_new = _upsert_vertex(intent_coll, key, doc)
            v_synced["intents"] += 1
            if is_new:
                v_new["intents"] += 1
            else:
                v_updated["intents"] += 1
        except Exception as e:
            report.warnings.append(f"Intent '{key}': {e}")

    persp_coll = graph.vertex_collection("perspectives")
    for persp in data["perspectives"]:
        key = persp["perspective_name"]
        doc = {
            "perspective_name": persp["perspective_name"],
            "description": persp.get("description", ""),
            "stakeholder_role": persp.get("stakeholder_role", ""),
            "priority_focus": persp.get("priority_focus", ""),
            "synced_at": report.timestamp,
        }
        try:
            is_new = _upsert_vertex(persp_coll, key, doc)
            v_synced["perspectives"] += 1
            if is_new:
                v_new["perspectives"] += 1
            else:
                v_updated["perspectives"] += 1
        except Exception as e:
            report.warnings.append(f"Perspective '{key}': {e}")

    concept_coll = graph.vertex_collection("concepts")
    for concept in data["concepts"]:
        key = concept["concept_name"]
        doc = {
            "concept_name": concept["concept_name"],
            "concept_type": concept.get("concept_type", ""),
            "description": concept.get("description", ""),
            "domain": concept.get("domain", ""),
            "synced_at": report.timestamp,
        }
        try:
            is_new = _upsert_vertex(concept_coll, key, doc)
            v_synced["concepts"] += 1
            if is_new:
                v_new["concepts"] += 1
            else:
                v_updated["concepts"] += 1
        except Exception as e:
            report.warnings.append(f"Concept '{key}': {e}")

    bindings_coll = graph.vertex_collection("bindings")
    approved = manifest.get("approved_snippets", {})
    for bk, entry in approved.items():
        doc = {
            "binding_key": bk,
            "concept_anchor": entry.get("concept_anchor", ""),
            "perspective": entry.get("perspective", ""),
            "category": entry.get("category", ""),
            "logic_type": entry.get("logic_type", ""),
            "file_path": entry.get("file_path", ""),
            "sme_justification": entry.get("sme_justification", ""),
            "validation_status": entry.get("validation_status", ""),
            "approved_by": entry.get("approved_by", ""),
            "synced_at": report.timestamp,
        }
        try:
            is_new = _upsert_vertex(bindings_coll, bk, doc)
            v_synced["bindings"] += 1
            if is_new:
                v_new["bindings"] += 1
            else:
                v_updated["bindings"] += 1
        except Exception as e:
            report.warnings.append(f"Binding '{bk}': {e}")

    report.vertices_synced = v_synced
    report.vertices_new = v_new
    report.vertices_updated = v_updated

    e_synced = {"operates_within": 0, "elevates": 0, "uses_definition": 0, "bound_to": 0}
    e_new = {"operates_within": 0, "elevates": 0, "uses_definition": 0, "bound_to": 0}
    e_updated = {"operates_within": 0, "elevates": 0, "uses_definition": 0, "bound_to": 0}

    ow_coll = graph.edge_collection("operates_within")
    for ip in data["intent_perspectives"]:
        from_id = f"intents/{ip['intent_name']}"
        to_id = f"perspectives/{ip['perspective_name']}"
        key = f"{ip['intent_name']}__{ip['perspective_name']}"
        doc = {
            "weight": ip.get("intent_factor_weight", 1),
            "explanation": ip.get("explanation", ""),
            "synced_at": report.timestamp,
        }
        try:
            is_new = _upsert_edge(ow_coll, from_id, to_id, key, doc)
            e_synced["operates_within"] += 1
            if is_new:
                e_new["operates_within"] += 1
            else:
                e_updated["operates_within"] += 1
        except Exception as e:
            report.warnings.append(f"operates_within '{key}': {e}")

    el_coll = graph.edge_collection("elevates")
    for ic in data["intent_concepts"]:
        from_id = f"intents/{ic['intent_name']}"
        to_id = f"concepts/{ic['concept_name']}"
        key = f"{ic['intent_name']}__{ic['concept_name']}"
        doc = {
            "weight": ic.get("intent_factor_weight", 0),
            "explanation": ic.get("explanation", ""),
            "relationship": "ELEVATES" if ic.get("intent_factor_weight", 0) >= 1 else "NEUTRAL" if ic.get("intent_factor_weight", 0) == 0 else "SUPPRESSES",
            "synced_at": report.timestamp,
        }
        try:
            is_new = _upsert_edge(el_coll, from_id, to_id, key, doc)
            e_synced["elevates"] += 1
            if is_new:
                e_new["elevates"] += 1
            else:
                e_updated["elevates"] += 1
        except Exception as e:
            report.warnings.append(f"elevates '{key}': {e}")

    ud_coll = graph.edge_collection("uses_definition")
    for pc in data["perspective_concepts"]:
        from_id = f"perspectives/{pc['perspective_name']}"
        to_id = f"concepts/{pc['concept_name']}"
        key = f"{pc['perspective_name']}__{pc['concept_name']}"
        doc = {
            "relationship_type": pc.get("relationship_type", "USES_DEFINITION"),
            "priority_weight": pc.get("priority_weight", 1),
            "synced_at": report.timestamp,
        }
        try:
            is_new = _upsert_edge(ud_coll, from_id, to_id, key, doc)
            e_synced["uses_definition"] += 1
            if is_new:
                e_new["uses_definition"] += 1
            else:
                e_updated["uses_definition"] += 1
        except Exception as e:
            report.warnings.append(f"uses_definition '{key}': {e}")

    bt_coll = graph.edge_collection("bound_to")
    for intent in data["intents"]:
        bk = intent.get("primary_binding_key")
        if bk and bk in approved:
            from_id = f"intents/{intent['intent_name']}"
            to_id = f"bindings/{bk}"
            key = f"{intent['intent_name']}__{bk}"
            doc = {
                "relationship": "BOUND_TO",
                "synced_at": report.timestamp,
            }
            try:
                is_new = _upsert_edge(bt_coll, from_id, to_id, key, doc)
                e_synced["bound_to"] += 1
                if is_new:
                    e_new["bound_to"] += 1
                else:
                    e_updated["bound_to"] += 1
            except Exception as e:
                report.warnings.append(f"bound_to '{key}': {e}")

    report.edges_synced = e_synced
    report.edges_new = e_new
    report.edges_updated = e_updated
    return report


if __name__ == "__main__":
    import sys

    dry = "--dry-run" in sys.argv

    print("=" * 60)
    print("ArangoDB GRAPH SYNC")
    print("=" * 60)

    if dry:
        print("MODE: DRY RUN (no changes will be written)\n")
    else:
        print("MODE: LIVE SYNC\n")

    report = sync_graph(dry_run=dry)
    print(report.summary())

    sys.exit(0 if report.success else 1)
