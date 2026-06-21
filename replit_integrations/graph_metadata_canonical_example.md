# graph_metadata_canonical_example.md
replit_integrations\graph_metadata_canonical_example.md

# structural layer (family)

"_id": "manufacturing_graph_edge/PAYABLE:INVOICE_ID:structural:system:has_column:SYS_HAS_PAY_INV_001",
"_key": "PAYABLE:INVOICE_ID:structural:system:has_column:SYS_HAS_PAY_INV_001",

## parity triplet
manufacturing_graph_node/PAYABLE:entity:structural:system:none:none

Predicate (edge_type): has_column

Object (_to): manufacturing_graph_node/PAYABLE:INVOICE_ID:structural:system:none:none

### structural unique edge key
SYS_HAS_PAY_INV_001 = perspective(3) _ edge_type(3) _ table(3) _ column|entity(3) _ uniqifier(3, default 001)

**The Structural ID Generation (`SYS_HAS_PAY_INV_001`)**

* **Perspective (3):** `SYS` (system)
* **Edge Type (3):** `HAS` (has_column)
* **Table (3):** `PAY` (PAYABLE)
* **Column/Entity (3):** `INV` (INVOICE_ID)
* **Uniquifier (3):** `001`

# semantic layer (family)
"_id": "manufacturing_graph_edge/PAYABLE:INVOICE_ID:semantic:Payables:resolves_to:PAY_RES_PAY_INV_001",
"_key": "PAYABLE:INVOICE_ID:semantic:Payables:resolves_to:PAY_RES_PAY_INV_001",

### semantic unique edge key

PAY_RES_PAY_INV_001 = perspective(3) _ edge_type(3) _ table(3) _ column|entity(3) _ uniqifier(3, default 001)

**The Semantic ID Generation (`PAY_RES_PAY_INV_001`)**

* **Perspective (3):** `PAY` (Payables)
* **Edge Type (3):** `RES` (resolves_to)
* **Table (3):** `PAY` (PAYABLE)
* **Column/Entity (3):** `INV` (INVOICE_ID)
* **Uniquifier (3):** `001`

# Concept Node
Name:entity:semantic:canonical:none:none

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
    },
    {
      "_id": "manufacturing_graph_node/InvoiceIdentifier:entity:semantic:canonical:none:none",
      "_key": "InvoiceIdentifier:entity:semantic:canonical:none:none",
      "node_type": "concept",
      "concept_name": "InvoiceIdentifier"
    }
  ],
  "edges": [
    {
      "//": "--- PHYSICAL has_column EDGE ---",
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
      "//": "--- SEMANTIC resolves_to EDGE (column -> concept node, M2/v14) ---",
      "_id": "manufacturing_graph_edge/PAYABLE:INVOICE_ID:semantic:Payables:resolves_to:PAY_RES_PAY_INV_001",
      "_key": "PAYABLE:INVOICE_ID:semantic:Payables:resolves_to:PAY_RES_PAY_INV_001",
      "_from": "manufacturing_graph_node/PAYABLE:INVOICE_ID:structural:system:none:none",
      "_to": "manufacturing_graph_node/InvoiceIdentifier:entity:semantic:canonical:none:none",
      "edge_family": "semantic",
      "edge_type": "resolves_to",
      "perspective": "Payables",
      "unique_id": "PAY_RES_PAY_INV_001",
      "field_component": 1
    },
    {
      "//": "--- PHYSICAL references EDGE ---",
      "_id": "manufacturing_graph_edge/customer_order_line:site_id:structural:system:references:SYS_REF_CUS_SIT_001",
      "_key": "customer_order_line:site_id:structural:system:references:SYS_REF_CUS_SIT_001",

      // 🚀 Declaring Column Node (Child Source)
      "_from": "manufacturing_graph_node/customer_order_line:site_id:structural:system:none:none",

      // 🎯 Referenced Column Node (Parent Target)
      "_to": "manufacturing_graph_node/site:site_id:structural:system:none:none",

      "edge_family": "structural",
      "edge_type": "references",
      "perspective": "system",
      "unique_id": "SYS_REF_CUS_SIT_001"
    }
    
  ]
}
```
