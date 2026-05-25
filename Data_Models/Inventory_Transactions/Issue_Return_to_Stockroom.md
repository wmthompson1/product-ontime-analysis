# Issue Return to Stockroom

## Overview

Return issued material from work orders back to inventory. This transaction reverses a previous issue transaction, returning unused or excess raw materials to the stockroom.

---

## Database Schema

| Attribute | Value |
|-----------|-------|
| **CLASS** | `I` (Issue) |
| **TYPE** | `I` (In) |
| **Scenario** | 5 |
| **Effect on QOH** | `+1 * QTY` (Increases inventory) |

---

## ⚠️ Critical Distinction

**Issue Return (I+I)** is NOT the same as **Receipt Return (R+O)**

| Transaction | Direction | QOH Effect | Use Case |
|-------------|-----------|------------|----------|
| **Issue Return** (I+I) | Work Order → Inventory | ↑ Increases | Unused raw materials returned to stockroom |
| **Receipt Return** (R+O) | Inventory → WIP/Vendor | ↓ Decreases | Finished goods back to WIP or vendor returns |

```
ISSUE RETURN (I+I):
┌─────────────┐         ┌───────────┐
│ Work Order  │ ──────> │ Inventory │
│   (WIP)     │  Return │ (Stock)   │
└─────────────┘  Unused └───────────┘
                Material
Effect: +QTY to Inventory
```

---

## Business Process

### Typical Workflow

1. **Material Previously Issued**
   - Material was issued to work order (I+O transaction)
   - Material staged at work center
   - Now determined to be unused/excess

2. **Determine Return Quantity**
   - Excess material not needed
   - Material issued in error
   - Damaged material before use
   - Operation cancelled or modified

3. **Return to Stockroom**
   - Transport material back to warehouse
   - Scan or enter return transaction
   - Specify return location (may differ from original issue location)

4. **Execute Transaction**
   - Select work order and piece number
   - Enter return quantity
   - Select warehouse/location for return
   - Optionally enter reason code

5. **System Updates**
   - Inventory QOH increased
   - Work order material cost decreased
   - Material requirement re-released if was closed
   - Requirement completion percentage updated

---

## Transaction Fields

### Required Fields

| Field | Description | Source |
|-------|-------------|--------|
| `SITE_ID` | Site where transaction occurs | System/User selection |
| `PART_ID` | Part being returned | Auto-populated from requirement |
| `WORKORDER_BASE_ID` | Work order base identifier | User selection |
| `WORKORDER_LOT_ID` | Work order lot identifier | Auto-populated |
| `WORKORDER_SPLIT_ID` | Work order split identifier | Auto-populated |
| `WORKORDER_SUB_ID` | Subordinate work order (leg) | Auto-populated if exists |
| `OPERATION_SEQ_NO` | Operation from which returning | From requirement |
| `REQ_PIECE_NO` | Material requirement card | User selection |
| `QTY` | Quantity being returned | User entry |
| `WAREHOUSE_ID` | Warehouse receiving material | User selection (may default) |
| `LOCATION_ID` | Location receiving material | User selection (may default) |

### Optional Fields

| Field | Description | Notes |
|-------|-------------|-------|
| `ISSUE_REAS_ID` | Reason code for return | May be required per site settings |
| `DESCRIPTION` | Transaction description | Explain reason for return |
| `TRANSACTION_DATE` | Date of transaction | Defaults to current date |

### System-Generated Fields

| Field | Value | Purpose |
|-------|-------|---------|
| `TRANSACTION_ID` | Auto-generated unique ID | Transaction identifier |
| `CLASS` | `'I'` | Issue classification |
| `TYPE` | `'I'` | In type (return direction) |
| `ACT_MATERIAL_COST` | Calculated (negative) | Cost removed from WO |

---

## Quantity Tracking

### Display Values During Transaction

| Display Field | Description | Calculation |
|---------------|-------------|-------------|
| **Required** | Total quantity needed | From `REQUIREMENT.CALC_QTY` |
| **Issued** | Net quantity issued to WO | Issues - Returns |
| **Due** | Remaining quantity to issue | Required - Issued (net) |
| **On Hand** | Part QOH across all locations | Current inventory |
| **Available** | Available QOH | After this return applied |

### Material Requirement Status Changes

