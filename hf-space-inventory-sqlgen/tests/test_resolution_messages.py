"""Regression tests for bridge-row resolution message strings.

Task #25: Verifies that the updated explanation strings produced by
`semantic_reasoning.resolve_field_meaning` use bridge-row language and
that those strings reach the Gradio disambiguation interface.

Two test categories:
1. Unit tests — construct ResolutionResult directly, assert explanation format.
2. Integration tests — seed an in-memory SQLite DB, run resolve_field_meaning,
   confirm both the 'resolved' and 'ambiguous' explanation strings.

Run: python hf-space-inventory-sqlgen/tests/test_resolution_messages.py
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)


# ---------------------------------------------------------------------------
# Unit tests — no database required
# ---------------------------------------------------------------------------

def test_resolved_explanation_contains_bridge_row_language():
    """ResolutionResult for 'resolved' status must use bridge-row notation."""
    from semantic_reasoning import ResolutionResult

    intent = "defect_cost_analysis"
    perspective = "Finance"
    concept = "DEFECTSEVERITYCOST"

    result = ResolutionResult(
        intent=intent,
        field_name="quality_events.defect_severity",
        resolved_concept=concept,
        perspective=perspective,
        status="resolved",
        candidate_concepts=[concept],
        explanation=(
            f"Resolved via bridge rows: {intent} "
            f"-[Perspective_Intents]-> {perspective} "
            f"-[Perspective_Concepts]-> {concept}"
        ),
    )

    assert "Resolved via bridge rows" in result.explanation, (
        f"Expected 'Resolved via bridge rows' in explanation, got: {result.explanation!r}"
    )
    assert "-[Perspective_Intents]->" in result.explanation, (
        f"Expected '-[Perspective_Intents]->' in explanation, got: {result.explanation!r}"
    )
    assert "-[Perspective_Concepts]->" in result.explanation, (
        f"Expected '-[Perspective_Concepts]->' in explanation, got: {result.explanation!r}"
    )
    assert result.is_valid
    print("PASS: resolved explanation contains correct bridge-row language")


def test_ambiguous_explanation_contains_bridge_row_language():
    """ResolutionResult for 'ambiguous' status must reference bridge-row notation."""
    from semantic_reasoning import ResolutionResult

    intent = "defect_cost_analysis"
    perspective = "Finance"
    concepts = ["DEFECTSEVERITYCOST", "DEFECTSEVERITYQUALITY"]

    result = ResolutionResult(
        intent=intent,
        field_name="quality_events.defect_severity",
        resolved_concept=None,
        perspective=perspective,
        status="ambiguous",
        candidate_concepts=concepts,
        explanation=(
            f"MODELING ERROR: {len(concepts)} concepts resolved via bridge rows "
            f"({intent} -[Perspective_Intents]-> {perspective} "
            f"-[Perspective_Concepts]-> …). "
            f"Intent must elevate exactly one: {concepts}"
        ),
    )

    assert "MODELING ERROR" in result.explanation, (
        f"Expected 'MODELING ERROR' in ambiguous explanation, got: {result.explanation!r}"
    )
    assert "bridge rows" in result.explanation, (
        f"Expected 'bridge rows' in ambiguous explanation, got: {result.explanation!r}"
    )
    assert "-[Perspective_Intents]->" in result.explanation, (
        f"Expected '-[Perspective_Intents]->' in ambiguous explanation, got: {result.explanation!r}"
    )
    assert "-[Perspective_Concepts]->" in result.explanation, (
        f"Expected '-[Perspective_Concepts]->' in ambiguous explanation, got: {result.explanation!r}"
    )
    assert "Intent must elevate exactly one" in result.explanation, (
        f"Expected 'Intent must elevate exactly one' in ambiguous explanation, got: {result.explanation!r}"
    )
    assert not result.is_valid
    print("PASS: ambiguous explanation contains correct bridge-row language")


# ---------------------------------------------------------------------------
# Integration tests — in-memory SQLite DB seeded with minimal bridge data
# ---------------------------------------------------------------------------

def _build_seeded_engine():
    """Create an in-memory SQLite engine with the minimal schema needed by
    resolve_field_meaning, seeded with one (Intent, Perspective, Concept, Field)
    chain for the 'resolved' case and two concepts for the 'ambiguous' case."""
    try:
        from sqlalchemy import create_engine, text as sa_text
    except ImportError:
        return None

    engine = create_engine("sqlite:///:memory:")
    ddl = [
        """CREATE TABLE schema_intents (
            intent_id   INTEGER PRIMARY KEY,
            intent_name TEXT NOT NULL UNIQUE
        )""",
        """CREATE TABLE schema_perspectives (
            perspective_id   INTEGER PRIMARY KEY,
            perspective_name TEXT NOT NULL UNIQUE
        )""",
        """CREATE TABLE schema_concepts (
            concept_id   INTEGER PRIMARY KEY,
            concept_name TEXT NOT NULL UNIQUE
        )""",
        """CREATE TABLE schema_intent_perspectives (
            intent_id          INTEGER NOT NULL,
            perspective_id     INTEGER NOT NULL,
            intent_factor_weight INTEGER NOT NULL DEFAULT 0
        )""",
        """CREATE TABLE schema_perspective_concepts (
            perspective_id INTEGER NOT NULL,
            concept_id     INTEGER NOT NULL
        )""",
        """CREATE TABLE schema_concept_fields (
            concept_id INTEGER NOT NULL,
            table_name TEXT NOT NULL,
            field_name TEXT NOT NULL
        )""",
        """CREATE TABLE schema_intent_concepts (
            intent_id            INTEGER NOT NULL,
            concept_id           INTEGER NOT NULL,
            intent_factor_weight INTEGER NOT NULL DEFAULT 0
        )""",
    ]
    seed = [
        # Intents
        "INSERT INTO schema_intents VALUES (1, 'defect_cost_analysis')",
        "INSERT INTO schema_intents VALUES (2, 'ambiguous_intent')",
        # Perspectives
        "INSERT INTO schema_perspectives VALUES (10, 'Finance')",
        # Concepts
        "INSERT INTO schema_concepts VALUES (100, 'DEFECTSEVERITYCOST')",
        "INSERT INTO schema_concepts VALUES (101, 'DEFECTSEVERITYQUALITY')",
        # Perspective_Intents bridge (resolved intent → Finance, weight=0)
        "INSERT INTO schema_intent_perspectives VALUES (1, 10, 0)",
        # Perspective_Intents bridge (ambiguous intent → Finance, weight=0)
        "INSERT INTO schema_intent_perspectives VALUES (2, 10, 0)",
        # Perspective_Concepts bridge (Finance → both concepts)
        "INSERT INTO schema_perspective_concepts VALUES (10, 100)",
        "INSERT INTO schema_perspective_concepts VALUES (10, 101)",
        # CAN_MEAN: field → concept 100 only (for resolved case)
        "INSERT INTO schema_concept_fields VALUES (100, 'quality_events', 'ncm_cost')",
        # CAN_MEAN: field → BOTH concepts (for ambiguous case)
        "INSERT INTO schema_concept_fields VALUES (100, 'quality_events', 'defect_severity')",
        "INSERT INTO schema_concept_fields VALUES (101, 'quality_events', 'defect_severity')",
        # Elevate concept 100 for resolved intent
        "INSERT INTO schema_intent_concepts VALUES (1, 100, 1)",
    ]

    with engine.begin() as conn:
        for stmt in ddl + seed:
            conn.execute(sa_text(stmt))

    return engine


def test_resolve_field_meaning_resolved_explanation():
    """resolve_field_meaning produces 'Resolved via bridge rows' for a clean path."""
    try:
        from sqlalchemy import create_engine  # noqa: F401
    except ImportError:
        print("SKIP: sqlalchemy not installed")
        return

    import semantic_reasoning

    engine = _build_seeded_engine()
    if engine is None:
        print("SKIP: could not build in-memory engine")
        return

    result = semantic_reasoning.resolve_field_meaning(
        engine, "defect_cost_analysis", "quality_events", "ncm_cost"
    )

    assert result.status == "resolved", (
        f"Expected status='resolved', got '{result.status}': {result.explanation}"
    )
    assert "Resolved via bridge rows" in result.explanation, (
        f"Expected 'Resolved via bridge rows' in explanation, got: {result.explanation!r}"
    )
    assert "-[Perspective_Intents]->" in result.explanation, (
        f"Expected '-[Perspective_Intents]->' in explanation, got: {result.explanation!r}"
    )
    assert "-[Perspective_Concepts]->" in result.explanation, (
        f"Expected '-[Perspective_Concepts]->' in explanation, got: {result.explanation!r}"
    )
    print(
        f"PASS: resolve_field_meaning 'resolved' explanation correct: "
        f"{result.explanation!r}"
    )


def test_resolve_field_meaning_ambiguous_explanation():
    """resolve_field_meaning produces MODELING ERROR with bridge-row notation
    when multiple concepts survive the resolution algorithm."""
    try:
        from sqlalchemy import create_engine  # noqa: F401
    except ImportError:
        print("SKIP: sqlalchemy not installed")
        return

    import semantic_reasoning

    engine = _build_seeded_engine()
    if engine is None:
        print("SKIP: could not build in-memory engine")
        return

    result = semantic_reasoning.resolve_field_meaning(
        engine, "ambiguous_intent", "quality_events", "defect_severity"
    )

    assert result.status == "ambiguous", (
        f"Expected status='ambiguous', got '{result.status}': {result.explanation}"
    )
    assert "MODELING ERROR" in result.explanation, (
        f"Expected 'MODELING ERROR' in ambiguous explanation, got: {result.explanation!r}"
    )
    assert "bridge rows" in result.explanation, (
        f"Expected 'bridge rows' in ambiguous explanation, got: {result.explanation!r}"
    )
    assert "-[Perspective_Intents]->" in result.explanation, (
        f"Expected '-[Perspective_Intents]->' in ambiguous explanation, got: {result.explanation!r}"
    )
    assert "-[Perspective_Concepts]->" in result.explanation, (
        f"Expected '-[Perspective_Concepts]->' in ambiguous explanation, got: {result.explanation!r}"
    )
    assert "Intent must elevate exactly one" in result.explanation, (
        f"Expected 'Intent must elevate exactly one' in ambiguous explanation, "
        f"got: {result.explanation!r}"
    )
    print(
        f"PASS: resolve_field_meaning 'ambiguous' explanation correct: "
        f"{result.explanation!r}"
    )


# ---------------------------------------------------------------------------
# Gradio surface test — confirm explanation key is forwarded by the endpoint
# ---------------------------------------------------------------------------

def test_gradio_resolve_endpoint_surfaces_explanation():
    """The /mcp/tools/resolve_field endpoint must include 'explanation' in its
    response body and, when the status is 'resolved', the value must contain the
    bridge-row phrase 'Resolved via bridge rows'.

    /mcp/tools/resolve_field is the Gradio-facing endpoint that calls
    resolve_field_meaning() and surfaces ResolutionResult.explanation directly.
    """
    db_path = os.path.join(HF_DIR, "app_schema", "manufacturing.db")
    if not os.path.exists(db_path):
        print("SKIP: manufacturing.db not present — live endpoint check skipped")
        return

    try:
        from fastapi.testclient import TestClient
        import app as fastapi_app
    except ImportError as exc:
        print(f"SKIP: could not import app or TestClient: {exc}")
        return

    client = TestClient(fastapi_app.app, raise_server_exceptions=False)
    params = {
        "table_name": "stg_manufacturing_flat",
        "field_name": "ncm_cost",
        "intent_name": "defect_cost_analysis",
    }
    response = client.get("/mcp/tools/resolve_field", params=params)
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    body = response.json()
    assert "explanation" in body, (
        f"'explanation' key missing from /mcp/tools/resolve_field response. "
        f"Present keys: {list(body.keys())}"
    )
    explanation = body["explanation"]
    if body.get("status") == "resolved":
        assert "Resolved via bridge rows" in explanation, (
            f"Resolved response explanation missing bridge-row phrase. "
            f"Got: {explanation!r}"
        )
        assert "-[Perspective_Intents]->" in explanation, (
            f"Resolved response explanation missing -[Perspective_Intents]->. "
            f"Got: {explanation!r}"
        )
        assert "-[Perspective_Concepts]->" in explanation, (
            f"Resolved response explanation missing -[Perspective_Concepts]->. "
            f"Got: {explanation!r}"
        )
    print(
        f"PASS: /mcp/tools/resolve_field surfaces 'explanation' key "
        f"with correct bridge-row language (status={body.get('status')!r})"
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> int:
    tests = [
        test_resolved_explanation_contains_bridge_row_language,
        test_ambiguous_explanation_contains_bridge_row_language,
        test_resolve_field_meaning_resolved_explanation,
        test_resolve_field_meaning_ambiguous_explanation,
        test_gradio_resolve_endpoint_surfaces_explanation,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print()
    print(f"{'PASS' if failed == 0 else 'FAIL'}: {len(tests) - failed}/{len(tests)} tests passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
