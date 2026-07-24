"""Gate: governed ledger binding map — loader validation + fail-closed proofs.

Run directly (gate style):  python hf-space-inventory-sqlgen/tests/test_ledger_bindings.py

Proves:
  1. The committed binding map loads cleanly and binds every ledger (gl_*)
     table in the governed graph exactly once, and every posting event_type
     exactly once.
  2. Lookups are consistent both directions (concept<->table, class<->type).
  3. The API-facing record view is a plain-dict copy carrying both sections.
  4. FAIL CLOSED: an unknown concept URI, an unknown table, a dropped ledger
     binding, an unknown event class, a wrong event_type, and a duplicated
     event_type each raise LedgerBindingError.
"""

import copy
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(HERE)
sys.path.insert(0, APP_DIR)

import ledger_bindings as lb  # noqa: E402
from ledger_bindings import LedgerBindingError, load_ledger_bindings  # noqa: E402

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if cond:
        PASS += 1
    else:
        FAIL += 1


def _load_map():
    with open(lb.DEFAULT_BINDING_MAP_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _expect_error(name, doc, needle=""):
    with tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="utf-8"
    ) as fh:
        json.dump(doc, fh)
        path = fh.name
    try:
        try:
            load_ledger_bindings(binding_map_path=path)
        except LedgerBindingError as e:
            ok = (needle in str(e)) if needle else True
            check(name, ok, f"raised but message lacked {needle!r}: {e}")
            return
        check(name, False, "no LedgerBindingError raised")
    finally:
        os.unlink(path)


def main():
    print("== Ledger binding map gate ==")

    # ---- 1. Committed map loads and is complete -------------------------
    store = load_ledger_bindings()
    check("committed map loads", True)
    check("5 concept->table bindings", len(store.concept_bindings) == 5,
          str(len(store.concept_bindings)))
    check("6 event-class bindings", len(store.event_bindings) == 6,
          str(len(store.event_bindings)))
    bound_tables = {b.table_name for b in store.concept_bindings}
    check("all five gl_* tables bound", bound_tables == {
        "gl_events", "gl_raw_materials_inventory", "gl_wip_inventory",
        "gl_finished_goods_inventory", "gl_job_cost_detail"})
    bound_types = {b.event_type for b in store.event_bindings}
    check("all six posting event types bound",
          bound_types == {"RM_ISSUE", "LABOR", "BURDEN", "FG_COMPLETION",
                          "CUSTOMER_SHIPMENT", "CASH_RECEIPT"})
    check("every binding carries a prefLabel",
          all(b.pref_label for b in store.concept_bindings))
    check("every event binding carries its SKOS concept",
          all(b.skos_concept_uri.startswith("ledger:")
              for b in store.event_bindings))

    # ---- 2. Bidirectional lookups ---------------------------------------
    check("table_for_concept",
          store.table_for_concept("ledger:WIPInventory") == "gl_wip_inventory")
    check("concept_for_table",
          store.concept_for_table("gl_events") == "ledger:CostAccumulationEvent")
    check("event_type_for_class",
          store.event_type_for_class("ledger:MaterialIssueEvent") == "RM_ISSUE")
    check("class_for_event_type",
          store.class_for_event_type("BURDEN") == "ledger:OverheadApplicationEvent")
    check("unknown lookups return None",
          store.table_for_concept("ledger:Nope") is None
          and store.class_for_event_type("NOPE") is None)

    # ---- 3. Record view ---------------------------------------------------
    rec = store.as_records()
    check("as_records carries both sections",
          len(rec["concept_table_bindings"]) == 5
          and len(rec["event_class_bindings"]) == 6)
    check("as_records is a plain-dict copy",
          isinstance(rec["concept_table_bindings"][0], dict))

    # ---- 4. Fail-closed proofs -------------------------------------------
    base = _load_map()

    doc = copy.deepcopy(base)
    doc["concept_table_bindings"]["ledger:NotAConcept"] = "gl_events_x"
    _expect_error("unknown concept URI fails closed", doc, "absent from the SKOS")

    doc = copy.deepcopy(base)
    doc["concept_table_bindings"]["ledger:RawMaterialsInventory"] = "no_such_table"
    _expect_error("unknown table fails closed", doc, "absent from the governed graph")

    doc = copy.deepcopy(base)
    del doc["concept_table_bindings"]["ledger:WIPInventory"]
    _expect_error("dropped ledger binding fails closed", doc, "left unbound")

    doc = copy.deepcopy(base)
    doc["concept_table_bindings"]["ledger:CostAccumulationEvent"] = "work_order"
    _expect_error("non-ledger table fails closed", doc)

    doc = copy.deepcopy(base)
    doc["event_class_bindings"]["ledger:NoSuchEvent"] = "RM_ISSUE"
    _expect_error("unknown event class fails closed", doc, "not declared")

    doc = copy.deepcopy(base)
    doc["event_class_bindings"]["ledger:MaterialIssueEvent"] = "LABOR"
    _expect_error("wrong event_type fails closed", doc)

    doc = copy.deepcopy(base)
    del doc["event_class_bindings"]["ledger:JobCompletionEvent"]
    _expect_error("unbound event_type fails closed", doc, "left unbound")

    doc = copy.deepcopy(base)
    doc["scheme"] = "ledger:WrongScheme"
    _expect_error("scheme mismatch fails closed", doc, "scheme")

    print()
    if FAIL:
        print(f"RESULT: FAIL ({FAIL} failure(s), {PASS} passed)")
        sys.exit(1)
    print(f"RESULT: LEDGER BINDING GATE PASSED ({PASS} checks)")


if __name__ == "__main__":
    main()
