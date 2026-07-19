"""Ledger binding map loader — binds the ontology layers to the SQL ledger.

Parses the committed, governed binding map
(``poc/ontop-ontology-poc/ledger_binding_map.json``) into an in-memory,
read-only store and exposes it to the app/semantic layer. The map ties:

  * SKOS concept URIs (``ontology/ledger_skos.jsonld``) -> physical ledger
    tables (the ``gl_*`` tables in the governed SQL graph), and
  * RDF (OWL) posting-event classes (``ontology/ledger_events.ttl``) ->
    ``gl_events.event_type`` values.

Design rules (Solder Pattern spirit — identical to skos_ledger.py):
- The committed JSON is the single source of truth; nothing here infers or
  fuzzy-matches bindings.
- FAIL CLOSED on any inconsistency (``LedgerBindingError``):
    * a bound concept URI absent from the SKOS scheme,
    * a bound table absent from the governed graph (graph_metadata.json),
    * a ledger (gl_*) table in the governed graph left unbound, or a table
      bound twice,
    * a bound event class not declared ``a owl:Class`` in ledger_events.ttl,
    * an event_type not carried as a skos:notation in the SKOS scheme,
      bound twice, or left unbound,
    * an event class whose bound event_type disagrees with the notation of
      its skos:closeMatch SKOS concept (cross-layer coherence).
- Read-only after load: the store hands out copies, never internal state.
"""

from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional

from skos_ledger import SkosConceptStore, get_ledger_concept_store

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_POC_DIR = os.path.join(_REPO_ROOT, "poc", "ontop-ontology-poc")
DEFAULT_BINDING_MAP_PATH = os.path.join(_POC_DIR, "ledger_binding_map.json")
DEFAULT_EVENTS_TTL_PATH = os.path.join(_POC_DIR, "ontology", "ledger_events.ttl")
DEFAULT_GRAPH_METADATA_PATH = os.path.join(
    _REPO_ROOT, "replit_integrations", "graph_metadata.json"
)

# The ledger tables are recognized in the governed graph by this prefix.
LEDGER_TABLE_PREFIX = "gl_"


class LedgerBindingError(ValueError):
    """Raised when the binding map is missing, unparseable, or inconsistent."""


@dataclass(frozen=True)
class ConceptTableBinding:
    """SKOS concept -> physical ledger table."""

    concept_uri: str
    pref_label: str
    table_name: str

    def to_dict(self) -> dict:
        return {
            "concept_uri": self.concept_uri,
            "pref_label": self.pref_label,
            "table_name": self.table_name,
        }


@dataclass(frozen=True)
class EntityTableBinding:
    """OWL entity class -> physical (non-ledger) table + key column."""

    entity_class_uri: str
    table_name: str
    key_column: str

    def to_dict(self) -> dict:
        return {
            "entity_class_uri": self.entity_class_uri,
            "table_name": self.table_name,
            "key_column": self.key_column,
        }


@dataclass(frozen=True)
class EventClassBinding:
    """RDF posting-event class -> gl_events.event_type."""

    event_class_uri: str
    event_type: str
    skos_concept_uri: str

    def to_dict(self) -> dict:
        return {
            "event_class_uri": self.event_class_uri,
            "event_type": self.event_type,
            "skos_concept_uri": self.skos_concept_uri,
        }


@dataclass(frozen=True)
class LedgerBindingStore:
    """Read-only, validated view of the committed binding map."""

    version: int
    namespace: str
    scheme_uri: str
    concept_bindings: tuple
    event_bindings: tuple
    entity_bindings: tuple = ()

    # -- lookups ---------------------------------------------------------
    def table_for_concept(self, concept_uri: str) -> Optional[str]:
        for b in self.concept_bindings:
            if b.concept_uri == concept_uri:
                return b.table_name
        return None

    def concept_for_table(self, table_name: str) -> Optional[str]:
        for b in self.concept_bindings:
            if b.table_name == table_name:
                return b.concept_uri
        return None

    def event_type_for_class(self, event_class_uri: str) -> Optional[str]:
        for b in self.event_bindings:
            if b.event_class_uri == event_class_uri:
                return b.event_type
        return None

    def class_for_event_type(self, event_type: str) -> Optional[str]:
        for b in self.event_bindings:
            if b.event_type == event_type:
                return b.event_class_uri
        return None

    def entity_binding(self, entity_class_uri: str) -> Optional["EntityTableBinding"]:
        for b in self.entity_bindings:
            if b.entity_class_uri == entity_class_uri:
                return b
        return None

    def table_for_entity(self, entity_class_uri: str) -> Optional[str]:
        b = self.entity_binding(entity_class_uri)
        return b.table_name if b else None

    def as_records(self) -> dict:
        """Plain-dict view for API / UI surfaces (copies, never internals)."""
        return {
            "version": self.version,
            "namespace": self.namespace,
            "scheme": self.scheme_uri,
            "concept_table_bindings": [b.to_dict() for b in self.concept_bindings],
            "event_class_bindings": [b.to_dict() for b in self.event_bindings],
            "entity_table_bindings": [b.to_dict() for b in self.entity_bindings],
        }


