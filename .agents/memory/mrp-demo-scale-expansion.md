---
name: MRP synthetic expansion vs demo-scale prune bands
description: Constraints any synthetic ERP data expansion must respect so bootstrap re-runs stay stable.
---
Rule: any migration that adds synthetic CO/WO/PO headers must (a) run AFTER prune_erp_to_demo_scale in the bootstrap chain and (b) leave header counts inside the prune bands (CO/WO [10,20], PO [10,25]), or a bootstrap re-run trims the rows and the keep-set reshuffles non-deterministically.

**Why:** prune skips trimming only when counts are already in band (`already_at_demo_scale`); out-of-band counts trigger a trim whose keep-set depends on current demand parts, diverging fresh vs re-run states.

**How to apply:** scale demand via many customer_order_line rows on a couple of Open COs (prune always keeps Open COs) and supply via consolidated multi-line block POs, not per-part headers. Positive on_hand_qty alone is a valid supply basis per validate_planning_inputs. Demand dates must reuse backfill_mrp_demand_supply's exact crc32("col:<order_line_id>") formula so a backfill re-run is a no-op (the expansion migration imports its `_horizon_date`).
