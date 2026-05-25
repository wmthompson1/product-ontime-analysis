# Issue Material to Work Order

## Overview

Issue raw materials from inventory to work order material requirements for production consumption. This transaction relieves inventory and charges material costs to the work order.

---

## Database Schema

| Attribute | Value |
|-----------|-------|
| **CLASS** | `I` (Issue) |
| **TYPE** | `O` (Out) |
| **Scenario** | 4 |
| **Effect on QOH** | `-1 * QTY` (Decreases inventory) |

---

## Business Process

### Typical Workflow

1. **Print Work Order Pick List**
   - Generate pick list showing required materials
   - Lists warehouse locations for each part
   - Shows required quantities per operation

2. **Locate Material**
   - Navigate to warehouse location
   - Scan or manually locate part
   - Verify part number and lot/serial if traced

3. **Move to Production**
   - Transport material to work center
   - Stage at operation location
   - May create move request if using WMS

4. **Execute Issue Transaction**
   - Scan or enter part ID
   - Select work order and piece number (requirement)
   - Enter quantity and location
   - Save transaction to relieve inventory

5. **System Updates**
   - Inventory QOH decreased
   - Work order material cost increased
   - Material requirement marked as issued
   - Completion percentage updated

---

## Transaction Fields

### Required Fields

| Field | Description | Source |
|-------|-------------|--------|
| `SITE_ID` | Site where transaction occurs | System/User selection |
| `PART_ID` | Part being issued | From material requirement |
| `WORKORDER_BASE_ID` | Work order base identifier | User selection |
| `WORKORDER_LOT_ID` | Work order lot identifier | Auto-populated |
| `WORKORDER_SPLIT_ID` | Work order split identifier | Auto-populated |
| `WORKORDER_SUB_ID` | Subordinate work order (leg) | Auto-populated if exists |
| `OPERATION_SEQ_NO` | Operation requiring material | From requirement |
| `REQ_PIECE_NO` | Material requirement card | User selection |
| `QTY` | Quantity being issued | User entry |
| `WAREHOUSE_ID` | Warehouse issuing material | User selection |
| `LOCATION_ID` | Location issuing material | User selection |

### Optional Fields

| Field | Description | Notes |
|-------|-------------|-------|
| `ISSUE_REAS_ID` | Reason code for issue | May be required per site settings |
| `DESCRIPTION` | Transaction description | Free text explanation |
| `TRANSACTION_DATE` | Date of transaction | Defaults to current date |
| `USER_ID` | User creating transaction | Auto-populated |

### System-Generated Fields

| Field | Value | Purpose |
|-------|-------|---------|
| `TRANSACTION_ID` | Auto-generated unique ID | Transaction identifier |
| `CLASS` | `'I'` | Transaction classification |
| `TYPE` | `'O'` | Transaction type |
| `ACT_MATERIAL_COST` | Calculated | Material cost charged to WO |
| `ACT_LABOR_COST` | Calculated | Labor cost if applicable |
| `ACT_BURDEN_COST` | Calculated | Overhead cost if applicable |
| `ACT_SERVICE_COST` | Calculated | Service cost if applicable |

---

## Material Requirement Linking

### Standard Issue (Existing Requirement)

```sql
-- Links to existing material requirement
INNER JOIN REQUIREMENT r
  ON r.WORKORDER_BASE_ID = i.WORKORDER_BASE_ID
  AND r.WORKORDER_LOT_ID = i.WORKORDER_LOT_ID
  AND r.WORKORDER_SPLIT_ID = i.WORKORDER_SPLIT_ID
  AND r.OPERATION_SEQ_NO = i.OPERATION_SEQ_NO
  AND r.PIECE_NO = i.REQ_PIECE_NO
  AND r.SUBORD_WO_SUB_ID = ISNULL(i.WORKORDER_SUB_ID, 0)
```

### New Material Requirement

**Special Case:** SYSADM user can add new material requirements directly in Inventory Transaction Entry

**Requirements:**
- User must be `SYSADM`
- `NewMaterialMode` preference must be set to `On`
- Check **New Material Req't** checkbox
- Select piece number that doesn't exist
- Select part ID to add

---

## Quantity Tracking

### Display Values During Transaction

