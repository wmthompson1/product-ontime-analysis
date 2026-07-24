"""Gate: SKOS-first Semantic Ontology pane (Task: SKOS story leads).

Directly runnable (`python tests/test_semantic_ontology_skos.py`), no pytest
required. Proves:
  1. get_skos_overlay resolves committed SKOS concepts for bound gl_* tables
     (URIs, labels, broader chain, event narrower + OWL event classes).
  2. Unbound tables yield no overlay (honest degradation, never invention).
  3. Entity-bound tables (work_order) pull the corpus vocabulary in via the
     committed skos:closeMatch links — incl. lifecycle chain and
     forbidden-synonym governance — and forbidden synonyms never surface as
     preferred labels.
  4. The rendered pane is SKOS-first: SKOS section precedes lineage and the
     frozen graph facts are demoted to a compact trailing section.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(HERE)
sys.path.insert(0, APP_DIR)

from semantic_ontology import (  # noqa: E402
    get_semantic_ontology,
    get_skos_overlay,
    render_semantic_ontology_markdown,
)

DB_PATH = os.path.join(APP_DIR, "app_schema", "manufacturing.db")

PASS = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS
    if not cond:
        print(f"FAIL: {name}" + (f" — {detail}" if detail else ""))
        sys.exit(1)
    PASS += 1
    print(f"ok: {name}")


def main() -> None:
    # 1. Bound ledger tables resolve to committed SKOS concepts.
    ov = get_skos_overlay(
        ["gl_raw_materials_inventory", "gl_wip_inventory", "gl_events"]
    )
    check("bound gl_* tables yield an overlay", ov is not None)
    check(
        "scheme label from committed JSON-LD",
        ov["scheme_label"] == "Job-Costing Ledger Concept Scheme",
        str(ov["scheme_label"]),
    )
    by_table = {c["table"]: c for c in ov["concepts"]}
    check(
        "each bound table resolved exactly once",
        set(by_table) == {
            "gl_raw_materials_inventory", "gl_wip_inventory", "gl_events"
        },
        str(sorted(by_table)),
    )
    rm = by_table["gl_raw_materials_inventory"]
    check(
        "RM concept URI + label",
        rm["uri"] == "ledger:RawMaterialsInventory"
        and rm["pref_label"] == "Raw Materials Inventory",
    )
    check(
        "RM narrower subtypes are vocabulary-only (4)",
        len(rm["narrower"]) == 4
        and all(n["notation"] is None for n in rm["narrower"]),
    )
    ev = by_table["gl_events"]
    ev_narrower = {n["pref_label"]: n for n in ev["narrower"]}
    check(
        "gl_events narrower = 5 posting events with notations",
        {n["notation"] for n in ev["narrower"]}
        == {"RM_ISSUE", "LABOR", "BURDEN", "FG_COMPLETION", "CUSTOMER_SHIPMENT"},
    )
    check(
        "posting event carries its OWL event class from the binding map",
        ev_narrower["Material Issued"].get("event_class")
        == "ledger:MaterialIssueEvent",
        str(ev_narrower["Material Issued"]),
    )
    check(
        "definitions come verbatim from the committed scheme",
        rm["definition"].startswith("Endurant inventory account"),
    )

    # 2. Unbound tables — no overlay, never invention.
    check("unbound tables yield None", get_skos_overlay(["part"]) is None)
    check("empty lineage yields None", get_skos_overlay([]) is None)

    # 3. Entity-bound table pulls the corpus vocabulary via closeMatch.
    ov_wo = get_skos_overlay(["work_order"])
    check("work_order yields corpus overlay", ov_wo is not None)
    corpus_labels = {c["pref_label"] for c in ov_wo["corpus_concepts"]}
    check(
        "corpus:WorkOrderTerm reached via committed closeMatch",
        "Work Order" in corpus_labels,
        str(corpus_labels),
    )
    check(
        "lifecycle progression is the stored status vocabulary",
        [s["notation"] for s in ov_wo["lifecycle"]]
        == ["unreleased", "firmed", "released", "closed"],
        str(ov_wo["lifecycle"]),
    )
    fs = ov_wo["forbidden_synonyms"]
    check(
        "forbidden-synonym governance surfaced (Job / Shop Order)",
        {k.lower() for k in fs} >= {"job", "shop order"},
        str(fs),
    )
    check(
        "forbidden synonyms never appear as corpus preferred labels",
        not ({c["pref_label"] for c in ov_wo["corpus_concepts"]}
             & set(fs.keys())),
    )

    # 4. Rendered pane is SKOS-first with graph facts demoted.
    if os.path.exists(DB_PATH):
        onto = get_semantic_ontology(DB_PATH, "INVENTORYBUCKETBALANCE")
        check("bound anchor resolves in the governed graph", onto is not None)
        md = render_semantic_ontology_markdown(onto, "INVENTORYBUCKETBALANCE")
        i_skos = md.find("#### SKOS concepts")
        i_lineage = md.find("#### `resolves_to` lineage")
        i_facts = md.find("#### Frozen graph facts")
        check("SKOS section present", i_skos >= 0)
        check(
            "SKOS leads, lineage follows, graph facts trail",
            0 <= i_skos < i_lineage < i_facts,
            f"skos={i_skos} lineage={i_lineage} facts={i_facts}",
        )
        check(
            "concept key demoted out of the header",
            "—  concept node" not in md,
        )

        onto_ss = get_semantic_ontology(DB_PATH, "SAFETYSTOCK")
        if onto_ss is not None:
            md_ss = render_semantic_ontology_markdown(onto_ss, "SAFETYSTOCK")
            check(
                "unbound anchor degrades honestly (no SKOS invention)",
                "No SKOS coverage" in md_ss
                and "#### SKOS concepts" not in md_ss,
            )
    else:
        print("note: app DB missing — renderer checks skipped (overlay "
              "checks above are file-only and did run)")

    print(f"\nAll {PASS} SKOS-first semantic ontology checks passed.")


if __name__ == "__main__":
    main()
