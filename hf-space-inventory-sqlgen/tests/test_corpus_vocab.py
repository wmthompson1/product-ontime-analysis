"""Gate-style test for the corpus vocabulary SKOS loader (corpus_vocab.py).

Run directly: python hf-space-inventory-sqlgen/tests/test_corpus_vocab.py
Exits non-zero on any failure.

Proves the five corpus-taxonomy architectural rules:
1. Collections group (active/terminal/time-based/forbidden-synonyms).
2. Concepts carry the terms (labels, definitions, scope notes).
3. broader/narrower is lifecycle progression ONLY (linear chains, stored
   statuses with notation).
4. SKOS touches OWL only via skos:closeMatch.
5. Dedicated corpus namespace, separate from ledger# and the OWL layer.
Plus fail-closed behavior on every governance violation.
"""

import copy
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from corpus_vocab import (  # noqa: E402
    DEFAULT_JSONLD_PATH,
    FORBIDDEN_SYNONYM_COLLECTION,
    TIME_BASED_COLLECTION,
    CorpusVocabError,
    get_corpus_vocab_store,
    load_corpus_vocab,
)

FAILURES = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def load_mutated(mutate):
    """Deep-copy the committed doc, apply ``mutate``, load from a temp file."""
    with open(DEFAULT_JSONLD_PATH, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    doc = copy.deepcopy(doc)
    mutate(doc)
    with tempfile.NamedTemporaryFile(
        "w", suffix=".jsonld", delete=False, encoding="utf-8"
    ) as tf:
        json.dump(doc, tf)
        path = tf.name
    try:
        return load_corpus_vocab(path)
    finally:
        os.unlink(path)


def node(doc, uri):
    return next(n for n in doc["@graph"] if n.get("@id") == uri)


def expect_fail(name, mutate, needle=""):
    try:
        load_mutated(mutate)
    except CorpusVocabError as e:
        ok = needle.lower() in str(e).lower() if needle else True
        check(name, ok, f"raised but message lacked {needle!r}: {e}")
        return
    check(name, False, "no CorpusVocabError raised")


def main():
    print("== Corpus vocabulary loader gate ==")

    # ---- 1. Load the committed file ----
    store = load_corpus_vocab(DEFAULT_JSONLD_PATH)
    check("committed JSON-LD loads", store is not None)
    check("scheme labelled", store.scheme_label == "Corpus Vocabulary")
    check("dedicated corpus namespace",
          store.scheme_uri.startswith("corpus:"))
    check("10 concepts", len(store.all_concepts()) == 10,
          f"got {len(store.all_concepts())}")
    check("7 top concepts", len(store.top_concepts()) == 7,
          f"got {len(store.top_concepts())}")
    check("4 collections", len(store.all_collections()) == 4,
          f"got {len(store.all_collections())}")

    # ---- 2. Collections group; concepts carry terms ----
    active = store.collection("corpus:ActiveWorkOrderStates")
    terminal = store.collection("corpus:TerminalWorkOrderStates")
    tb = store.collection(TIME_BASED_COLLECTION)
    gov = store.collection(FORBIDDEN_SYNONYM_COLLECTION)
    check("active states collection",
          active is not None and set(active.members) ==
          {"corpus:UnreleasedState", "corpus:FirmedState", "corpus:ReleasedState"})
    check("terminal states collection",
          terminal is not None and terminal.members == ("corpus:ClosedState",))
    check("time-based collection",
          tb is not None and set(tb.members) ==
          {"corpus:PastDueTerm", "corpus:InHorizonTerm", "corpus:AsOfTerm"})
    check("governance collection",
          gov is not None and gov.members == ("corpus:WorkOrderTerm",))
    check("collections_of finds groupings",
          {c.uri for c in store.collections_of("corpus:ClosedState")} ==
          {"corpus:TerminalWorkOrderStates"})
    wo = store.get("corpus:WorkOrderTerm")
    check("entity term has scope note", bool(wo and wo.scope_note))

    # ---- 3. Lifecycle progression (linear, stored, notated) ----
    chain = store.progression_from("corpus:UnreleasedState")
    check("lifecycle progression order",
          [c.pref_label for c in chain] ==
          ["Unreleased", "Firmed", "Released", "Closed"])
    check("every chain member notated",
          all(c.notation for c in chain))
    check("notation = physical status value",
          [c.notation for c in chain] ==
          ["unreleased", "firmed", "released", "closed"])
    for n in ("unreleased", "firmed", "released", "closed"):
        check(f"notation lookup {n}", store.get_by_notation(n) is not None)
    check("time-based terms carry no notation",
          all(store.get(m).notation is None for m in tb.members))
    check("time-based terms are outside any chain",
          all(not store.get(m).broader and not store.get(m).narrower
              for m in tb.members))

    # ---- 4. OWL contact via closeMatch only ----
    check("lifecycle states closeMatch OWL individuals",
          [c.close_match for c in chain] ==
          [("ledger:UnreleasedWorkOrderState",),
           ("ledger:FirmedWorkOrderState",),
           ("ledger:ReleasedWorkOrderState",),
           ("ledger:ClosedWorkOrderState",)])
    check("entity term closeMatch OWL class",
          wo.close_match == ("ledger:WorkOrder",))
    raw = open(DEFAULT_JSONLD_PATH, encoding="utf-8").read()
    check("no owl:equivalentClass in scheme", "equivalentClass" not in raw)
    check("no rdfs:subClassOf in scheme", "subClassOf" not in raw)

    # ---- 5. Forbidden synonym governance (machine-readable) ----
    fs = store.forbidden_synonyms()
    check("'job' is a governed forbidden synonym",
          fs.get("job") == "Work Order")
    check("'shop order' is a governed forbidden synonym",
          fs.get("shop order") == "Work Order")
    check("hiddenLabel still resolves for matching",
          store.get_by_label("Job") is not None
          and store.get_by_label("Job").pref_label == "Work Order")
    check("practice term keeps 'Job Costing' legitimate",
          store.get_by_label("Job Costing") is not None)

    # ---- 6. Read-only accessor ----
    s2 = get_corpus_vocab_store(reload=True)
    check("singleton accessor loads", s2.scheme_uri == store.scheme_uri)

    # ---- 7. Fail-closed on governance violations ----
    def _branch(doc):
        n = node(doc, "corpus:FirmedState")
        n["narrower"] = ["corpus:ReleasedState", "corpus:ClosedState"]
    expect_fail("branching progression rejected", _branch, "linear")

    def _notationless_chain(doc):
        n = node(doc, "corpus:FirmedState")
        n.pop("notation")
    expect_fail("chain member without notation rejected",
                _notationless_chain, "notation")

    def _time_based_notation(doc):
        n = node(doc, "corpus:PastDueTerm")
        n["notation"] = "past_due"
    expect_fail("notation on time-based term rejected",
                _time_based_notation, "reserved for stored status")

    def _gov_without_hidden(doc):
        n = node(doc, "corpus:WorkOrderTerm")
        n.pop("hiddenLabel")
    expect_fail("governance member without hiddenLabel rejected",
                _gov_without_hidden, "hiddenLabel")

    def _dangling_member(doc):
        n = node(doc, TIME_BASED_COLLECTION)
        n["member"].append("corpus:Ghost")
    expect_fail("dangling collection member rejected",
                _dangling_member, "not a declared concept")

    def _dup_label(doc):
        n = node(doc, "corpus:PastDueTerm")
        n["altLabel"] = ["Shop Order"]
    expect_fail("duplicate label across concepts rejected",
                _dup_label, "duplicate label")

    def _asymmetric(doc):
        n = node(doc, "corpus:ClosedState")
        n["broader"] = "corpus:FirmedState"
    expect_fail("asymmetric hierarchy rejected", _asymmetric, "asymmetric")

    def _missing_collection(doc):
        doc["@graph"] = [n for n in doc["@graph"]
                         if n.get("@id") != FORBIDDEN_SYNONYM_COLLECTION]
    expect_fail("missing required collection rejected",
                _missing_collection, "required collection")

    def _rogue_notation(doc):
        n = node(doc, "corpus:WorkOrderTerm")
        n["notation"] = "work_order"
    expect_fail("notation on non-lifecycle concept rejected",
                _rogue_notation, "reserved for stored status")

    def _orphan(doc):
        n = node(doc, "corpus:AsOfTerm")
        n.pop("topConceptOf")
        sch = node(doc, "corpus:CorpusVocabularyScheme")
        sch["hasTopConcept"].remove("corpus:AsOfTerm")
    expect_fail("orphan concept rejected", _orphan, "neither a top concept")

    print()
    if FAILURES:
        print(f"GATE FAILED — {len(FAILURES)} failure(s): {FAILURES}")
        sys.exit(1)
    print("GATE PASSED — corpus vocabulary loader OK")


if __name__ == "__main__":
    main()
