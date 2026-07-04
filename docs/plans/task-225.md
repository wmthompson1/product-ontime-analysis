---
title: Wire the remaining 7 MRP glossary concepts (SafetyStock, ATP, AllocatedQty, etc.) to real columns so they also return SQL
---
# Wire the remaining 7 MRP glossary concepts to real columns so they also return SQL

  ## What & Why
  This task wired ReorderPoint, LeadTime, and OnHandQuantity (the 3 concepts with existing
  physical column bindings). Seven other MRP concepts promoted into the certified layer are still
  glossary-only nodes with no column binding and no approved SQL snippet:
  SafetyStock, LeadTimeDemand, MinimumStockQuantity, MaximumStockQuantity,
  EconomicOrderQuantity, AvailableToPromise, AllocatedQuantity.

  For ATP and AllocatedQuantity, the data is derivable from customer_order_line and
  inventory_transaction tables already in manufacturing.db.

  ## Done looks like
  - Column bindings added to schema_concept_fields for at least ATP and AllocatedQuantity
  - SME-approved SQL snippets added for those concepts
  - seed_elevations.py and reviewer_manifest.json updated
  - SolderEngine returns real SQL for each newly wired concept

  ## Relevant files
  - `replit_integrations/seed_elevations.py` — ELEVATIONS list (batch 6)
  - `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/`
  - `hf-space-inventory-sqlgen/app_schema/ground_truth/reviewer_manifest.json`
  - `hf-space-inventory-sqlgen/app_schema/manufacturing.db` — customer_order_line, inventory_transaction tables