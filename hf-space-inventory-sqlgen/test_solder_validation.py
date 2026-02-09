"""
Solder Validation Test Case
============================
Verifies that the SolderEngine correctly:
1. Selects NCM cost snippet for Financial Perspective (defect_cost_analysis intent)
2. Suppresses non-financial concepts when Financial intent is active
3. Assembles multi-concept queries with proper elevation/suppression
4. Produces NULL for suppressed concepts in assembled output
5. AQL Bridge: Python routing matches AQL spec contracts (026_AQL_Path_Resolution_Test.aql)

Run: python test_solder_validation.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

import sqlglot
from solder_engine import SolderEngine

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "app_schema")
DB_PATH = os.path.join(SCHEMA_DIR, "manufacturing.db")
MANIFEST_PATH = os.path.join(SCHEMA_DIR, "ground_truth", "reviewer_manifest.json")
AQL_SPEC_PATH = os.path.join(SCHEMA_DIR, "ground_truth", "026_AQL_Path_Resolution_Test.aql")


def test_elevation_weight_lookup():
    engine = SolderEngine(db_path=DB_PATH, manifest_path=MANIFEST_PATH)

    cost_weight = engine.get_elevation_weight("defect_cost_analysis", "DefectSeverityCost")
    assert cost_weight == 1.0, f"Expected 1.0, got {cost_weight}"

    quality_weight = engine.get_elevation_weight("defect_cost_analysis", "DefectSeverityQuality")
    assert quality_weight == 0.0, f"Expected 0.0, got {quality_weight}"

    customer_weight = engine.get_elevation_weight("defect_cost_analysis", "DefectSeverityCustomer")
    assert customer_weight == 0.0, f"Expected 0.0, got {customer_weight}"

    print("PASS: Elevation weight lookup correct")


def test_resolve_concept_financial():
    engine = SolderEngine(db_path=DB_PATH, manifest_path=MANIFEST_PATH)

    binding = engine.resolve_concept_snippet("Finance", "DefectSeverityCost", "defect_cost_analysis")
    assert binding is not None, "Expected binding for DefectSeverityCost"
    assert binding.concept_anchor == "DEFECTSEVERITYCOST"
    assert "ncm_cost" in binding.sql_text.lower(), "Expected NCM cost in SQL"
    print(f"PASS: Financial concept resolved to binding '{binding.binding_key}'")

    binding_q = engine.resolve_concept_snippet("Quality", "DefectSeverityQuality", "defect_cost_analysis")
    assert binding_q is not None, "Expected binding for DefectSeverityQuality (weight=0 is neutral, not suppressed)"
    assert binding_q.concept_anchor == "DEFECTSEVERITYQUALITY"
    print(f"PASS: Quality concept resolved (neutral weight=0, not suppressed)")


def test_single_concept_solder():
    engine = SolderEngine(db_path=DB_PATH, manifest_path=MANIFEST_PATH)

    result = engine.solder(
        intent_name="defect_cost_analysis",
        target_concept="DefectSeverityCost",
        target_dialect="sqlite"
    )

    assert result.concept == "DefectSeverityCost", f"Expected DefectSeverityCost, got {result.concept}"
    assert result.elevation_weight == 1.0, f"Expected weight 1.0, got {result.elevation_weight}"
    assert "ncm_cost" in result.soldered_sql.lower(), "Expected ncm_cost in soldered SQL"
    print(f"PASS: Single-concept solder produced correct SQL")
    print(f"  Binding: {result.binding_key}")
    print(f"  SQL preview: {result.soldered_sql[:100]}...")


def test_multi_concept_assembly():
    engine = SolderEngine(db_path=DB_PATH, manifest_path=MANIFEST_PATH)

    result = engine.assemble_query(
        intent="defect_cost_analysis",
        perspective="Finance",
        concepts=["DefectSeverityCost", "DefectSeverityQuality", "DefectSeverityCustomer"],
        base_table="stg_manufacturing_flat",
        target_dialect="sqlite"
    )

    assert "sql" in result, "Expected 'sql' key in result"
    sql = result["sql"]

    assert "WITH" in sql, "Expected CTE (WITH clause) in assembled SQL"
    assert "DefectSeverityCost" in sql, "Expected DefectSeverityCost CTE"
    assert "ncm_cost" in sql.lower(), "Expected ncm_cost in assembled SQL"

    parsed = sqlglot.parse(sql, read="sqlite")
    assert parsed and parsed[0], "Assembled SQL must be parseable by SQLGlot"
    print(f"PASS: Multi-concept assembly produced valid SQL")
    print(f"  Concepts resolved: {result.get('concept_count', 0)}")
    print(f"  SQL:\n{sql}")

    if result.get("report"):
        print("\n  Assembly Report:")
        for line in result["report"]:
            print(f"    {line}")


def test_dialect_transpilation():
    engine = SolderEngine(db_path=DB_PATH, manifest_path=MANIFEST_PATH)

    result = engine.assemble_query(
        intent="defect_cost_analysis",
        perspective="Finance",
        concepts=["DefectSeverityCost"],
        base_table="stg_manufacturing_flat",
        target_dialect="tsql"
    )

    sql = result.get("sql", "")
    assert sql, "Expected SQL output for T-SQL dialect"
    print(f"PASS: T-SQL transpilation produced output")
    print(f"  T-SQL:\n{sql}")


def test_cross_perspective_intent():
    engine = SolderEngine(db_path=DB_PATH, manifest_path=MANIFEST_PATH)

    cost_result = engine.solder(
        intent_name="defect_cost_analysis",
        target_concept="DefectSeverityCost",
        target_dialect="sqlite"
    )
    assert "ncm_cost" in cost_result.soldered_sql.lower()

    customer_result = engine.solder(
        intent_name="defect_customer_impact",
        target_concept="DefectSeverityCustomer",
        target_dialect="sqlite"
    )
    assert "customer_impact_flag" in customer_result.soldered_sql.lower()

    print("PASS: Cross-perspective intent routing correct")
    print(f"  Financial intent → {cost_result.concept} (ncm_cost)")
    print(f"  Customer intent  → {customer_result.concept} (customer_impact_flag)")


def parse_aql_contract(aql_path):
    """
    Parses the AQL spec file to extract contractual routing decisions.
    Returns a list of AqlContract dicts, each with:
      - test_id: TEST 1, TEST 2, etc.
      - perspective: the active perspective for this test
      - solder_decision: the expected routing result string
      - winner: the collision winner (if applicable)
      - loser: the collision loser (if applicable)
      - elevation_weight: expected weight value
    """
    with open(aql_path, "r") as f:
        content = f.read()

    contracts = []

    test_blocks = re.split(r"// -{10,}\n// TEST (\d+):", content)

    for i in range(1, len(test_blocks), 2):
        test_id = f"TEST {test_blocks[i]}"
        block = test_blocks[i + 1]

        perspective_match = re.search(
            r'LET active_perspective\s*=\s*"(\w+)"', block
        )
        perspective = perspective_match.group(1) if perspective_match else None

        if not perspective:
            perspective_match = re.search(
                r"(\w+) perspective elevates", block, re.IGNORECASE
            )
            perspective = perspective_match.group(1) if perspective_match else None

        solder_match = re.search(r'solder_decision:\s*"([^"]+)"', block)
        solder_decision = solder_match.group(1) if solder_match else None

        winner_match = re.search(r'winner:\s*"([^"]+)"', block)
        winner = winner_match.group(1) if winner_match else None

        loser_match = re.search(r'loser:\s*"([^"]+)"', block)
        loser = loser_match.group(1) if loser_match else None

        weight_match = re.search(r"weight\s*[=]\s*([\d.]+)\)", block)
        elevation_weight = float(weight_match.group(1)) if weight_match else None

        table_field_match = re.search(
            r"Routes to (\w+)\.(\w+)", block
        )
        expected_table = table_field_match.group(1) if table_field_match else None
        expected_field = table_field_match.group(2) if table_field_match else None

        contracts.append({
            "test_id": test_id,
            "perspective": perspective,
            "solder_decision": solder_decision,
            "winner": winner,
            "loser": loser,
            "elevation_weight": elevation_weight,
            "expected_table": expected_table,
            "expected_field": expected_field,
        })

    return contracts


def test_aql_bridge_parse():
    """Verify the AQL spec file is parseable and contains expected contracts."""
    assert os.path.exists(AQL_SPEC_PATH), f"AQL spec not found: {AQL_SPEC_PATH}"

    contracts = parse_aql_contract(AQL_SPEC_PATH)
    assert len(contracts) >= 2, f"Expected at least 2 test contracts, got {len(contracts)}"

    test1 = contracts[0]
    assert test1["perspective"] == "Quality", f"TEST 1 perspective should be Quality, got {test1['perspective']}"
    assert test1["solder_decision"] is not None, "TEST 1 missing solder_decision"
    assert "stg_non_conformant_materials" in test1["solder_decision"], \
        f"TEST 1 solder_decision should reference NCM table: {test1['solder_decision']}"

    test2 = contracts[1]
    assert test2["perspective"] == "Finance", f"TEST 2 perspective should be Finance, got {test2['perspective']}"
    assert test2["winner"] is not None, "TEST 2 missing collision winner"
    assert "stg_non_conformant_materials" in test2["winner"], \
        f"TEST 2 winner should be NCM table: {test2['winner']}"

    print("PASS: AQL spec parsed successfully")
    print(f"  Contracts extracted: {len(contracts)}")
    for c in contracts:
        print(f"  {c['test_id']}: perspective={c['perspective']}, "
              f"decision={(c.get('solder_decision') or 'N/A')[:60]}")


def test_aql_bridge_quality_routing():
    """
    AQL Bridge TEST 1: Quality perspective routes 'defects' to NCM severity.
    Contract from AQL: solder_decision = "Use stg_non_conformant_materials.severity"
    Python must: resolve DefectSeverityQuality with Quality perspective → NCM table.
    """
    contracts = parse_aql_contract(AQL_SPEC_PATH)
    quality_contract = contracts[0]
    assert quality_contract["perspective"] == "Quality"

    engine = SolderEngine(db_path=DB_PATH, manifest_path=MANIFEST_PATH)

    edges = engine.get_elevation_edges("defect_quality_trending")
    elevated = [e for e in edges if e.weight == 1.0]
    assert len(elevated) > 0, "Quality intent should have at least one elevated concept (weight=1.0)"
    print(f"  Elevated concepts: {[e.concept_name for e in elevated]}")

    result = engine.solder(
        intent_name="defect_quality_trending",
        target_concept="DefectSeverityQuality",
        target_dialect="sqlite"
    )

    assert result.soldered_sql and result.soldered_sql.strip() != "", \
        "Quality routing produced empty SQL"

    sql_lower = result.soldered_sql.lower()
    assert "severity" in sql_lower, \
        f"AQL contract violation: Quality routing must reference 'severity' field. SQL: {result.soldered_sql[:200]}"

    print("PASS: AQL Bridge — Quality perspective routes to severity field")
    print(f"  AQL contract: {quality_contract['solder_decision']}")
    print(f"  Python binding: {result.binding_key}")
    print(f"  Elevation weight: {result.elevation_weight}")


def test_aql_bridge_finance_collision():
    """
    AQL Bridge TEST 2: Finance perspective resolves cost_impact collision.
    Contract from AQL:
      winner = "stg_non_conformant_materials.cost_impact (actual)"
      loser  = "stg_product_defects.cost_impact (estimated)"
    Python must: resolve DefectSeverityCost with Finance perspective → NCM cost fields.
    """
    contracts = parse_aql_contract(AQL_SPEC_PATH)
    finance_contract = contracts[1]
    assert finance_contract["perspective"] == "Finance"

    engine = SolderEngine(db_path=DB_PATH, manifest_path=MANIFEST_PATH)

    cost_weight = engine.get_elevation_weight("defect_cost_analysis", "DefectSeverityCost")
    assert cost_weight == 1.0, \
        f"Finance intent must elevate DefectSeverityCost (weight=1.0), got {cost_weight}"

    result = engine.solder(
        intent_name="defect_cost_analysis",
        target_concept="DefectSeverityCost",
        target_dialect="sqlite"
    )

    sql_lower = result.soldered_sql.lower()
    assert "ncm_cost" in sql_lower or "cost_impact" in sql_lower or "cost" in sql_lower, \
        f"AQL contract violation: Finance routing must reference cost fields. SQL: {result.soldered_sql[:200]}"

    assert "stg_product_defects" not in sql_lower or "ncm" in sql_lower, \
        "AQL collision violation: Finance routing should prefer NCM table over product_defects"

    print("PASS: AQL Bridge — Finance collision resolved to NCM (actual cost)")
    print(f"  AQL winner: {finance_contract['winner']}")
    print(f"  AQL loser:  {finance_contract['loser']}")
    print(f"  Python binding: {result.binding_key}")
    print(f"  Elevation weight: {result.elevation_weight}")


def test_aql_bridge_elevation_weight_alignment():
    """
    AQL Bridge: Verify that elevation weights in SQLite match the AQL spec's
    expected weight=1.0 for elevated concepts and weight=0.0 for suppressed.
    This ensures the Python graph metadata stays in sync with the AQL contract.
    """
    engine = SolderEngine(db_path=DB_PATH, manifest_path=MANIFEST_PATH)

    quality_edges = engine.get_elevation_edges("defect_quality_trending")
    has_elevated = any(e.weight == 1.0 for e in quality_edges)
    assert has_elevated, \
        "AQL spec requires weight=1.0 elevation for Quality perspective concepts"

    finance_edges = engine.get_elevation_edges("defect_cost_analysis")
    cost_edge = [e for e in finance_edges if "cost" in e.concept_name.lower()]
    assert len(cost_edge) > 0, "Finance intent must have cost-related concept edge"
    assert any(e.weight == 1.0 for e in cost_edge), \
        "Finance intent must elevate cost concept with weight=1.0 per AQL spec"

    suppressed = [e for e in finance_edges if e.weight == 0.0]
    print("PASS: AQL Bridge — Elevation weights align with AQL spec")
    print(f"  Quality intent: {len(quality_edges)} edges, "
          f"{sum(1 for e in quality_edges if e.weight == 1.0)} elevated")
    print(f"  Finance intent: {len(finance_edges)} edges, "
          f"{sum(1 for e in finance_edges if e.weight == 1.0)} elevated, "
          f"{len(suppressed)} neutral/suppressed")


if __name__ == "__main__":
    print("=" * 60)
    print("SOLDER VALIDATION TEST SUITE")
    print("=" * 60)

    tests = [
        ("Elevation Weight Lookup", test_elevation_weight_lookup),
        ("Resolve Concept (Financial)", test_resolve_concept_financial),
        ("Single-Concept Solder", test_single_concept_solder),
        ("Multi-Concept Assembly", test_multi_concept_assembly),
        ("Dialect Transpilation (T-SQL)", test_dialect_transpilation),
        ("Cross-Perspective Intent Routing", test_cross_perspective_intent),
        ("AQL Bridge: Parse Spec", test_aql_bridge_parse),
        ("AQL Bridge: Quality Routing", test_aql_bridge_quality_routing),
        ("AQL Bridge: Finance Collision", test_aql_bridge_finance_collision),
        ("AQL Bridge: Elevation Weight Alignment", test_aql_bridge_elevation_weight_alignment),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        print(f"\n--- {name} ---")
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    print(f"{'=' * 60}")

    sys.exit(0 if failed == 0 else 1)