| Display Field | Description | Calculation |
|---------------|-------------|-------------|
| **Required** | Total quantity needed | From `REQUIREMENT.CALC_QTY` |
| **Issued** | Previously issued quantity | Sum of prior issues |
| **Due** | Remaining quantity to issue | Required - Issued |
| **On Hand** | Part QOH across all locations | From `PART.QTY_ON_HAND` |
| **Available** | Available QOH (not allocated) | From `PART.QTY_AVAILABLE` |

### Material Requirement Completion

```sql
-- Calculate completion percentage
Completion_Pct = (Issued_Qty / Required_Qty) * 100

-- Requirement closes when:
Issued_Qty >= Required_Qty
```

---

## Special Cases

### Purchase Order Linked to Requirement

When receiving a PO linked to a requirement, **two transactions** are created automatically:

1. **Receipt Transaction** (R+I)
   - Receives quantity into inventory
   
2. **Issue Transaction** (I+O) - **THIS TRANSACTION**
   - Automatically issues to requirement
   - Quantity = MIN(received_qty, required_qty)

**Important:** You cannot manually issue materials that will be received via linked PO

---

### Over-Issue

**Behavior varies by part type:**

- **Inventory Parts:** System may allow over-issue based on site settings
- **Non-Inventory Parts:** Generally allows over-issue
- **System Warning:** User notified if issuing more than required

---

### Partial Issues

**Allowed:** Issue partial quantities across multiple transactions

**Example:**
- Required: 100 EA
- Issue 1: 50 EA (50% complete)
- Issue 2: 30 EA (80% complete)
- Issue 3: 20 EA (100% complete, requirement closed)

---

## Traceability

### Lot-Tracked Parts

**If traceability starts at issue:**
- System creates new lot numbers for issued quantity
- Distributes total quantity across lot numbers
- User can modify default lot number assignments

**If traceability starts at receipt:**
- System shows existing lot numbers in inventory
- User selects which lot numbers to issue
- Tracks FIFO/FEFO if configured

### Serial-Tracked Parts

- Each serial number issues individually
- Must specify serial number for each piece
- Serialization typically starts at issue for work orders

**Related:** [For Issue of Inventory to a Work Order](../Help-md/VM/For_Issue_of_Inventory_to_a_Work_Order.md)

---

## Cost Accounting

### Material Cost Calculation

```sql
-- Material cost charged to work order
ACT_MATERIAL_COST = QTY * Part_Unit_Cost

-- Part_Unit_Cost determined by:
-- 1. Average cost (if using average costing)
-- 2. Standard cost (if using standard costing)
-- 3. FIFO cost (if using FIFO costing)
```

### Work Order Impact

**Debit:** Work Order WIP Account
**Credit:** Inventory Asset Account

**Work Order Costing:**
- Material cost added to WO actual costs
- Tracked separately from labor/burden
- Used for variance analysis at WO completion

---

## Validation Rules

### Pre-Transaction Validation

| Check | Rule | Error Message |
|-------|------|---------------|
| Part exists | Part must exist in PART table | "Part not found" |
| Work order exists | WO must exist and be Released | "Work order not found or not released" |
| Requirement exists | Piece No must exist (unless new) | "Material requirement not found" |
| Location valid | Warehouse/Location must exist | "Location not valid" |
| Quantity available | QTY_ON_HAND >= Issue_QTY | "Insufficient quantity" (warning) |

### Post-Transaction Validation

```sql
-- Verify inventory decreased
SELECT QTY_ON_HAND FROM PART WHERE ID = @Part_ID

-- Verify WO material cost increased
SELECT ACT_MATERIAL_COST 
FROM REQUIREMENT 
WHERE WORKORDER_BASE_ID = @WO_Base_ID
  AND PIECE_NO = @Piece_No
```

---

## Issue by Exception

### Batch Processing Alternative

Instead of issuing one requirement at a time, use **Issue by Exception** to:
- View all requirements for a work order
- Issue to multiple requirements simultaneously
- Use auto-mode for automatic warehouse selection
- Process entire work order material list

**See:** [Issue and Return by Exception](../Help-md/VM/VMINVENT_APLfrmIssue.md)

---

## SQL Examples

### Find All Issues to Specific Work Order

