# Using Inventory Transaction Entry

## Overview

Use Inventory Transaction Entry for six basic operations that manage material flow through your facility. Each operation maps to specific database transaction classes and types that affect Quantity on Hand (QOH).

---

## Six Basic Operations

### 1. Receipt of Fabricated Material into Inventory

Receive finished goods from work orders or parts directly into inventory.

**Operation Variants:**
- Receipt by Work Order - Receive completed work order output
- Receipt by Part - Receive materials by part number

**Database Schema:**
- **CLASS**: `R` (Released)
- **TYPE**: `I` (In)
- **Effect on QOH**: `+1 * QTY` (Increases inventory)

**Business Context:**
- Receiving finished goods from manufacturing
- Moving completed products from WIP to finished goods inventory
- Updates work order completion status

**Key Fields:**
- `WORKORDER_BASE_ID`, `WORKORDER_LOT_ID`, `WORKORDER_SPLIT_ID`
- `WAREHOUSE_ID`, `LOCATION_ID`
- `QTY` (quantity being received)

**Related Help Files:**
- [Receiving Materials by Work Order](Receiving_Materials_Into_Inventory.md)
- [Receiving by Part](Receiving_by_Part.md)

---

### 2. Issue Material to a Work Order

Issue raw materials from inventory to work order requirements for production.

**Operation Details:**
- [Issue Material to Work Order](Issue_Material_to_Work_Order.md)

**Database Schema:**
- **CLASS**: `I` (Issue)
- **TYPE**: `O` (Out)
- **Effect on QOH**: `-1 * QTY` (Decreases inventory)

**Business Context:**
- Relieving inventory for production consumption
- Charging raw materials to work orders
- Fulfilling material requirements for operations

**Key Fields:**
- `WORKORDER_BASE_ID`, `WORKORDER_LOT_ID`, `WORKORDER_SPLIT_ID`, `WORKORDER_SUB_ID`
- `OPERATION_SEQ_NO` (operation requiring the material)
- `REQ_PIECE_NO` (material requirement card)
- `WAREHOUSE_ID`, `LOCATION_ID`
- `QTY` (quantity being issued)
- `ISSUE_REAS_ID` (reason code for issue)

**Process Flow:**
1. Print Work Order Pick List
2. Locate material in warehouse
3. Move material to production area
4. Scan/enter transaction to relieve inventory
5. Material charged to work order

**Related Help Files:**
- [Issuing Materials to Work Orders](VMINVENTfrmIssue.md)
- [Issue and Return by Exception](VMINVENT_APLfrmIssue.md)

---

### 3. Adjust Material Into Inventory

Manually add material to inventory for corrections, found items, or adjustments.

**Database Schema:**
- **CLASS**: `A` (Adjust)
- **TYPE**: `I` (In)
- **Effect on QOH**: `+1 * QTY` (Increases inventory)

**Business Context:**
- Inventory corrections (count adjustments)
- Found inventory
- Initial inventory setup
- Cycle count adjustments (positive)

**Key Fields:**
- `PART_ID`
- `WAREHOUSE_ID`, `LOCATION_ID`
- `QTY` (quantity being added)
- `ISSUE_REAS_ID` (reason code for adjustment)
- `GL_ADJ_ACCT_ID` (GL account for adjustment)
- `DESCRIPTION` (explanation of adjustment)

**Related Help Files:**
- [Adjusting Materials](Adjusting_Materials.md)

---

### 4. Receipt Return

Return a material to the work order (reverses a receipt transaction).

**Database Schema:**
- **CLASS**: `R` (Released)
- **TYPE**: `O` (Out)
- **Effect on QOH**: `-1 * QTY` (Decreases inventory)

**Business Context:**
- Returning finished goods back to WIP
- Reversing work order receipts
- Defective finished goods going back for rework
- Moving material from finished goods back to work-in-process

