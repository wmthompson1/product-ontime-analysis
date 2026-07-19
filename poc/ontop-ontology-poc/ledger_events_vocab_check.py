#!/usr/bin/env python3
"""Offline vocabulary gate for the ledger EVENT ontology (ledger_events.ttl).

Run directly: python poc/ontop-ontology-poc/ledger_events_vocab_check.py
Exits non-zero on any failure. File-vs-file only — no DB, no network, no JVM.

Proves:
  1. The Turtle file parses into subject blocks (same focused parser style as
     mapping_drift_check.py — no rdflib dependency).
  2. The four required event classes, the WorkOrder class, and the four flow
     properties are declared with the exact domains/ranges the task defines:
       MaterialIssueEvent    consumesMaterial      -> RawMaterialsInventory
       WIP-addition events   addsCostToWIP         -> WIPInventory
       JobCompletionEvent    producesFinishedGoods -> FinishedGoodsInventory
       every LedgerEvent     forJob                -> WorkOrder
  3. The class hierarchy is safe-annotation only: rdfs:subClassOf and
     skos:closeMatch — NO owl:equivalentClass anywhere in the file.
  4. Every skos:closeMatch target and every SKOS-concept range actually exists
     in the committed SKOS scheme (ontology/ledger_skos.jsonld) — shared
     ledger# namespace, no dangling links.
  5. No free-floating terms: every ``:Term`` referenced in the file is either
     declared here or a concept of the SKOS scheme.
  6. The file loads cleanly alongside the existing POC ontologies: every
     ``.ttl`` in ontology/ still parses with the same block parser and no
     other showcase file declares a conflicting term in the ledger namespace.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Dict, List, Set

POC_DIR = os.path.dirname(os.path.abspath(__file__))
ONTOLOGY_DIR = os.path.join(POC_DIR, "ontology")
EVENTS_TTL = os.path.join(ONTOLOGY_DIR, "ledger_events.ttl")
SKOS_JSONLD = os.path.join(ONTOLOGY_DIR, "ledger_skos.jsonld")

FAILURES: List[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def parse_blocks(path: str) -> Dict[str, str]:
    """Group a Turtle file into {subject: block-text} — the same focused,
    no-rdflib parse mapping_drift_check.py uses (column-0 ``:Name`` starts a
    block; indented lines continue it)."""
    with open(path, encoding="utf-8") as fh:
        raw_lines = fh.readlines()

    blocks: Dict[str, str] = {}
    current: str | None = None
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


def skos_local_names(path: str) -> Set[str]:
    """Local names of every concept/scheme in the committed SKOS JSON-LD."""
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    names: Set[str] = set()
    for node in doc.get("@graph", []):
        node_id = node.get("@id", "")
        if node_id.startswith("ledger:"):
            names.add(node_id.split(":", 1)[1])
    return names


def pred_object(body: str, predicate: str) -> Set[str]:
    """All ``:LocalName`` objects of a predicate inside one subject block."""
    return set(re.findall(rf"{re.escape(predicate)}\s+:([A-Za-z_][A-Za-z0-9_]*)", body))


def main() -> None:
    print("== Ledger event ontology vocabulary gate ==")

    for required in (EVENTS_TTL, SKOS_JSONLD):
        if not os.path.exists(required):
            print(f"FAIL: required file missing: {required}")
            sys.exit(1)

    blocks = parse_blocks(EVENTS_TTL)
    skos_names = skos_local_names(SKOS_JSONLD)
    check("SKOS scheme parses", len(skos_names) >= 13, f"got {len(skos_names)}")

    # ---- 1. Declared classes and properties ----
    def is_class(name: str) -> bool:
        return name in blocks and re.search(r"\ba\s+owl:Class\b", blocks[name]) is not None

    def is_obj_prop(name: str) -> bool:
        return name in blocks and re.search(r"\ba\s+owl:ObjectProperty\b", blocks[name]) is not None

    event_classes = ["MaterialIssueEvent", "LaborApplicationEvent",
                     "OverheadApplicationEvent", "JobCompletionEvent"]
    for cls in event_classes + ["LedgerEvent", "WIPAdditionEvent", "WorkOrder"]:
        check(f"class :{cls} declared", is_class(cls))
    for prop in ["consumesMaterial", "addsCostToWIP", "producesFinishedGoods", "forJob"]:
        check(f"object property :{prop} declared", is_obj_prop(prop))

    # ---- 2. Hierarchy: subclass chain + closeMatch into the SKOS scheme ----
    def subclass_of(name: str) -> Set[str]:
        return pred_object(blocks.get(name, ""), "rdfs:subClassOf")

    check("WIP-addition events under :WIPAdditionEvent",
          all(subclass_of(c) == {"WIPAdditionEvent"} for c in
              ("MaterialIssueEvent", "LaborApplicationEvent", "OverheadApplicationEvent")))
    check(":JobCompletionEvent directly under :LedgerEvent (not WIP-addition)",
          subclass_of("JobCompletionEvent") == {"LedgerEvent"})
    check(":WIPAdditionEvent under :LedgerEvent",
          subclass_of("WIPAdditionEvent") == {"LedgerEvent"})

    expected_close = {"LedgerEvent": "CostAccumulationEvent",
                      "MaterialIssueEvent": "MaterialIssued",
                      "LaborApplicationEvent": "LaborApplied",
                      "OverheadApplicationEvent": "OverheadApplied",
                      "JobCompletionEvent": "JobCompletion"}
    for cls, concept in expected_close.items():
        matches = pred_object(blocks.get(cls, ""), "skos:closeMatch")
        check(f":{cls} closeMatch :{concept}", matches == {concept})
        check(f"  ...and :{concept} exists in the SKOS scheme", concept in skos_names)

    # ---- 3. Flow-property domains/ranges tie events to SKOS concepts ----
    expected_dr = {
        "consumesMaterial":      ("MaterialIssueEvent", "RawMaterialsInventory"),
        "addsCostToWIP":         ("WIPAdditionEvent", "WIPInventory"),
        "producesFinishedGoods": ("JobCompletionEvent", "FinishedGoodsInventory"),
        "forJob":                ("LedgerEvent", "WorkOrder"),
    }
    for prop, (dom, rng) in expected_dr.items():
        body = blocks.get(prop, "")
        check(f":{prop} domain :{dom}", pred_object(body, "rdfs:domain") == {dom})
        check(f":{prop} range :{rng}", pred_object(body, "rdfs:range") == {rng})
    for concept in ("RawMaterialsInventory", "WIPInventory", "FinishedGoodsInventory"):
        check(f"range concept :{concept} exists in the SKOS scheme", concept in skos_names)

    # ---- 4. Safe-annotation convention: never owl:equivalentClass ----
    # (comment lines are stripped — the header may MENTION the banned term)
    with open(EVENTS_TTL, encoding="utf-8") as fh:
        full_text = fh.read()
    body_text = "\n".join(
        line for line in full_text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    check("no owl:equivalentClass anywhere",
          "owl:equivalentClass" not in body_text and "owl:equivalentProperty" not in body_text)

    # ---- 5. No free-floating terms beyond the declared set ----
    declared = set(blocks)
    referenced = {m.group(1) for m in
                  re.finditer(r"(?<![A-Za-z0-9_]):([A-Za-z_][A-Za-z0-9_]*)", body_text)}
    unmapped = referenced - declared - skos_names
    check("every referenced :Term is declared here or in the SKOS scheme",
          not unmapped, f"free-floating: {sorted(unmapped)}")

    # ---- 6. Loads cleanly alongside the existing POC ontologies ----
    sibling_ok = True
    ledger_conflicts: Set[str] = set()
    for fname in sorted(os.listdir(ONTOLOGY_DIR)):
        if not fname.endswith(".ttl") or fname == "ledger_events.ttl":
            continue
        path = os.path.join(ONTOLOGY_DIR, fname)
        try:
            sib_blocks = parse_blocks(path)
        except Exception as exc:  # noqa: BLE001
            sibling_ok = False
            print(f"    could not parse {fname}: {exc}")
            continue
        with open(path, encoding="utf-8") as fh:
            if "http://example.org/manufacturing/ledger#" in fh.read():
                ledger_conflicts |= (set(sib_blocks) & declared)
    check("all sibling .ttl ontologies still parse", sibling_ok)
    check("no other showcase re-declares a ledger-namespace term",
          not ledger_conflicts, f"conflicts: {sorted(ledger_conflicts)}")

    print()
    if FAILURES:
        print(f"RESULT: FAIL ({len(FAILURES)} failure(s)): {FAILURES}")
        sys.exit(1)
    print("RESULT: LEDGER EVENT VOCABULARY GATE PASSED")


if __name__ == "__main__":
    main()
