# graph_metadata_canonical_example.md
replit_integrations\graph_metadata_canonical_example.md

## structural layer (family)

## parity triplet
manufacturing_graph_node/PAYABLE:entity:structural:system

Predicate (edge_type): has_column

Object (_to): manufacturing_graph_node/PAYABLE:INVOICE_ID:structural:system

### structural unique edge key
SYS_HAS_PAY_INV_001 = perspective(3) _ edge_type(3) _ table(3) _ column|entity(3) _ uniqifier(3, default 001)

**The Structural ID Generation (`SYS_HAS_PAY_INV_001`)**

* **Perspective (3):** `SYS` (system)
* **Edge Type (3):** `HAS` (has_column)
* **Table (3):** `PAY` (PAYABLE)
* **Column/Entity (3):** `INV` (INVOICE_ID)
* **Uniquifier (3):** `001`

## semantic layer (family)

## what changed
### semantic unique edge key

PAY_ELE_PAY_INV_001 = perspective(3) _ edge_type(3) _ table(3) _ column|entity(3) _ uniqifier(3, default 001)

**The Semantic ID Generation (`PAY_ELE_PAY_INV_001`)**

* **Perspective (3):** `PAY` (Payables)
* **Edge Type (3):** `ELE` (elevates)
* **Table (3):** `PAY` (PAYABLE)
* **Column/Entity (3):** `INV` (INVOICE_ID)
* **Uniquifier (3):** `001`

## Updated Canonical Milestone

replit_integrations\graph_metadata_canonical_example.json
```JSON
{
  "schema_version": 1,
  "milestone": "database_bound_unambiguous_slots",
  "synced_at": "2026-06-05T20:15:00Z",
  "nodes": [
    {
      "_id": "manufacturing_graph_node/PAYABLE:entity:structural:system:none:none",
      "_key": "PAYABLE:entity:structural:system:none:none",
      "node_type": "table",
      "table_name": "PAYABLE"
    },
    {
      "_id": "manufacturing_graph_node/PAYABLE:INVOICE_ID:structural:system:none:none",
      "_key": "PAYABLE:INVOICE_ID:structural:system:none:none",
      "node_type": "column",
      "column_name": "INVOICE_ID"
    }
  ],
  "edges": [
    {
      "//": "--- PHYSICAL CONTAINMENT EDGE (Unified Abbreviated UID) ---",
      "_id": "manufacturing_graph_edge/PAYABLE:INVOICE_ID:structural:system:has_column:SYS_HAS_PAY_INV_001",
      "_key": "PAYABLE:INVOICE_ID:structural:system:has_column:SYS_HAS_PAY_INV_001",
      "_from": "manufacturing_graph_node/PAYABLE:entity:structural:system:none:none",
      "_to": "manufacturing_graph_node/PAYABLE:INVOICE_ID:structural:system:none:none",
      "edge_family": "structural",
      "edge_type": "has_column",
      "perspective": "system",
      "unique_id": "SYS_HAS_PAY_INV_001"
    },
    {
      "//": "--- SEMANTIC SELF-JOIN EDGE (Unified Abbreviated UID) ---",
      "_id": "manufacturing_graph_edge/PAYABLE:INVOICE_ID:semantic:Payables:elevates:PAY_ELE_PAY_INV_001",
      "_key": "PAYABLE:INVOICE_ID:semantic:Payables:elevates:PAY_ELE_PAY_INV_001",
      "_from": "manufacturing_graph_node/PAYABLE:INVOICE_ID:structural:system:none:none",
      "_to": "manufacturing_graph_node/PAYABLE:INVOICE_ID:structural:system:none:none",
      "edge_family": "semantic",
      "edge_type": "elevates",
      "perspective": "Payables",
      "unique_id": "PAY_ELE_PAY_INV_001"
    }
  ]
}
```