**Key Fields:**
- `WORKORDER_BASE_ID`, `WORKORDER_LOT_ID`, `WORKORDER_SPLIT_ID`
- `WAREHOUSE_ID`, `LOCATION_ID`
- `QTY` (quantity being returned)

**Important Note:**
- **NOT** the same as returning materials to vendor
- This reverses a work order receipt, not a purchase receipt
- Material moves FROM finished goods TO work-in-process

**Related Help Files:**
- [Returning Received Materials](Returning_Received_Materials.md)

---

### 5. Issue Return

Return issued material to the stockroom (reverses an issue transaction).

**Operation Details:**
- [Issue Return to Stockroom](Issue_Return_to_Stockroom.md)

**Database Schema:**
- **CLASS**: `I` (Issue)
- **TYPE**: `I` (In)
- **Effect on QOH**: `+1 * QTY` (Increases inventory)

**Business Context:**
- Returning unused raw materials from work orders
- Excess materials not consumed in production
- Material issued in error
- Defective materials being returned before use

**Key Fields:**
- `WORKORDER_BASE_ID`, `WORKORDER_LOT_ID`, `WORKORDER_SPLIT_ID`, `WORKORDER_SUB_ID`
- `OPERATION_SEQ_NO`
- `REQ_PIECE_NO`
- `WAREHOUSE_ID`, `LOCATION_ID`
- `QTY` (quantity being returned)
- `ISSUE_REAS_ID` (reason code for return)

**Process Flow:**
1. Material previously issued to work order
2. Material not consumed in production
3. Return unused material to stockroom
4. Inventory increased, work order material cost reduced

**Critical Distinction:**
- **Issue Return** (I+I): Materials FROM work order TO inventory (↑ QOH)
- **Receipt Return** (R+O): Materials FROM inventory TO WIP (↓ QOH)

**Related Help Files:**
- [Returning Issued Materials](Returning_Issued_Materials.md)

---

### 6. Adjust Material Out of Inventory

Manually subtract material from inventory for corrections, scrap, or losses.

**Database Schema:**
- **CLASS**: `A` (Adjust)
- **TYPE**: `O` (Out)
- **Effect on QOH**: `-1 * QTY` (Decreases inventory)

**Business Context:**
- Inventory corrections (count adjustments)
- Scrapped materials
- Lost or damaged inventory
- Obsolete inventory write-offs
- Cycle count adjustments (negative)

**Key Fields:**
- `PART_ID`
- `WAREHOUSE_ID`, `LOCATION_ID`
- `QTY` (quantity being removed)
- `ISSUE_REAS_ID` (reason code for adjustment)
- `GL_ADJ_ACCT_ID` (GL account for adjustment)
- `DESCRIPTION` (explanation of adjustment)

**Related Help Files:**
- [Adjusting Materials](Adjusting_Materials.md)

---

## Transaction Matrix Reference

| Operation | UI Label | CLASS | TYPE | Direction | QOH Effect | Scenario # |
|-----------|----------|-------|------|-----------|------------|------------|
| Receipt by WO/Part | Receipt | R | I | In | +QTY | 1 |
| Issue to WO | Issue | I | O | Out | -QTY | 4 |
| Adjust In | Adjust In | A | I | In | +QTY | 3 |
| Receipt Return | Receipt Rtn | R | O | Out | -QTY | 6 |
| Issue Return | Issue Rtn | I | I | In | +QTY | 5 |
| Adjust Out | Adjust Out | A | O | Out | -QTY | 2 |

---

## Multi-Site Considerations

If licensed to use multiple sites:
- Enter inventory transactions on a **site-by-site** basis
- Each transaction is associated with a specific `SITE_ID`
- Cross-site transfers require special transfer transactions

---

## Consignment Inventory

**Important Note:**
- You can **view** consignment inventory transactions in Inventory Transaction Entry
- You **cannot create** consignment transactions here
- Must use dedicated Consignment features for consignment inventory transactions

---

