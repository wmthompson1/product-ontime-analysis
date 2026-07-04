"""test_mrp_keyword_routing.py

Guards the MOCK_ROUTES keyword→intent dispatch table in production_dispatcher.py.

Each test calls extract_via_mock() directly with a natural-language query and
asserts the expected intent and (optionally) the expected primary concept.
SolderEngine is replaced with a MagicMock so no database or manifest file is
needed — the tests are pure routing logic, isolated from SQL assembly.

Coverage:
  - Original MRP routes (reorder, stock status, lead time, replenishment)
  - Priority order: "replenish" wins over the later "inventory" catch-all
  - Batch 7: ATP and AllocatedQuantity
  - Batch 8: SafetyStock, LeadTimeDemand, MinimumStock, MaximumStock, EOQ
  - Priority fix: "lead time demand" wins over the shorter "lead time"
  - Non-MRP routes are unaffected (defect, OEE, supplier)
  - Unknown queries return OUT_OF_SCOPE
"""
import os
import sys
from unittest.mock import MagicMock

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
HF_DIR    = os.path.dirname(TESTS_DIR)
sys.path.insert(0, HF_DIR)

from production_dispatcher import ProductionDispatcher, MOCK_ROUTES  # noqa: E402


def _dispatcher() -> ProductionDispatcher:
    """Return a dispatcher with a mock SolderEngine — no DB or manifest needed."""
    return ProductionDispatcher(solder_engine=MagicMock(), use_live_api=False)


def _route(query: str):
    """Return (intent, concepts) for query via mock routing."""
    result = _dispatcher().extract_via_mock(query)
    return result["intent"], result["concepts"]


# ---------------------------------------------------------------------------
# Original MRP routes
# ---------------------------------------------------------------------------

def test_reorder_routes_to_inventory_planning():
    intent, concepts = _route("Which parts need reordering?")
    assert intent == "inventory_planning", f"Expected inventory_planning, got {intent}"
    assert "ReorderPoint" in concepts


def test_replenish_routes_to_inventory_planning_not_stock_status():
    """'replenish' must win over the later 'inventory' catch-all."""
    intent, concepts = _route("What inventory needs replenishment?")
    assert intent == "inventory_planning", (
        f"Expected inventory_planning (replenish beats inventory catch-all), got {intent}"
    )


def test_stock_level_routes_to_stock_status():
    intent, concepts = _route("What are our current stock levels?")
    assert intent == "inventory_stock_status", f"Expected inventory_stock_status, got {intent}"
    assert "OnHandQuantity" in concepts


def test_on_hand_routes_to_stock_status():
    intent, _ = _route("Show me on hand quantities")
    assert intent == "inventory_stock_status"


def test_lead_time_routes_to_inventory_planning():
    intent, concepts = _route("What is the lead time for titanium brackets?")
    assert intent == "inventory_planning", f"Expected inventory_planning, got {intent}"
    assert "LeadTime" in concepts


def test_mrp_keyword_routes_to_inventory_planning():
    intent, concepts = _route("Run the MRP calculation for this month")
    assert intent == "inventory_planning"
    assert "ReorderPoint" in concepts
    assert "LeadTime" in concepts


# ---------------------------------------------------------------------------
# Batch 7: ATP and AllocatedQuantity
# ---------------------------------------------------------------------------

def test_atp_keyword_routes_to_inventory_atp():
    intent, concepts = _route("What is our ATP for fasteners?")
    assert intent == "inventory_atp", f"Expected inventory_atp, got {intent}"
    assert "AvailableToPromise" in concepts


def test_available_to_promise_phrase_routes_to_atp():
    intent, concepts = _route("Show me the available to promise report")
    assert intent == "inventory_atp"
    assert "AvailableToPromise" in concepts


def test_allocated_keyword_routes_to_allocated_qty():
    intent, concepts = _route("How much stock is already allocated to open orders?")
    assert intent == "inventory_allocated_qty", f"Expected inventory_allocated_qty, got {intent}"
    assert "AllocatedQuantity" in concepts


def test_committed_keyword_routes_to_allocated_qty():
    intent, _ = _route("Show me committed inventory by part")
    assert intent == "inventory_allocated_qty"


# ---------------------------------------------------------------------------
# Batch 8: five remaining glossary concepts
# ---------------------------------------------------------------------------

def test_safety_stock_routes_to_inventory_safety_stock():
    intent, concepts = _route("What safety stock buffer do we carry for bearings?")
    assert intent == "inventory_safety_stock", f"Expected inventory_safety_stock, got {intent}"
    assert "SafetyStock" in concepts


def test_buffer_stock_routes_to_safety_stock():
    intent, _ = _route("Show buffer stock levels by part class")
    assert intent == "inventory_safety_stock"


def test_lead_time_demand_routes_to_lead_time_demand_not_planning():
    """Critical priority test: 'lead time demand' must beat the shorter 'lead time'."""
    intent, concepts = _route("What is the lead time demand for turbine blades?")
    assert intent == "inventory_lead_time_demand", (
        f"Expected inventory_lead_time_demand but got {intent!r}. "
        f"'lead time demand' keyword must appear BEFORE 'lead time' in MOCK_ROUTES."
    )
    assert "LeadTimeDemand" in concepts


