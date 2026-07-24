"""Gate-style test for the SKOS ledger concept loader (skos_ledger.py).

Run directly: python hf-space-inventory-sqlgen/tests/test_skos_ledger.py
Exits non-zero on any failure.

Proves: load from the committed JSON-LD, lookup by URI/label/notation,
hierarchy traversal (broader/narrower/ancestors/descendants), the read-only
accessor, and fail-closed behavior on malformed input.
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skos_ledger import (  # noqa: E402
    DEFAULT_JSONLD_PATH,
    SkosLoadError,
    get_ledger_concept_store,
    load_ledger_concepts,
)

FAILURES = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


LEDGER = "http://example.org/manufacturing/ledger#"


def expand(doc):
    """The committed file uses the 'ledger:' prefix; loader keeps ids verbatim."""
    return doc


def main():
    print("== SKOS ledger loader gate ==")

    # ---- 1. Load the committed file ----
    store = load_ledger_concepts(DEFAULT_JSONLD_PATH)
    check("committed JSON-LD loads", store is not None)
    check("scheme labelled", store.scheme_label == "Job-Costing Ledger Concept Scheme")
    check("14 concepts", len(store.all_concepts()) == 14,
          f"got {len(store.all_concepts())}")
    check("5 top concepts", len(store.top_concepts()) == 5,
          f"got {len(store.top_concepts())}")

    # ---- 2. Lookups ----
    rm = store.get_by_label("Raw Materials Inventory")
    check("lookup by prefLabel", rm is not None and rm.uri == "ledger:RawMaterialsInventory")
    check("lookup case-insensitive", store.get_by_label("wip inventory") is not None)
    check("lookup by altLabel", store.get_by_label("FG") is not None
          and store.get_by_label("FG").uri == "ledger:FinishedGoodsInventory")
    check("lookup by URI", store.get("ledger:JobCostDetail") is not None)
    check("unknown label returns None", store.get_by_label("nope") is None)
    # Event vocabulary notations match the gl_events event_type values.
    for notation, label in [("RM_ISSUE", "Material Issued"), ("LABOR", "Labor Applied"),
                            ("BURDEN", "Overhead Applied"), ("FG_COMPLETION", "Job Completion")]:
        c = store.get_by_notation(notation)
        check(f"notation {notation}", c is not None and c.pref_label == label)

    # ---- 3. Hierarchy traversal ----
    kids = store.narrower_of("ledger:RawMaterialsInventory")
    check("RM has 4 subtypes", {k.pref_label for k in kids} ==
          {"Standards", "Detail Parts", "Components", "Sheet Metal"})
    sheet = store.get_by_label("Sheet Metal")
    check("broader of subtype", store.broader_of(sheet.uri).uri == "ledger:RawMaterialsInventory")
    anc = store.ancestors(sheet.uri)
    check("ancestors chain to top", len(anc) == 1 and anc[0].top_concept)
    desc = store.descendants("ledger:CostAccumulationEvent")
    check("event vocabulary has 5 events", len(desc) == 5)
    check("top concept has no broader", store.broader_of("ledger:WIPInventory") is None)

    # ---- 4. Read-only accessor ----
    s1 = get_ledger_concept_store(reload=True)
    s2 = get_ledger_concept_store()
    check("accessor is cached singleton", s1 is s2)
    recs = s1.as_records()
    check("as_records exposes all concepts", len(recs) == 14
          and all(r["pref_label"] and r["definition"] for r in recs))

    # ---- 5. Fail-closed on malformed input ----
    with open(DEFAULT_JSONLD_PATH, "r", encoding="utf-8") as fh:
        good = json.load(fh)

    def expect_fail(name, mutate):
        doc = json.loads(json.dumps(good))
        mutate(doc)
        with tempfile.NamedTemporaryFile("w", suffix=".jsonld", delete=False) as tmp:
            json.dump(doc, tmp)
            path = tmp.name
        try:
            load_ledger_concepts(path)
            check(name, False, "loaded despite defect")
        except SkosLoadError:
            check(name, True)
        finally:
            os.unlink(path)

    def find(doc, cid):
        return next(n for n in doc["@graph"] if n.get("@id") == cid)

    try:
        load_ledger_concepts("/nonexistent/ledger.jsonld")
        check("missing file fails closed", False)
    except SkosLoadError:
        check("missing file fails closed", True)

    expect_fail("empty definition rejected",
                lambda d: find(d, "ledger:WIPInventory").update({"definition": ""}))
    expect_fail("dangling broader rejected",
                lambda d: find(d, "ledger:SheetMetalRawMaterial").update({"broader": "ledger:Ghost"}))
    expect_fail("asymmetric narrower rejected",
                lambda d: find(d, "ledger:RawMaterialsInventory")["narrower"].remove(
                    "ledger:SheetMetalRawMaterial"))
    expect_fail("duplicate URI rejected",
                lambda d: d["@graph"].append(dict(find(d, "ledger:WIPInventory"))))
    expect_fail("orphan (no broader, not top) rejected",
                lambda d: find(d, "ledger:MaterialIssued").pop("broader"))
    expect_fail("top-concept mismatch rejected",
                lambda d: find(d, "ledger:JobCostingLedgerScheme")["hasTopConcept"].remove(
                    "ledger:JobCostDetail"))
    expect_fail("duplicate label rejected",
                lambda d: find(d, "ledger:JobCostDetail").update({"prefLabel": "WIP Inventory"}))
    expect_fail("not-JSON rejected",
                lambda d: d.pop("@graph"))

    print()
    if FAILURES:
        print(f"RESULT: FAIL ({len(FAILURES)} failure(s)): {FAILURES}")
        sys.exit(1)
    print("RESULT: SKOS LEDGER LOADER GATE PASSED")


if __name__ == "__main__":
    main()