```sql
-- If requirement was closed:
IF (Issued_Qty >= Required_Qty) THEN
    Requirement_Status = 'Closed'
END IF

-- After Issue Return:
New_Issued_Qty = Issued_Qty - Return_Qty

IF (New_Issued_Qty < Required_Qty) THEN
    Requirement_Status = 'Released'  -- Re-opens requirement
END IF
```

**Important:** Issue returns can re-open a closed requirement

---

## Cost Accounting

### Material Cost Reversal

```sql
-- Cost returned FROM work order TO inventory
ACT_MATERIAL_COST = -(QTY * Part_Unit_Cost)

-- Negative cost reduces work order WIP
```

### Accounting Impact

**Debit:** Inventory Asset Account
**Credit:** Work Order WIP Account

**Work Order Costing:**
- Material cost decreased on work order
- WIP value reduced
- May impact work order variance calculations

---

## Traceability

### Lot-Tracked Parts

**All lot numbers previously issued to the requirement appear:**
- System shows lot numbers with unreceived (unissued) quantity
- User selects which lot numbers to return
- System auto-distributes return quantity across lots
- User can modify default distribution

**Creating New Lot Numbers:**
- Unlikely at this point
- Lot numbers typically assigned at receipt or issue
- If material from different lot, use Insert to add new line

### Serial-Tracked Parts

**Cannot return piece-tracked parts using table method**
- Must use Auto Issue/Return mode with warehouse prompts
- Each serial number returns individually

**See:** [Issue Returning Piece Tracked Parts to Inventory](../Help-md/VM/Issue_Returning_Piece_Tracked_Parts_to_Inventory.md)

---

## Validation Rules

### Pre-Transaction Validation

| Check | Rule | Error/Warning |
|-------|------|---------------|
| Part exists | Part must exist in PART table | "Part not found" |
| Work order exists | WO must exist | "Work order not found" |
| Requirement exists | Piece No must exist | "Material requirement not found" |
| Previously issued | Net issued qty must be > 0 | "No quantity issued to return" |
| Return quantity | Return_Qty <= Net_Issued_Qty | Warning if exceeding (may allow) |
| Location valid | Warehouse/Location must exist | "Location not valid" |

### Over-Return Validation

**Behavior when Return_Qty > Net_Issued_Qty:**
- System displays warning message
- User can cancel or accept override
- If accepted, may create negative issued quantity
- Controlled by site settings

---

## Special Cases

### Purchase Order Linked Requirements

**If requirement is linked to PO:**
- Cannot use Inventory Transaction Entry for purchase returns
- Must use Purchase Receipt Entry to process vendor returns
- System will generate Receipt Return transaction automatically

### Multi-Location Returns

**Returning to different location than original issue:**
- Allowed based on site settings
- Default location may be specified in Site Maintenance
- User can override default location

### Partial Returns

**Allowed:** Return partial quantities across multiple transactions

**Example:**
- Issued: 100 EA
- Return 1: 20 EA (Net issued = 80)
- Return 2: 10 EA (Net issued = 70)
- Remaining issued to WO: 70 EA

---

## Move Requests Integration

### Warehouse Management

If using move requests:
- Issue return can trigger move request
- Material moves from work center to stockroom
- Move request links to inventory transaction
- Tracks physical movement separately from transaction

**Fields in Move Request:**

| Field | Value |
|-------|-------|
| Transaction Type | "Inventory" |
| From Resource | Operation resource |
| From Department | Operation department |
| To Warehouse | Return warehouse ID |
| To Location | Return location ID (default stockroom) |

**See:** [Creating Move Requests in Inventory Transaction Entry](../Help-md/VM/Creating_Move_Requests_in_Inventory_Transaction_Entry.md)

---

## SQL Examples

### Find All Issue Returns for Work Order

```sql
SELECT 
    i.TRANSACTION_ID,
    i.TRANSACTION_DATE,
    i.PART_ID,
    i.OPERATION_SEQ_NO,
    i.REQ_PIECE_NO,
    i.QTY AS Return_Qty,
    i.WAREHOUSE_ID,
    i.LOCATION_ID,
    i.ACT_MATERIAL_COST,
    i.ISSUE_REAS_ID,
    i.DESCRIPTION
FROM INVENTORY_TRANS i
WHERE i.TYPE = 'I' 
  AND i.CLASS = 'I'  -- Issue Return
  AND i.WORKORDER_BASE_ID = '1234567'
ORDER BY i.TRANSACTION_DATE;
```