## Common Transaction Workflows

### Purchase Order Receipt to Work Order

When a purchase order line is linked to a work order requirement:

**Two Transactions Are Created Automatically:**

1. **Receipt Transaction** (R+I)
   - Receives material into inventory
   - CLASS='R', TYPE='I'
   - Effect: +QTY

2. **Issue Transaction** (I+O)
   - Immediately issues to work order
   - CLASS='I', TYPE='O'
   - Effect: -QTY

**Net Result:** Material flows through inventory with minimal dwell time

**Related Documentation:**
- [Inventory Transactions](Inventory_Transactions.md)

---

### Work Order Shipment to Customer

When shipping a customer order with linked work order:

**Two Transactions Are Created:**

1. **Receipt Transaction** (R+I)
   - Receives finished goods from work order
   - Closes work order if quantities match
   - CLASS='R', TYPE='I'

2. **Issue Transaction** (I+O)
   - Issues to customer order for shipment
   - CLASS='I', TYPE='O'

**Related Documentation:**
- [Creating Inventory Transactions (Shipping)](Creating_Inventory_Transactions.md)

---

## Related Documentation

### Core Schema Documentation
- [Material Requirements Flow](materiall_requirements_flow.md) - Database schema and CLASS+TYPE definitions
- [Inventory Transaction Terminology Guide](Inventory_Transaction_Terminology_Guide.md) - Complete disambiguation reference
- [Inventory Transactions Flow](Inventory_transactions_flow.md) - Data flow diagrams

### SQL Implementation
- [Inventory_Transactions_Filtered.sql](Inventory_Transactions_Filtered.sql) - Production query examples
- [Inventory - Transactions AI Review.sql](Inventory%20-%20Transactions%20AI%20Review.sql) - Analysis queries

### ERP Help Files
- [Using Inventory Transaction Entry](VMINVENT_APLfrmInventoryEntry.md) - Main transaction entry screen
- [BTS_BI_Basic_Inventory_Transactions](BTS_BI_Basic_Inventory_Transactions.md) - BTS integration
- [Inventory Transaction Costing](Inventory_Transaction_Costing.md) - Cost accounting

---

## Validation and Reconciliation

### QOH Calculation Formula

```sql
SELECT 
    PART_ID,
    SUM(CASE
        WHEN TYPE = 'I' AND CLASS = 'R' THEN 1   -- Receipt
        WHEN TYPE = 'O' AND CLASS = 'I' THEN -1  -- Issue
        WHEN TYPE = 'O' AND CLASS = 'A' THEN -1  -- Adjust Out
        WHEN TYPE = 'I' AND CLASS = 'A' THEN 1   -- Adjust In
        WHEN TYPE = 'I' AND CLASS = 'I' THEN 1   -- Issue Return
        WHEN TYPE = 'O' AND CLASS = 'R' THEN -1  -- Receipt Return
        ELSE 0
    END * QTY) AS Calculated_QOH
FROM INVENTORY_TRANS
GROUP BY PART_ID;
```

### Reconciliation Report

Compare calculated QOH against `PART.QTY_ON_HAND`:

```sql
SELECT 
    p.ID AS PART_ID,
    p.QTY_ON_HAND AS System_QOH,
    ISNULL(t.Calculated_QOH, 0) AS Transaction_QOH,
    p.QTY_ON_HAND - ISNULL(t.Calculated_QOH, 0) AS Variance
FROM PART p
LEFT JOIN (
    SELECT 
        PART_ID,
        SUM(CASE
            WHEN TYPE = 'I' AND CLASS = 'R' THEN 1
            WHEN TYPE = 'O' AND CLASS = 'I' THEN -1
            WHEN TYPE = 'O' AND CLASS = 'A' THEN -1
            WHEN TYPE = 'I' AND CLASS = 'A' THEN 1
            WHEN TYPE = 'I' AND CLASS = 'I' THEN 1
            WHEN TYPE = 'O' AND CLASS = 'R' THEN -1
            ELSE 0
        END * QTY) AS Calculated_QOH
    FROM INVENTORY_TRANS
    GROUP BY PART_ID
) t ON p.ID = t.PART_ID
WHERE p.QTY_ON_HAND <> ISNULL(t.Calculated_QOH, 0);
```

