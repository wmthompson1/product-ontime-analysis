```mermaid
flowchart LR
  subgraph InventoryFlow [Inventory Transactions Flow]
    IT[INVENTORY_TRANS] -->|transaction_id| TIT[TRACE_INV_TRANS]
    TIT -->|trace_id| TR[TRACE]
    IT -->|workorder_base_id| WO[WORK_ORDER]
    WO -->|base_id| REQ[REQUIREMENT]
    IT <-->|inv_trans_dist| IT2[INVENTORY_TRANS]
  end

  classDef table fill:#f8f9fa,stroke:#333,stroke-width:1px;
  class IT,TIT,TR,WO,REQ,IT2 table;

  %% Notes: TRACE contains LOT_ID, SERIAL_ID and APROPERTY_1..5 (flex fields)
```

This diagram shows the common join path used in reports: INVENTORY_TRANS -> TRACE_INV_TRANS -> TRACE. `INV_TRANS_DIST` links paired IN/OUT transactions when present.
## Inventory Transactions Flow

work_order
join operation
...
and o.WORKORDER_SUB_ID = a.SUB_ID
join REQUIREMENT
...
-- > subordinate work order link:
and o.WORKORDER_SUB_ID = ISNULL(r.SUBORD_WO_SUB_ID, 0)

## inventory_transactions_flow
select 1 --. . .
from inventory_trans t ---, warehouse w, location l
  join dbo.warehouse w
  on w.id = t.warehouse_id
  join dbo.[location] l
  on w.id = l.warehouse_id
  and t.location_id = l.id
  LEFT JOIN TRACE_INV_TRANS ti WITH (NOLOCK)
  ON ti.TRANSACTION_ID = t.TRANSACTION_ID
  LEFT JOIN TRACE tr WITH (NOLOCK)
  ON tr.ID = ti.TRACE_ID

where t.class IN ( 'i' , 'r' )
  AND t.type IN ( 'i' , 'r' ) 
    AND ( T.SITE_ID IN ( N'SK01' ) )