def _parse_ttl_blocks(path: str) -> Dict[str, str]:
    """Group a Turtle file into {local_name: block_text} — the same focused,
    no-rdflib parse the POC checkers use (column-0 ``:Name`` starts a block;
    indented lines continue it)."""
    with open(path, encoding="utf-8") as fh:
        raw_lines = fh.readlines()
    blocks: Dict[str, str] = {}
    current: Optional[str] = None
    buf: List[str] = []
    for raw in raw_lines:
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1] == ":":
            if current is not None:
                blocks[current] = "\n".join(buf)
            m = re.match(r":([A-Za-z_][A-Za-z0-9_]*)", line)
            current = m.group(1) if m else None
            buf = [line]
        elif line[:1].isspace() and current is not None:
            buf.append(line)
        else:
            if current is not None:
                blocks[current] = "\n".join(buf)
                current = None
                buf = []
    if current is not None:
        blocks[current] = "\n".join(buf)
    return blocks


def _graph_tables(graph_metadata_path: str) -> set:
    if not os.path.exists(graph_metadata_path):
        raise LedgerBindingError(
            f"governed graph metadata not found: {graph_metadata_path}"
        )
    with open(graph_metadata_path, encoding="utf-8") as fh:
        doc = json.load(fh)
    return {
        n["table_name"]
        for n in doc.get("nodes", [])
        if n.get("node_type") == "table"
    }