---

## Advanced Features

### Issue by Exception
- Issue materials to multiple requirements simultaneously
- Use Work Order Material Issues table
- Auto-mode for batch processing

**Related:**
- [Issue and Return by Exception](VMINVENT_APLfrmIssue.md)

### Part Traceability
- Lot number tracking
- Serial number tracking
- Trace IDs for material genealogy

**Related:**
- [For Issue of Inventory to a Work Order](For_Issue_of_Inventory_to_a_Work_Order.md) (traceability section)
- [Setting Part Traceability Inventory Transaction Entry](Setting_Part_Traceability_Inventory_Transaction_Entry.md)

### Move Requests
- Material movement requests
- Warehouse management integration
- Pick/put-away workflows

**Related:**
- [Creating Move Requests in Inventory Transaction Entry](Creating_Move_Requests_in_Inventory_Transaction_Entry.md)
- [Move Requests in Inventory Transaction Entry](Move_Requests_in_Inventory_Transaction_Entry.md)

---

## Quick Reference: Transaction Selection Guide

**Need to...**

| Action | Select Transaction Type | Result |
|--------|-------------------------|--------|
| Receive materials from vendor | Receipt (with PO) | Automatic in Purchase Receipt Entry |
| Receive finished goods from production | Receipt by Work Order | R+I transaction |
| Send raw materials to production | Issue | I+O transaction |
| Return unused production materials | Issue Rtn | I+I transaction |
| Fix inventory count (add) | Adjust In | A+I transaction |
| Fix inventory count (subtract) | Adjust Out | A+O transaction |
| Scrap damaged inventory | Adjust Out | A+O transaction |
| Return finished goods to WIP | Receipt Rtn | R+O transaction |
| Return materials to vendor | Receipt Rtn | Done in Purchase Entry |

---

## Navigation Structure (for GitBook)

```
📘 Inventory Transaction Entry
├── 📄 Overview (this page)
├── 📁 Receipt Transactions
│   ├── Receiving Materials by Work Order (Receiving_Materials_Into_Inventory.md)
│   ├── Receiving by Part (Receiving_by_Part.md)
│   └── Receipt by Part Inventory Transaction Entry
├── 📁 Issue Transactions
│   ├── Issue Material to Work Order ✓
│   ├── Issue by Exception (VMINVENT_APLfrmIssue.md)
│   └── Auto-Issue Settings
├── 📁 Return Transactions
│   ├── Issue Return to Stockroom ✓ (Returning_Issued_Materials.md)
│   ├── Receipt Return (Returning_Received_Materials.md)
│   └── Return Transaction Disambiguation ✓
├── 📁 Adjustment Transactions
│   ├── Adjusting Materials (Adjusting_Materials.md)
│   └── For Adjust In or Adjust Out
├── 📁 Advanced Topics
│   ├── Part Traceability
│   ├── Move Requests
│   ├── Multi-Site Transactions
│   └── Consignment Inventory
└── 📁 Reference
    ├── Transaction Matrix
    ├── SQL Examples
    ├── Reconciliation Procedures
    └── Terminology Guide ✓
```

---

## Version History

| Date | Version | Author | Description |
|------|---------|--------|-------------|
| 2025-12-19 | 1.0 | System | Initial index creation for GitBook |

---

## See Also

- [Inventory Transaction Terminology Guide](Inventory_Transaction_Terminology_Guide.md) - Complete terminology reference
- [Material Requirements Flow](materiall_requirements_flow.md) - Database schema details
- [Work Order Operations Flow](work_order_operations_flow.md) - Work order integration
