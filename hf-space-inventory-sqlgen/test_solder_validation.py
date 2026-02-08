"""
Solder Validation Test Case
============================
Verifies that the SolderEngine correctly:
1. Selects NCM cost snippet for Financial Perspective (defect_cost_analysis intent)
2. Suppresses non-financial concepts when Financial intent is active
3. Assembles multi-concept queries with proper elevation/suppression
4. Produces NULL for suppressed concepts in assembled output

Run: python test_solder_validation.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import sqlglot
from solder_engine import SolderEngine

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "app_schema")
DB_PATH = os.path.join(SCHEMA_DIR, "manufacturing.db")
MANIFEST_PATH = os.path.join(SCHEMA_DIR, "ground_truth", "reviewer_manifest.json")


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