def load_ledger_bindings(
    binding_map_path: str = DEFAULT_BINDING_MAP_PATH,
    events_ttl_path: str = DEFAULT_EVENTS_TTL_PATH,
    graph_metadata_path: str = DEFAULT_GRAPH_METADATA_PATH,
    skos_store: Optional[SkosConceptStore] = None,
) -> LedgerBindingStore:
    """Parse and validate the binding map. Raises LedgerBindingError on defect."""
    if not os.path.exists(binding_map_path):
        raise LedgerBindingError(f"binding map not found: {binding_map_path}")
    try:
        with open(binding_map_path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except json.JSONDecodeError as e:
        raise LedgerBindingError(f"binding map is not valid JSON: {e}") from e

    concept_map = doc.get("concept_table_bindings")
    event_map = doc.get("event_class_bindings")
    if not isinstance(concept_map, dict) or not concept_map:
        raise LedgerBindingError("binding map has no concept_table_bindings")
    if not isinstance(event_map, dict) or not event_map:
        raise LedgerBindingError("binding map has no event_class_bindings")

    skos = skos_store if skos_store is not None else get_ledger_concept_store()
    scheme_uri = doc.get("scheme") or ""
    if scheme_uri != skos.scheme_uri:
        raise LedgerBindingError(
            f"binding map scheme {scheme_uri!r} != SKOS scheme {skos.scheme_uri!r}"
        )

    graph_tables = _graph_tables(graph_metadata_path)
    ledger_tables = {t for t in graph_tables if t.startswith(LEDGER_TABLE_PREFIX)}

    # ---- concept -> table bindings -------------------------------------
    concept_bindings: List[ConceptTableBinding] = []
    seen_tables: set = set()
    for uri, table in concept_map.items():
        concept = skos.get(uri)
        if concept is None:
            raise LedgerBindingError(
                f"bound concept {uri!r} is absent from the SKOS scheme"
            )
        if table not in graph_tables:
            raise LedgerBindingError(
                f"bound table {table!r} (for {uri}) is absent from the governed graph"
            )
        if table in seen_tables:
            raise LedgerBindingError(f"table {table!r} is bound more than once")
        seen_tables.add(table)
        concept_bindings.append(
            ConceptTableBinding(
                concept_uri=uri, pref_label=concept.pref_label, table_name=table
            )
        )
    unbound = ledger_tables - seen_tables
    if unbound:
        raise LedgerBindingError(
            f"ledger table(s) in the governed graph left unbound: {sorted(unbound)}"
        )
    extra = seen_tables - ledger_tables
    if extra:
        raise LedgerBindingError(
            f"bound table(s) are not ledger ({LEDGER_TABLE_PREFIX}*) tables: {sorted(extra)}"
        )

    # ---- event class -> event_type bindings ----------------------------
    if not os.path.exists(events_ttl_path):
        raise LedgerBindingError(f"event ontology not found: {events_ttl_path}")
    blocks = _parse_ttl_blocks(events_ttl_path)

    # ---- entity class -> physical table bindings ------------------------
    # (e.g. ledger:Job -> work_order keyed by wo_id). Entities ground on
    # NON-ledger tables of the governed graph, keyed by an explicit column.
    entity_map = doc.get("entity_table_bindings") or {}
    if not isinstance(entity_map, dict):
        raise LedgerBindingError("entity_table_bindings must be an object")
    entity_bindings: List[EntityTableBinding] = []
    for class_uri, spec in entity_map.items():
        local = class_uri.split(":", 1)[-1].split("#")[-1]
        body = blocks.get(local)
        if body is None or not re.search(r"\ba\s+owl:Class\b", body):
            raise LedgerBindingError(
                f"bound entity class {class_uri!r} is not declared "
                f"'a owl:Class' in {os.path.basename(events_ttl_path)}"
            )
        if not isinstance(spec, dict):
            raise LedgerBindingError(
                f"entity binding for {class_uri!r} must be an object "
                "with 'table' and 'key_column'"
            )
        table = spec.get("table")
        key_column = spec.get("key_column")
        if not table or not key_column:
            raise LedgerBindingError(
                f"entity binding for {class_uri!r} is missing table/key_column"
            )
        if table not in graph_tables:
            raise LedgerBindingError(
                f"bound entity table {table!r} (for {class_uri}) is absent "
                "from the governed graph"
            )
        if table.startswith(LEDGER_TABLE_PREFIX):
            raise LedgerBindingError(
                f"entity binding {class_uri!r} targets ledger table {table!r}; "
                "entities must ground on non-ledger tables"
            )
        entity_bindings.append(
            EntityTableBinding(
                entity_class_uri=class_uri,
                table_name=table,
                key_column=key_column,
            )
        )
    notations = {
        c.notation: c.uri for c in skos.all_concepts() if c.notation
    }

    event_bindings: List[EventClassBinding] = []
    seen_types: set = set()
    prefix = doc.get("namespace") or ""
    for class_uri, event_type in event_map.items():
        local = class_uri.split(":", 1)[-1].split("#")[-1]
        body = blocks.get(local)
        if body is None or not re.search(r"\ba\s+owl:Class\b", body):
            raise LedgerBindingError(
                f"bound event class {class_uri!r} is not declared "
                f"'a owl:Class' in {os.path.basename(events_ttl_path)}"
            )
        if event_type not in notations:
            raise LedgerBindingError(
                f"event_type {event_type!r} (for {class_uri}) is not a "
                "skos:notation in the SKOS scheme"
            )
        if event_type in seen_types:
            raise LedgerBindingError(
                f"event_type {event_type!r} is bound more than once"
            )
        seen_types.add(event_type)
        # Cross-layer coherence: the OWL class's skos:closeMatch concept must
        # carry exactly the bound event_type as its notation.
        close = re.findall(r"skos:closeMatch\s+:([A-Za-z_][A-Za-z0-9_]*)", body)
        if len(close) != 1:
            raise LedgerBindingError(
                f"event class {class_uri!r} must carry exactly one "
                f"skos:closeMatch (found {len(close)})"
            )
        skos_uri = f"ledger:{close[0]}"
        concept = skos.get(skos_uri)
        if concept is None:
            raise LedgerBindingError(
                f"event class {class_uri!r} closeMatch {skos_uri!r} is absent "
                "from the SKOS scheme"
            )
        if concept.notation != event_type:
            raise LedgerBindingError(
                f"event class {class_uri!r} is bound to {event_type!r} but its "
                f"closeMatch concept {skos_uri!r} carries notation "
                f"{concept.notation!r}"
            )
        event_bindings.append(
            EventClassBinding(
                event_class_uri=class_uri,
                event_type=event_type,
                skos_concept_uri=skos_uri,
            )
        )
    missing_types = set(notations) - seen_types
    if missing_types:
        raise LedgerBindingError(
            f"posting event_type(s) left unbound: {sorted(missing_types)}"
        )

    return LedgerBindingStore(
        version=int(doc.get("version") or 0),
        namespace=prefix,
        scheme_uri=scheme_uri,
        concept_bindings=tuple(
            sorted(concept_bindings, key=lambda b: b.concept_uri)
        ),
        event_bindings=tuple(sorted(event_bindings, key=lambda b: b.event_class_uri)),
        entity_bindings=tuple(
            sorted(entity_bindings, key=lambda b: b.entity_class_uri)
        ),
    )


# ---------------------------------------------------------------------------
# App-facing singleton accessor (loaded once, thread-safe).
# ---------------------------------------------------------------------------
_store_lock = threading.Lock()
_store: Optional[LedgerBindingStore] = None


def get_ledger_binding_store(reload: bool = False) -> LedgerBindingStore:
    """Read-only accessor for the validated ledger bindings.

    Loads once on first call and caches; fails closed by raising
    LedgerBindingError if the committed map is missing or inconsistent.
    """
    global _store
    with _store_lock:
        if _store is None or reload:
            _store = load_ledger_bindings()
        return _store


if __name__ == "__main__":
    s = load_ledger_bindings()
    print(f"scheme: {s.scheme_uri} (v{s.version})")
    print(f"concept->table bindings: {len(s.concept_bindings)}")
    for b in s.concept_bindings:
        print(f"  {b.concept_uri} -> {b.table_name}")
    print(f"event class->event_type bindings: {len(s.event_bindings)}")
    for b in s.event_bindings:
        print(f"  {b.event_class_uri} -> {b.event_type} (via {b.skos_concept_uri})")
    print(f"entity->table bindings: {len(s.entity_bindings)}")
    for b in s.entity_bindings:
        print(f"  {b.entity_class_uri} -> {b.table_name} (key {b.key_column})")
