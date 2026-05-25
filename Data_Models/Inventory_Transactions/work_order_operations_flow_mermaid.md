```mermaid
flowchart LR
  subgraph WorkOrderOps [Work Order Operations Flow]
    WO[WORK_ORDER] --> OP[WORK_ORDER_OPERATION]
    OP --> REQ[REQUIREMENT]
    REQ --> IT[INVENTORY_TRANS]
    IT --> TIT[TRACE_INV_TRANS]
    TIT --> TR[TRACE]
  end

  classDef table fill:#e6f7ff,stroke:#333,stroke-width:1px;
  class WO,OP,REQ,IT,TIT,TR table;

  %% Notes: Operation sequencing and sub-id matching are used to join requirements to subordinate WOs.
```

This diagram captures work order -> operations -> requirement -> inventory -> trace chain.
## work order operations flow
- perspective: inventory transactions

```
-- inventory transaction flow
from #inventory_trans i
  -- **work order operatioopns flow**
  inner 
  join dbo.WORK_ORDER a
  on i.WORKORDER_BASE_ID=a.BASE_ID
    and i.WORKORDER_LOT_ID=a.LOT_ID and
    i.WORKORDER_SPLIT_ID = a.SPLIT_ID


  INNER JOIN OPERATION o
  on o.WORKORDER_BASE_ID=a.BASE_ID and o.WORKORDER_LOT_ID=a.LOT_ID and
    o.WORKORDER_SPLIT_ID = a.SPLIT_ID
    and o.WORKORDER_SUB_ID = a.SUB_ID
```