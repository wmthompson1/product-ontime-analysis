---
title: Confirm 'Which parts need reordering?' routes to the new MRP SQL without manual intent selection
---
# Confirm 'Which parts need reordering?' routes to the new MRP SQL without manual intent selection

  ## What & Why
  The SolderEngine now returns correct SQL when `inventory_planning` is selected as the intent,
  but the Production Dispatcher's mock keyword router and live HuggingFace Inference API router
  have not been updated to recognise MRP inventory questions. A user asking "Which parts need
  reordering?" in the Ask a Question tab will currently get no intent match instead of the new
  ReorderPoint snippet.

  ## Done looks like
  - The mock keyword router in `production_dispatcher.py` maps inventory/reorder/stock/MRP
    question patterns to `inventory_planning` and `inventory_stock_status`
  - The Dispatcher's example-questions list in `app.py` includes at least one MRP question
  - Asking "Which parts need reordering?" in Demo Mode returns the ReorderPoint SQL

  ## Relevant files
  - `hf-space-inventory-sqlgen/production_dispatcher.py` — keyword mapping dict
  - `hf-space-inventory-sqlgen/app.py` lines 5300-5308 — example questions markdown