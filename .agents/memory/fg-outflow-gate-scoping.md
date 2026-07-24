---
name: FG outflow events and reconciliation gate scoping
description: How to add cost-outflow event types to the gl_* ledger without breaking the completion tie-out gates
---

The ledger now has an outbound event type (CUSTOMER_SHIPMENT: a negative
gl_finished_goods_inventory line, one job per event, no WIP/cost-detail lines).

**Rule:** any gate that ties FG to WIP completion outflow must scope FG to
`event_type = 'FG_COMPLETION'` inflows; outbound events get their own separate
gate (per-job net FG never negative). These checks exist in triplicate —
migrations/add_gl_schema_registry.py, tests/test_gl_schema_registry.py, and
tests/test_gl_posting.py — keep all three in sync.

**Why:** the original gates assumed FG contained only completion inflows; the
first shipment event made net-FG-per-job comparisons drift by the shipped cost.

**How to apply (new gl event type checklist):** OWL class in ledger_events.ttl,
SKOS concept+notation in ledger_skos.jsonld, event binding in
ledger_binding_map.json (loader fails closed on any gap), EVENT_TYPE_TO_CLASS +
CLASS_FLOW_PROPERTIES + the unknown-type whitelist in gl_events_rdf.py, posting
fn in gl_posting.py, and bump the counted vocab tests (skos_ledger,
ledger_bindings, semantic_ontology_skos narrower — grep the current counts in
those test files; baked-in numbers here went stale immediately).

Also: shipped CO demand is netted via customer_order_line.shipped_qty —
mrp_engine subtracts it (column-existence-tolerant, since the engine runs
before the shipment migration in the bootstrap chain).
