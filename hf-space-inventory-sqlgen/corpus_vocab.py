"""Corpus Vocabulary SKOS loader — the governed corpus taxonomy scheme.

Parses the committed SKOS JSON-LD concept scheme
(``poc/ontop-ontology-poc/ontology/corpus_vocab_skos.jsonld``) into an
in-memory, read-only store and exposes it to the app/semantic layer.

Architectural rules (the corpus taxonomy direction, verbatim):
- **Collections group; hierarchy orders.** ``skos:Collection`` is the ONLY
  grouping mechanism (active vs terminal states, time-based terms, forbidden
  synonym governance). ``skos:broader``/``skos:narrower`` expresses ONLY
  lifecycle progression (earlier state -> later state), so every
  broader/narrower chain must be LINEAR (one narrower per concept, max).
- **Concepts are vocabulary, never entities.** The OWL layer is touched only
  via ``skos:closeMatch`` — the loader carries the links but never interprets
  them.
- **notation is reserved for stored statuses.** Any concept inside a
  collection labeled as time-based must NOT carry a notation; lifecycle chain
  members MUST carry one (it is the physical column value verbatim).
- **Forbidden synonyms are machine-readable.** Members of the forbidden
  synonym governance collection must each carry at least one
  ``skos:hiddenLabel`` — recognized for matching, never surfaced.

Design rules (Solder Pattern spirit, identical to skos_ledger.py):
- The JSON-LD file is the single source of truth; nothing here generates
  terms.
- FAIL CLOSED on malformed input via ``CorpusVocabError`` — a partial or
  silently-repaired scheme is never served.
- Read-only after load: the store hands out copies, never internal state.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_JSONLD_PATH = os.path.join(
    _REPO_ROOT, "poc", "ontop-ontology-poc", "ontology",
    "corpus_vocab_skos.jsonld",
)

SKOS_CONCEPT = "skos:Concept"
SKOS_SCHEME = "skos:ConceptScheme"
SKOS_COLLECTION = "skos:Collection"

# Collection URIs with special validation semantics (governance contracts).
TIME_BASED_COLLECTION = "corpus:TimeBasedTerms"
FORBIDDEN_SYNONYM_COLLECTION = "corpus:ForbiddenSynonymGovernance"

# The taxonomy's required structure: all four collections must exist.
REQUIRED_COLLECTIONS = (
    "corpus:ActiveWorkOrderStates",
    "corpus:TerminalWorkOrderStates",
    TIME_BASED_COLLECTION,
    FORBIDDEN_SYNONYM_COLLECTION,
)


class CorpusVocabError(ValueError):
    """Raised when the corpus vocabulary JSON-LD is missing or inconsistent."""


@dataclass(frozen=True)
class CorpusConcept:
    """One immutable corpus vocabulary concept."""

    uri: str
    pref_label: str
    definition: str
    scope_note: str = ""
    alt_labels: tuple = ()
    hidden_labels: tuple = ()
    notation: Optional[str] = None
    broader: Optional[str] = None
    narrower: tuple = ()
    close_match: tuple = ()
    top_concept: bool = False

    def to_dict(self) -> dict:
        return {
            "uri": self.uri,
            "pref_label": self.pref_label,
            "definition": self.definition,
            "scope_note": self.scope_note,
            "alt_labels": list(self.alt_labels),
            "hidden_labels": list(self.hidden_labels),
            "notation": self.notation,
            "broader": self.broader,
            "narrower": list(self.narrower),
            "close_match": list(self.close_match),
            "top_concept": self.top_concept,
        }


@dataclass(frozen=True)
class CorpusCollection:
    """One immutable SKOS collection (grouping only — no hierarchy)."""

    uri: str
    pref_label: str
    definition: str
    members: tuple = ()

    def to_dict(self) -> dict:
        return {
            "uri": self.uri,
            "pref_label": self.pref_label,
            "definition": self.definition,
            "members": list(self.members),
        }


@dataclass
class CorpusVocabStore:
    """Read-only in-memory store: concepts, collections, and lookups."""

    scheme_uri: str
    scheme_label: str
    _by_uri: Dict[str, CorpusConcept] = field(default_factory=dict)
    _by_label: Dict[str, str] = field(default_factory=dict)
    _by_notation: Dict[str, str] = field(default_factory=dict)
    _collections: Dict[str, CorpusCollection] = field(default_factory=dict)

    # -- concept lookups ---------------------------------------------------
    def get(self, uri: str) -> Optional[CorpusConcept]:
        return self._by_uri.get(uri)

    def get_by_label(self, label: str) -> Optional[CorpusConcept]:
        """Case-insensitive lookup by prefLabel, altLabel, or hiddenLabel."""
        uri = self._by_label.get((label or "").strip().lower())
        return self._by_uri.get(uri) if uri else None

    def get_by_notation(self, notation: str) -> Optional[CorpusConcept]:
        uri = self._by_notation.get((notation or "").strip())
        return self._by_uri.get(uri) if uri else None

    def all_concepts(self) -> List[CorpusConcept]:
        return sorted(self._by_uri.values(), key=lambda c: c.uri)

    def top_concepts(self) -> List[CorpusConcept]:
        return [c for c in self.all_concepts() if c.top_concept]

    # -- collections ---------------------------------------------------------
    def all_collections(self) -> List[CorpusCollection]:
        return sorted(self._collections.values(), key=lambda c: c.uri)

    def collection(self, uri: str) -> Optional[CorpusCollection]:
        return self._collections.get(uri)

    def collections_of(self, concept_uri: str) -> List[CorpusCollection]:
        return [c for c in self.all_collections() if concept_uri in c.members]

    # -- lifecycle progression ---------------------------------------------
    def progression_from(self, uri: str) -> List[CorpusConcept]:
        """The linear lifecycle chain starting at ``uri`` (inclusive)."""
        cur = self._require(uri)
        out = [cur]
        seen = {uri}
        while cur.narrower:
            nxt = cur.narrower[0]
            if nxt in seen:
                raise CorpusVocabError(f"progression cycle detected at {nxt}")
            seen.add(nxt)
            cur = self._require(nxt)
            out.append(cur)
        return out

    def forbidden_synonyms(self) -> Dict[str, str]:
        """hiddenLabel (lower) -> governed prefLabel, for every governed concept."""
        gov = self._collections.get(FORBIDDEN_SYNONYM_COLLECTION)
        out: Dict[str, str] = {}
        if gov is None:
            return out
        for m in gov.members:
            c = self._require(m)
            for h in c.hidden_labels:
                out[h.strip().lower()] = c.pref_label
        return out

    def as_records(self) -> List[dict]:
        return [c.to_dict() for c in self.all_concepts()]

    def _require(self, uri: str) -> CorpusConcept:
        c = self._by_uri.get(uri)
        if c is None:
            raise CorpusVocabError(f"unknown concept URI: {uri}")
        return c


def _as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def load_corpus_vocab(jsonld_path: str = DEFAULT_JSONLD_PATH) -> CorpusVocabStore:
    """Parse and validate the corpus vocabulary. Raises CorpusVocabError."""
    if not os.path.exists(jsonld_path):
        raise CorpusVocabError(f"corpus vocabulary JSON-LD not found: {jsonld_path}")
    try:
        with open(jsonld_path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except json.JSONDecodeError as e:
        raise CorpusVocabError(f"corpus vocabulary is not valid JSON: {e}") from e

    graph = doc.get("@graph")
    if not isinstance(graph, list) or not graph:
        raise CorpusVocabError("corpus vocabulary has no @graph list")

    schemes = [n for n in graph if n.get("@type") == SKOS_SCHEME]
    if len(schemes) != 1:
        raise CorpusVocabError(
            f"expected exactly 1 skos:ConceptScheme, found {len(schemes)}"
        )
    scheme = schemes[0]
    scheme_uri = scheme.get("@id") or ""
    scheme_label = scheme.get("prefLabel") or ""
    declared_tops = set(_as_list(scheme.get("hasTopConcept")))
    if not scheme_uri or not scheme_label or not declared_tops:
        raise CorpusVocabError("scheme missing @id, prefLabel, or hasTopConcept")

    # ---- concepts ----------------------------------------------------------
    concepts: Dict[str, CorpusConcept] = {}
    for node in graph:
        if node.get("@type") != SKOS_CONCEPT:
            continue
        uri = node.get("@id") or ""
        pref = (node.get("prefLabel") or "").strip()
        definition = (node.get("definition") or "").strip()
        if not uri or not pref or not definition:
            raise CorpusVocabError(
                f"concept missing @id/prefLabel/definition: {uri or node!r}"
            )
        if uri in concepts:
            raise CorpusVocabError(f"duplicate concept URI: {uri}")
        if node.get("inScheme") != scheme_uri:
            raise CorpusVocabError(f"concept {uri} not inScheme {scheme_uri}")
        broader_vals = _as_list(node.get("broader"))
        if len(broader_vals) > 1:
            raise CorpusVocabError(f"concept {uri} has multiple broader values")
        narrower_vals = _as_list(node.get("narrower"))
        # broader/narrower is lifecycle PROGRESSION only: linear chain.
        if len(narrower_vals) > 1:
            raise CorpusVocabError(
                f"concept {uri} has {len(narrower_vals)} narrower values — "
                "broader/narrower expresses lifecycle progression only, so "
                "chains must be linear (use a skos:Collection to group)"
            )
        is_top = node.get("topConceptOf") == scheme_uri
        broader = broader_vals[0] if broader_vals else None
        if is_top and broader:
            raise CorpusVocabError(f"{uri} is both a top concept and has broader")
        if not is_top and not broader:
            raise CorpusVocabError(f"{uri} is neither a top concept nor has broader")
        concepts[uri] = CorpusConcept(
            uri=uri,
            pref_label=pref,
            definition=definition,
            scope_note=(node.get("scopeNote") or "").strip(),
            alt_labels=tuple(_as_list(node.get("altLabel"))),
            hidden_labels=tuple(_as_list(node.get("hiddenLabel"))),
            notation=node.get("notation"),
            broader=broader,
            narrower=tuple(narrower_vals),
            close_match=tuple(_as_list(node.get("closeMatch"))),
            top_concept=is_top,
        )

    if not concepts:
        raise CorpusVocabError("no skos:Concept nodes found")

    actual_tops = {u for u, c in concepts.items() if c.top_concept}
    if actual_tops != declared_tops:
        raise CorpusVocabError(
            f"hasTopConcept/topConceptOf mismatch: declared={sorted(declared_tops)} "
            f"actual={sorted(actual_tops)}"
        )
    for uri, c in concepts.items():
        if c.broader is not None:
            parent = concepts.get(c.broader)
            if parent is None:
                raise CorpusVocabError(f"{uri} broader points at unknown {c.broader}")
            if uri not in parent.narrower:
                raise CorpusVocabError(
                    f"asymmetric hierarchy: {uri} broader {c.broader}, "
                    f"but {c.broader} lacks the matching narrower"
                )
        for n in c.narrower:
            child = concepts.get(n)
            if child is None:
                raise CorpusVocabError(f"{uri} narrower points at unknown {n}")
            if child.broader != uri:
                raise CorpusVocabError(
                    f"asymmetric hierarchy: {uri} narrower {n}, "
                    f"but {n} broader is {child.broader!r}"
                )
        # Progression rule: every chained (non-top or chained-from) concept
        # in a broader/narrower chain must carry a notation — the chain IS the
        # stored status lifecycle, nothing else may use it.
        if (c.broader or c.narrower) and not c.notation:
            raise CorpusVocabError(
                f"{uri} participates in a broader/narrower chain but has no "
                "notation — progression chains are reserved for stored "
                "status lifecycles (notation = the physical column value)"
            )
        # And the inverse: notation appears ONLY on lifecycle-chain members
        # (stored statuses). Any other concept carrying one is fail-closed.
        if c.notation and not (c.broader or c.narrower):
            raise CorpusVocabError(
                f"{uri} carries notation {c.notation!r} but is not part of a "
                "lifecycle progression chain — notation is reserved for "
                "stored status values"
            )

    # ---- collections -------------------------------------------------------
    collections: Dict[str, CorpusCollection] = {}
    for node in graph:
        if node.get("@type") != SKOS_COLLECTION:
            continue
        uri = node.get("@id") or ""
        pref = (node.get("prefLabel") or "").strip()
        definition = (node.get("definition") or "").strip()
        members = tuple(_as_list(node.get("member")))
        if not uri or not pref or not definition or not members:
            raise CorpusVocabError(
                f"collection missing @id/prefLabel/definition/member: {uri or node!r}"
            )
        if uri in collections or uri in concepts:
            raise CorpusVocabError(f"duplicate collection URI: {uri}")
        for m in members:
            if m not in concepts:
                raise CorpusVocabError(
                    f"collection {uri} member {m} is not a declared concept"
                )
        collections[uri] = CorpusCollection(
            uri=uri, pref_label=pref, definition=definition, members=members
        )

    # Required taxonomy structure: all four collections must be present.
    missing = [u for u in REQUIRED_COLLECTIONS if u not in collections]
    if missing:
        raise CorpusVocabError(
            f"required collection(s) missing from scheme: {missing}"
        )

    # Governance contracts on the two special collections.
    for m in collections[TIME_BASED_COLLECTION].members:
        if concepts[m].notation:
            raise CorpusVocabError(
                f"time-based term {m} carries a notation — notation is "
                "reserved for stored statuses, and time-based terms are "
                "derived, never stored"
            )
    for m in collections[FORBIDDEN_SYNONYM_COLLECTION].members:
        if not concepts[m].hidden_labels:
            raise CorpusVocabError(
                f"forbidden-synonym governance member {m} carries no "
                "skos:hiddenLabel — nothing is governed"
            )

    # ---- label / notation indices (uniqueness across ALL label kinds) -----
    store = CorpusVocabStore(scheme_uri=scheme_uri, scheme_label=scheme_label)
    by_label: Dict[str, str] = {}
    by_notation: Dict[str, str] = {}
    for uri, c in concepts.items():
        for lbl in (c.pref_label, *c.alt_labels, *c.hidden_labels):
            key = lbl.strip().lower()
            if key in by_label:
                raise CorpusVocabError(
                    f"duplicate label {lbl!r} on {uri} and {by_label[key]}"
                )
            by_label[key] = uri
        if c.notation:
            if c.notation in by_notation:
                raise CorpusVocabError(f"duplicate notation {c.notation!r}")
            by_notation[c.notation] = uri
    store._by_uri = concepts
    store._by_label = by_label
    store._by_notation = by_notation
    store._collections = collections

    # Traversal sanity: every concept chains up to a top concept, acyclically.
    for uri in concepts:
        cur = concepts[uri]
        seen = {uri}
        while cur.broader:
            if cur.broader in seen:
                raise CorpusVocabError(f"broader cycle detected at {cur.broader}")
            seen.add(cur.broader)
            cur = concepts[cur.broader]
        if not cur.top_concept:
            raise CorpusVocabError(f"{uri} does not chain up to a top concept")
    return store


# ---------------------------------------------------------------------------
# App-facing singleton accessor (loaded once, thread-safe).
# ---------------------------------------------------------------------------
_store_lock = threading.Lock()
_store: Optional[CorpusVocabStore] = None


def get_corpus_vocab_store(reload: bool = False) -> CorpusVocabStore:
    """Read-only accessor for the loaded corpus vocabulary.

    Loads once on first call and caches; fails closed by raising
    CorpusVocabError if the committed JSON-LD is missing or malformed.
    """
    global _store
    with _store_lock:
        if _store is None or reload:
            _store = load_corpus_vocab()
        return _store


if __name__ == "__main__":
    s = load_corpus_vocab()
    print(f"scheme: {s.scheme_label} ({s.scheme_uri})")
    print(f"concepts: {len(s.all_concepts())}, top: {len(s.top_concepts())}, "
          f"collections: {len(s.all_collections())}")
    for col in s.all_collections():
        names = ", ".join(s.get(m).pref_label for m in col.members)
        print(f"  [{col.pref_label}] {names}")
    chain = " -> ".join(c.pref_label for c in s.progression_from("corpus:UnreleasedState"))
    print(f"  lifecycle: {chain}")
    fs = s.forbidden_synonyms()
    print(f"  forbidden synonyms: {fs}")