def test_demand_during_lead_time_routes_correctly():
    """'demand during lead time' also contains 'lead time' — must resolve to LeadTimeDemand."""
    intent, concepts = _route("What is the demand during lead time for P-10001?")
    assert intent == "inventory_lead_time_demand", (
        f"Expected inventory_lead_time_demand but got {intent!r}."
    )
    assert "LeadTimeDemand" in concepts


def test_minimum_stock_routes_to_minimum_stock():
    intent, concepts = _route("Show minimum stock quantity for active parts")
    assert intent == "inventory_minimum_stock", f"Expected inventory_minimum_stock, got {intent}"
    assert "MinimumStockQuantity" in concepts


def test_min_stock_abbreviation_routes_to_minimum_stock():
    intent, _ = _route("What is the min stock level for hydraulic seals?")
    assert intent == "inventory_minimum_stock"


def test_maximum_stock_routes_to_maximum_stock():
    intent, concepts = _route("What is our maximum stock target for each part?")
    assert intent == "inventory_maximum_stock", f"Expected inventory_maximum_stock, got {intent}"
    assert "MaximumStockQuantity" in concepts


def test_max_stock_abbreviation_routes_to_maximum_stock():
    intent, _ = _route("Show max stock levels across all BUY parts")
    assert intent == "inventory_maximum_stock"


def test_eoq_keyword_routes_to_eoq():
    intent, concepts = _route("What is the EOQ for aluminum brackets?")
    assert intent == "inventory_eoq", f"Expected inventory_eoq, got {intent}"
    assert "EconomicOrderQuantity" in concepts


def test_economic_order_quantity_phrase_routes_to_eoq():
    intent, concepts = _route("Calculate the economic order quantity for fasteners")
    assert intent == "inventory_eoq"
    assert "EconomicOrderQuantity" in concepts


# ---------------------------------------------------------------------------
# Non-MRP routes must be unaffected
# ---------------------------------------------------------------------------

def test_defect_routes_to_quality_trending():
    intent, _ = _route("Show me defect trends this quarter")
    assert intent == "defect_quality_trending"


def test_oee_routes_to_oee_operational():
    intent, _ = _route("What is our OEE for press line 3?")
    assert intent == "oee_operational"


def test_supplier_routes_to_supplier_scorecard():
    intent, _ = _route("Supplier scorecard for Q2")
    assert intent == "supplier_scorecard"


# ---------------------------------------------------------------------------
# Unknown queries return OUT_OF_SCOPE
# ---------------------------------------------------------------------------

def test_unknown_query_returns_out_of_scope():
    intent, concepts = _route("What is the weather like today?")
    assert intent == "OUT_OF_SCOPE", f"Expected OUT_OF_SCOPE, got {intent}"
    assert concepts == []


# ---------------------------------------------------------------------------
# Structural guard: all intents in MOCK_ROUTES must be unique-enough to
# warrant the route (no obvious missing entries for batch 8 concepts).
# ---------------------------------------------------------------------------

def test_all_batch8_concepts_have_routes():
    """Every batch-8 concept must have at least one route in MOCK_ROUTES."""
    expected_intents = {
        "inventory_safety_stock",
        "inventory_lead_time_demand",
        "inventory_minimum_stock",
        "inventory_maximum_stock",
        "inventory_eoq",
    }
    routed_intents = {route["intent"] for route in MOCK_ROUTES.values()}
    missing = expected_intents - routed_intents
    assert not missing, (
        f"The following batch-8 intents have no MOCK_ROUTES entry: {missing}"
    )


# ---------------------------------------------------------------------------
# Standalone runner (also runs under pytest)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _TESTS = [
        test_reorder_routes_to_inventory_planning,
        test_replenish_routes_to_inventory_planning_not_stock_status,
        test_stock_level_routes_to_stock_status,
        test_on_hand_routes_to_stock_status,
        test_lead_time_routes_to_inventory_planning,
        test_mrp_keyword_routes_to_inventory_planning,
        test_atp_keyword_routes_to_inventory_atp,
        test_available_to_promise_phrase_routes_to_atp,
        test_allocated_keyword_routes_to_allocated_qty,
        test_committed_keyword_routes_to_allocated_qty,
        test_safety_stock_routes_to_inventory_safety_stock,
        test_buffer_stock_routes_to_safety_stock,
        test_lead_time_demand_routes_to_lead_time_demand_not_planning,
        test_demand_during_lead_time_routes_correctly,
        test_minimum_stock_routes_to_minimum_stock,
        test_min_stock_abbreviation_routes_to_minimum_stock,
        test_maximum_stock_routes_to_maximum_stock,
        test_max_stock_abbreviation_routes_to_maximum_stock,
        test_eoq_keyword_routes_to_eoq,
        test_economic_order_quantity_phrase_routes_to_eoq,
        test_defect_routes_to_quality_trending,
        test_oee_routes_to_oee_operational,
        test_supplier_routes_to_supplier_scorecard,
        test_unknown_query_returns_out_of_scope,
        test_all_batch8_concepts_have_routes,
    ]
    passed = failed = 0
    for _t in _TESTS:
        try:
            _t()
            print(f"  PASS  {_t.__name__}")
            passed += 1
        except Exception as _exc:
            import traceback
            print(f"  FAIL  {_t.__name__}: {_exc}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    if failed:
        raise SystemExit(1)
