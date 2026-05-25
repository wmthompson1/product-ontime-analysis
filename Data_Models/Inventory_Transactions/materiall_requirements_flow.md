# Material Requirements Flow

## Inventory Transaction Class and Type Definitions

### Transaction Scenarios

Inventory transactions are classified by two key attributes: **CLASS** and **TYPE**. These determine the direction and nature of the transaction's effect on Quantity on Hand (QOH).

| Scenario | Class | Type | Class Tag | Type Tag | Effect on QOH | Context |
|----------|-------|------|-----------|----------|---------------|---------|
| 1 | R | I | Released | In | `+1 * QTY` | Material received from Purchase Order |
| 2 | A | O | Adjust | Out | `-1 * QTY` | Inventory adjustment decreasing stock |
| 3 | A | I | Adjust | In | `+1 * QTY` | Inventory adjustment increasing stock |
| 4 | I | O | Issue | Out | `-1 * QTY` | Material issued to Work Order |
| 5 | I | I | Issue | In | `+1 * QTY` | Material returned from Work Order (Issue Return) |

### CLASS Definitions

- **R (Released)**: Material receipts from purchase orders or vendors
- **A (Adjust)**: Manual inventory adjustments for corrections
- **I (Issue)**: Material movements to/from work orders

### TYPE Definitions

- **I (In)**: Transaction increases Quantity on Hand
- **O (Out)**: Transaction decreases Quantity on Hand

### Effect on QOH Calculation

```sql
CASE
    WHEN TYPE = 'I' AND CLASS = 'R' THEN 1  -- Receipt In
    WHEN TYPE = 'O' AND CLASS = 'I' THEN -1  -- Issue Out
    WHEN TYPE = 'O' AND CLASS = 'A' THEN -1  -- Adjust Out
    WHEN TYPE = 'I' AND CLASS = 'A' THEN 1   -- Adjust In
    WHEN TYPE = 'I' AND CLASS = 'I' THEN 1   -- Issue Return In
    WHEN TYPE = 'O' AND CLASS = 'R' THEN -1  -- Receipt Return Out
    ELSE 0
END * QTY
```

---

## Data Flow Relationships

### 1) **Inventory Transaction Flow**
  - Reference: [inventory_transactions_flow.md](Inventory_transactions_flow.md)
```sql
FROM #inventory_trans i
```

### 2) **Work Order Operations Flow**
```sql
INNER JOIN dbo.WORK_ORDER a
  ON i.WORKORDER_BASE_ID = a.BASE_ID
  AND i.WORKORDER_LOT_ID = a.LOT_ID
  AND i.WORKORDER_SPLIT_ID = a.SPLIT_ID

INNER JOIN OPERATION o
  ON o.WORKORDER_BASE_ID = a.BASE_ID
  AND o.WORKORDER_LOT_ID = a.LOT_ID
  AND o.WORKORDER_SPLIT_ID = a.SPLIT_ID
  AND o.WORKORDER_SUB_ID = a.SUB_ID
```

### 3) **Materials Requirement Flow**
*(Includes subordinate work order link)*
```sql
INNER JOIN REQUIREMENT r WITH (NOLOCK)
  ON i.part_id = r.part_id
  AND o.WORKORDER_BASE_ID = r.WORKORDER_BASE_ID
  AND o.WORKORDER_LOT_ID = r.WORKORDER_LOT_ID
  AND o.WORKORDER_SPLIT_ID = r.WORKORDER_SPLIT_ID
  AND o.SEQUENCE_NO = r.OPERATION_SEQ_NO
  AND o.WORKORDER_SUB_ID = ISNULL(r.SUBORD_WO_SUB_ID, 0)
```

---

## Key Relationships

### Purchase Order Context
- **Scenario 1 (R+I)**: Links to `purc_order_id` when material is received

### Work Order Context
- **Scenario 4 (I+O)**: Links to `work_order` (BASE_ID/LOT_ID/SPLIT_ID) when material is issued
- **Scenario 5 (I+I)**: Links to `work_order` when material is returned from issue

### Adjustment Context
- **Scenarios 2 & 3 (A+O/A+I)**: Typically used for cycle counts, physical inventory corrections, or manual adjustments