"""SKOS ledger concept loader — the ontology backbone for the job-costing ledger.

Parses the committed SKOS JSON-LD concept scheme
(``poc/ontop-ontology-poc/ontology/ledger_skos.jsonld``) into an in-memory,
read-only concept store and exposes it to the app/semantic layer.

Design rules (Solder Pattern spirit):
- The JSON-LD file is the single source of truth; nothing here generates terms.
- FAIL CLOSED on malformed input: missing labels/definitions, dangling
  broader/narrower references, duplicate URIs or prefLabels, asymmetric
  broader/narrower pairs, or concepts outside the declared scheme all raise
  ``SkosLoadError`` — a partial or silently-repaired scheme is never served.
- Read-only after load: the store hands out copies, never internal state.

Out of scope here (later ledger tasks): RDF event classes / flow properties
and binding concepts to physical tables.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Path to the committed JSON-LD, resolved relative to the repo root
# (this file lives in hf-space-inventory-sqlgen/).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_JSONLD_PATH = os.path.join(
    _REPO_ROOT, "poc", "ontop-ontology-poc", "ontology", "ledger_skos.jsonld"
)

SKOS_CONCEPT = "skos:Concept"
SKOS_SCHEME = "skos:ConceptScheme"


class SkosLoadError(ValueError):
    """Raised when the SKOS JSON-LD is missing, unparseable, or inconsistent."""


@dataclass(frozen=True)
class SkosConcept:
    """One immutable SKOS concept."""

    uri: str
    pref_label: str
    definition: str
    alt_labels: tuple = ()
    notation: Optional[str] = None
    broader: Optional[str] = None
    narrower: tuple = ()
    top_concept: bool = False

    def to_dict(self) -> dict:
        return {
            "uri": self.uri,
            "pref_label": self.pref_label,
            "definition": self.definition,
            "alt_labels": list(self.alt_labels),
            "notation": self.notation,
            "broader": self.broader,
            "narrower": list(self.narrower),
            "top_concept": self.top_concept,
        }


@dataclass
class SkosConceptStore:
    """Read-only in-memory store with lookup and hierarchy traversal."""

    scheme_uri: str
    scheme_label: str
    _by_uri: Dict[str, SkosConcept] = field(default_factory=dict)
    _by_label: Dict[str, str] = field(default_factory=dict)  # lower label -> uri
    _by_notation: Dict[str, str] = field(default_factory=dict)

    # -- lookups ---------------------------------------------------------
    def get(self, uri: str) -> Optional[SkosConcept]:
        return self._by_uri.get(uri)

    def get_by_label(self, label: str) -> Optional[SkosConcept]:
        """Case-insensitive lookup by prefLabel or altLabel."""
        uri = self._by_label.get((label or "").strip().lower())
        return self._by_uri.get(uri) if uri else None

    def get_by_notation(self, notation: str) -> Optional[SkosConcept]:
        uri = self._by_notation.get((notation or "").strip())
        return self._by_uri.get(uri) if uri else None

    def all_concepts(self) -> List[SkosConcept]:
        return sorted(self._by_uri.values(), key=lambda c: c.uri)

    def top_concepts(self) -> List[SkosConcept]:
        return [c for c in self.all_concepts() if c.top_concept]

    # -- hierarchy traversal ----------------------------------------------
    def narrower_of(self, uri: str) -> List[SkosConcept]:
        c = self._require(uri)
        return [self._require(n) for n in c.narrower]

    def broader_of(self, uri: str) -> Optional[SkosConcept]:
        c = self._require(uri)
        return self._require(c.broader) if c.broader else None

    def ancestors(self, uri: str) -> List[SkosConcept]:
        """Broader chain from the concept up to its top concept (exclusive of self)."""
        out: List[SkosConcept] = []
        cur = self._require(uri)
        seen = {uri}
        while cur.broader:
            if cur.broader in seen:
                raise SkosLoadError(f"broader cycle detected at {cur.broader}")
            cur = self._require(cur.broader)
            seen.add(cur.uri)
            out.append(cur)
        return out

    def descendants(self, uri: str) -> List[SkosConcept]:
        """All narrower concepts transitively (depth-first, exclusive of self)."""
        out: List[SkosConcept] = []
        stack = list(self._require(uri).narrower)
        seen = {uri}
        while stack:
            nxt = stack.pop(0)
            if nxt in seen:
                raise SkosLoadError(f"narrower cycle detected at {nxt}")
            seen.add(nxt)
            c = self._require(nxt)
            out.append(c)
            stack = list(c.narrower) + stack
        return out

    # -- semantic-layer accessor -----------------------------------------
    def as_records(self) -> List[dict]:
        """Plain-dict view of every concept (for UI / API surfaces)."""
        return [c.to_dict() for c in self.all_concepts()]

    def _require(self, uri: str) -> SkosConcept:
        c = self._by_uri.get(uri)
        if c is None:
            raise SkosLoadError(f"unknown concept URI: {uri}")
        return c


def _as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def load_ledger_concepts(jsonld_path: str = DEFAULT_JSONLD_PATH) -> SkosConceptStore:
    """Parse and validate the SKOS JSON-LD. Raises SkosLoadError on any defect."""
    if not os.path.exists(jsonld_path):
        raise SkosLoadError(f"SKOS JSON-LD not found: {jsonld_path}")
    try:
        with open(jsonld_path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except json.JSONDecodeError as e:
        raise SkosLoadError(f"SKOS JSON-LD is not valid JSON: {e}") from e

    graph = doc.get("@graph")
    if not isinstance(graph, list) or not graph:
        raise SkosLoadError("SKOS JSON-LD has no @graph list")

    schemes = [n for n in graph if n.get("@type") == SKOS_SCHEME]
    if len(schemes) != 1:
        raise SkosLoadError(f"expected exactly 1 skos:ConceptScheme, found {len(schemes)}")
    scheme = schemes[0]
    scheme_uri = scheme.get("@id") or ""
    scheme_label = scheme.get("prefLabel") or ""
    declared_tops = set(_as_list(scheme.get("hasTopConcept")))
    if not scheme_uri or not scheme_label or not declared_tops:
        raise SkosLoadError("concept scheme missing @id, prefLabel, or hasTopConcept")

    concepts: Dict[str, SkosConcept] = {}
    for node in graph:
        if node.get("@type") != SKOS_CONCEPT:
            continue
        uri = node.get("@id") or ""
        pref = (node.get("prefLabel") or "").strip()
        definition = (node.get("definition") or "").strip()
        if not uri or not pref or not definition:
            raise SkosLoadError(
                f"concept missing @id/prefLabel/definition: {uri or node!r}"
            )
        if uri in concepts:
            raise SkosLoadError(f"duplicate concept URI: {uri}")
        if node.get("inScheme") != scheme_uri:
            raise SkosLoadError(f"concept {uri} not inScheme {scheme_uri}")
        broader_vals = _as_list(node.get("broader"))
        if len(broader_vals) > 1:
            raise SkosLoadError(f"concept {uri} has multiple broader values")
        is_top = node.get("topConceptOf") == scheme_uri
        broader = broader_vals[0] if broader_vals else None
        if is_top and broader:
            raise SkosLoadError(f"concept {uri} is both a top concept and has broader")
        if not is_top and not broader:
            raise SkosLoadError(f"concept {uri} is neither a top concept nor has broader")
        concepts[uri] = SkosConcept(
            uri=uri,
            pref_label=pref,
            definition=definition,
            alt_labels=tuple(_as_list(node.get("altLabel"))),
            notation=node.get("notation"),
            broader=broader,
            narrower=tuple(_as_list(node.get("narrower"))),
            top_concept=is_top,
        )

    if not concepts:
        raise SkosLoadError("no skos:Concept nodes found")

    # Referential integrity + broader/narrower symmetry.
    actual_tops = {u for u, c in concepts.items() if c.top_concept}
    if actual_tops != declared_tops:
        raise SkosLoadError(
            f"hasTopConcept/topConceptOf mismatch: declared={sorted(declared_tops)} "
            f"actual={sorted(actual_tops)}"
        )
    for uri, c in concepts.items():
        if c.broader is not None:
            parent = concepts.get(c.broader)
            if parent is None:
                raise SkosLoadError(f"{uri} broader points at unknown {c.broader}")
            if uri not in parent.narrower:
                raise SkosLoadError(
                    f"asymmetric hierarchy: {uri} broader {c.broader}, "
                    f"but {c.broader} lacks the matching narrower"
                )
        for n in c.narrower:
            child = concepts.get(n)
            if child is None:
                raise SkosLoadError(f"{uri} narrower points at unknown {n}")
            if child.broader != uri:
                raise SkosLoadError(
                    f"asymmetric hierarchy: {uri} narrower {n}, "
                    f"but {n} broader is {child.broader!r}"
                )

    store = SkosConceptStore(scheme_uri=scheme_uri, scheme_label=scheme_label)
    by_label: Dict[str, str] = {}
    by_notation: Dict[str, str] = {}
    for uri, c in concepts.items():
        for lbl in (c.pref_label, *c.alt_labels):
            key = lbl.strip().lower()
            if key in by_label:
                raise SkosLoadError(
                    f"duplicate label {lbl!r} on {uri} and {by_label[key]}"
                )
            by_label[key] = uri
        if c.notation:
            if c.notation in by_notation:
                raise SkosLoadError(f"duplicate notation {c.notation!r}")
            by_notation[c.notation] = uri
    store._by_uri = concepts
    store._by_label = by_label
    store._by_notation = by_notation

    # Traversal sanity: every concept reaches a top concept without cycles.
    for uri in concepts:
        chain = store.ancestors(uri)
        top = chain[-1] if chain else concepts[uri]
        if not top.top_concept:
            raise SkosLoadError(f"{uri} does not chain up to a top concept")
    return store


# ---------------------------------------------------------------------------
# App-facing singleton accessor (loaded once, thread-safe).
# ---------------------------------------------------------------------------
_store_lock = threading.Lock()
_store: Optional[SkosConceptStore] = None


def get_ledger_concept_store(reload: bool = False) -> SkosConceptStore:
    """Read-only accessor for the loaded SKOS ledger concepts.

    Loads once on first call (or at startup) and caches; fails closed by
    raising SkosLoadError if the committed JSON-LD is missing or malformed.
    """
    global _store
    with _store_lock:
        if _store is None or reload:
            _store = load_ledger_concepts()
        return _store


if __name__ == "__main__":
    s = load_ledger_concepts()
    print(f"scheme: {s.scheme_label} ({s.scheme_uri})")
    print(f"concepts: {len(s.all_concepts())}, top: {len(s.top_concepts())}")
    for c in s.top_concepts():
        kids = ", ".join(k.pref_label for k in s.narrower_of(c.uri)) or "-"
        print(f"  {c.pref_label}: narrower = {kids}")
