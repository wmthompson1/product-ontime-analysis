import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hf-space-inventory-sqlgen"))

from semantic_reasoning import get_cypher_traversal, get_aql_traversal


INTENT = "quality_analysis"
TABLE = "defect_events"
FIELD = "defect_count"


def test_get_cypher_traversal_fires_deprecation_warning():
    with pytest.warns(DeprecationWarning, match="get_cypher_traversal\\(\\) returns an ILLUSTRATIVE template only"):
        result = get_cypher_traversal(INTENT, TABLE, FIELD)
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_aql_traversal_fires_deprecation_warning():
    with pytest.warns(DeprecationWarning, match="get_aql_traversal\\(\\) returns an ILLUSTRATIVE template only"):
        result = get_aql_traversal(INTENT, TABLE, FIELD)
    assert isinstance(result, str)
    assert len(result) > 0


def test_cypher_warning_mentions_retired_perspective():
    with pytest.warns(DeprecationWarning) as record:
        get_cypher_traversal(INTENT, TABLE, FIELD)
    messages = [str(w.message) for w in record]
    assert any("Perspective vertex is retired" in m for m in messages)


def test_aql_warning_mentions_retired_perspective():
    with pytest.warns(DeprecationWarning) as record:
        get_aql_traversal(INTENT, TABLE, FIELD)
    messages = [str(w.message) for w in record]
    assert any("Perspective vertex is retired" in m for m in messages)


def test_cypher_warning_cautions_against_live_execution():
    with pytest.warns(DeprecationWarning) as record:
        get_cypher_traversal(INTENT, TABLE, FIELD)
    messages = [str(w.message) for w in record]
    assert any("Do not execute" in m for m in messages)


def test_aql_warning_cautions_against_live_execution():
    with pytest.warns(DeprecationWarning) as record:
        get_aql_traversal(INTENT, TABLE, FIELD)
    messages = [str(w.message) for w in record]
    assert any("Do not execute" in m for m in messages)