```sql
SELECT 
    i.TRANSACTION_ID,
    i.TRANSACTION_DATE,
    i.PART_ID,
    i.OPERATION_SEQ_NO,
    i.REQ_PIECE_NO,
    i.QTY,
    i.WAREHOUSE_ID,
    i.LOCATION_ID,
    i.ACT_MATERIAL_COST,
    r.CALC_QTY AS Required_Qty,
    r.DESCRIPTION AS Requirement_Description
FROM INVENTORY_TRANS i
INNER JOIN REQUIREMENT r
  ON r.WORKORDER_BASE_ID = i.WORKORDER_BASE_ID
  AND r.WORKORDER_LOT_ID = i.WORKORDER_LOT_ID
  AND r.WORKORDER_SPLIT_ID = i.WORKORDER_SPLIT_ID
  AND r.OPERATION_SEQ_NO = i.OPERATION_SEQ_NO
  AND r.PIECE_NO = i.REQ_PIECE_NO
WHERE i.TYPE = 'O' 
  AND i.CLASS = 'I'
  AND i.WORKORDER_BASE_ID = '1234567'
ORDER BY i.TRANSACTION_DATE;
```

### Calculate Total Issued vs Required

```sql
SELECT 
    r.WORKORDER_BASE_ID,
    r.PART_ID,
    r.CALC_QTY AS Required,
    ISNULL(SUM(CASE 
        WHEN i.TYPE = 'O' AND i.CLASS = 'I' THEN i.QTY  -- Issues
        WHEN i.TYPE = 'I' AND i.CLASS = 'I' THEN -i.QTY  -- Issue Returns
    END), 0) AS Total_Issued,
    r.CALC_QTY - ISNULL(SUM(CASE 
        WHEN i.TYPE = 'O' AND i.CLASS = 'I' THEN i.QTY 
        WHEN i.TYPE = 'I' AND i.CLASS = 'I' THEN -i.QTY 
    END), 0) AS Remaining
FROM REQUIREMENT r
LEFT JOIN INVENTORY_TRANS i
  ON i.WORKORDER_BASE_ID = r.WORKORDER_BASE_ID
  AND i.WORKORDER_LOT_ID = r.WORKORDER_LOT_ID
  AND i.WORKORDER_SPLIT_ID = r.WORKORDER_SPLIT_ID
  AND i.OPERATION_SEQ_NO = r.OPERATION_SEQ_NO
  AND i.REQ_PIECE_NO = r.PIECE_NO
  AND i.CLASS = 'I'  -- Issue transactions only
WHERE r.WORKORDER_BASE_ID = '1234567'
GROUP BY r.WORKORDER_BASE_ID, r.PART_ID, r.CALC_QTY, r.PIECE_NO
ORDER BY r.OPERATION_SEQ_NO, r.PIECE_NO;
```

---

## Related Transactions

| Transaction | Relationship |
|-------------|--------------|
| [Issue Return](Issue_Return_to_Stockroom.md) | Reverses this transaction (I+I) |
| [Receipt by Work Order](Receipt_by_Work_Order.md) | Receives finished goods (R+I) |
| [Purchase Receipt](../Help-md/VM/Inventory_Transactions.md) | Auto-creates issue if linked (R+I then I+O) |

---

## Troubleshooting

### Common Issues

**"Cannot issue to closed work order"**
- Work order status must be Released or Started
- Check `WORK_ORDER.STATUS`

**"Insufficient quantity"**
- Warning only, may proceed based on site settings
- Check `PART.QTY_ON_HAND` and `PART.QTY_AVAILABLE`

**"Material requirement not found"**
- Verify piece number exists for work order
- Check operation sequence number matches
- Verify subordinate WO sub ID if applicable

**"Quantity on Hand decreased incorrectly"**
- Verify CLASS='I' and TYPE='O'
- Check for duplicate transactions
- Review transaction history

---

## See Also

- [Inventory Transaction Entry Index](Inventory_Transaction_Entry_Index.md)
- [Issue Return to Stockroom](Issue_Return_to_Stockroom.md)
- [Material Requirements Flow](materiall_requirements_flow.md)
- [VMINVENTfrmIssue](../Help-md/VM/VMINVENTfrmIssue.md)