### Calculate Net Issued Quantity

```sql
SELECT 
    r.WORKORDER_BASE_ID,
    r.OPERATION_SEQ_NO,
    r.PIECE_NO,
    r.PART_ID,
    r.CALC_QTY AS Required,
    ISNULL(SUM(CASE 
        WHEN i.TYPE = 'O' THEN i.QTY   -- Issues (positive)
        WHEN i.TYPE = 'I' THEN -i.QTY  -- Returns (negative)
    END), 0) AS Net_Issued,
    r.CALC_QTY - ISNULL(SUM(CASE 
        WHEN i.TYPE = 'O' THEN i.QTY 
        WHEN i.TYPE = 'I' THEN -i.QTY 
    END), 0) AS Still_Due
FROM REQUIREMENT r
LEFT JOIN INVENTORY_TRANS i
  ON i.WORKORDER_BASE_ID = r.WORKORDER_BASE_ID
  AND i.WORKORDER_LOT_ID = r.WORKORDER_LOT_ID
  AND i.WORKORDER_SPLIT_ID = r.WORKORDER_SPLIT_ID
  AND i.OPERATION_SEQ_NO = r.OPERATION_SEQ_NO
  AND i.REQ_PIECE_NO = r.PIECE_NO
  AND i.CLASS = 'I'  -- Issue transactions only
WHERE r.WORKORDER_BASE_ID = '1234567'
GROUP BY r.WORKORDER_BASE_ID, r.OPERATION_SEQ_NO, r.PIECE_NO, 
         r.PART_ID, r.CALC_QTY
ORDER BY r.OPERATION_SEQ_NO, r.PIECE_NO;
```

### Audit Issue/Return Activity

```sql
SELECT 
    i.TRANSACTION_DATE,
    i.TRANSACTION_ID,
    CASE 
        WHEN i.TYPE = 'O' THEN 'Issue'
        WHEN i.TYPE = 'I' THEN 'Issue Return'
    END AS Transaction_Type,
    i.PART_ID,
    i.QTY,
    i.WAREHOUSE_ID,
    i.LOCATION_ID,
    i.USER_ID,
    i.DESCRIPTION
FROM INVENTORY_TRANS i
WHERE i.CLASS = 'I'  -- All issue-related transactions
  AND i.WORKORDER_BASE_ID = '1234567'
  AND i.REQ_PIECE_NO = 1
ORDER BY i.TRANSACTION_DATE;
```

---

## Return by Exception

### Batch Processing Alternative

**Use Return by Exception to:**
- View all requirements with issued quantities
- Return materials from multiple requirements
- Use auto-mode for automatic processing
- Specify different return locations per requirement

**See:** [Issue and Return by Exception](../Help-md/VM/VMINVENT_APLfrmIssue.md)

---

## Troubleshooting

### Common Issues

**"No quantity issued to return"**
- Verify material was previously issued
- Check for negative issued quantities
- Review transaction history

**"Cannot exceed issued quantity"**
- Net issued quantity < return quantity
- Check for prior returns
- May be allowed as override

**"Material requirement re-opened unexpectedly"**
- Expected behavior when net issued < required
- Return caused requirement to fall below completion threshold

**"Cost not reversing on work order"**
- Verify CLASS='I' and TYPE='I'
- Check ACT_MATERIAL_COST is negative
- Review work order costing configuration

---

## Related Transactions

| Transaction | Relationship |
|-------------|--------------|
| [Issue Material to Work Order](Issue_Material_to_Work_Order.md) | Original transaction being reversed (I+O) |
| [Receipt Return](Receipt_Return_to_Work_Order.md) | Different transaction (R+O) - DO NOT CONFUSE |
| [Adjust Material In](Adjust_Material_In.md) | Alternative for non-WO returns (A+I) |

---

## See Also

- [Inventory Transaction Entry Index](Inventory_Transaction_Entry_Index.md)
- [Inventory Transaction Terminology Guide](Inventory_Transaction_Terminology_Guide.md)
- [Returning Issued Materials](../Help-md/VM/Returning_Issued_Materials.md)
- [For Return of Issued Material from a Work Order](../Help-md/VM/For_Return_of_Issued_Material_from_a_Work_Order.md)
