this file: C:\Users\williamt\source\skillsinc\skills-inc-org\SQL-Projects\Documentation\Data Models\Inventory_Transactions\Inventory_transactions_flow.md

todo: create mermaid for files so named ...mermaidbased on schema flow
## Inventory Transactions Flow
- mermaid files were created without mermaid (add todo)
- sql in Inventory_Transactions_Filtered.sql
- folder: Documentation\Data Models\Inventory_Transactions\
Documentation\Data Models\Inventory_Transactions\inventory_material_requirements_mermaid.md
Documentation\Data Models\Inventory_Transactions\Inventory_Transactions_Filtered.sql
Documentation\Data Models\Inventory_Transactions\inventory_transactions_flow_mermaid.md
Documentation\Data Models\Inventory_Transactions\material_requirements_flow_mermaid.md
Documentation\Data Models\Inventory_Transactions\materiall_requirements_flow.md
Documentation\Data Models\Inventory_Transactions\work_order_operations_flow_mermaid.md
Documentation\Data Models\Inventory_Transactions\work_order_operations_flow.md


inventory transaction flow
    -inventory_transactions
    -TRACE_INV_TRANS  (intermediate)
    -trace
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

  ### Mermaid Diagrams
  - Inventory transactions flow: [inventory_transactions_flow_mermaid.md](inventory_transactions_flow_mermaid.md)
  - Material requirements flow: [material_requirements_flow_mermaid.md](material_requirements_flow_mermaid.md)
  - Work order operations flow: [work_order_operations_flow_mermaid.md](work_order_operations_flow_mermaid.md)