# Inventory Transaction Terminology Guide

## Purpose
This document disambiguates inventory transaction terminology between the **Visual ERP User Interface**, **Help Documentation**, and the **Database Schema**.

---

## Transaction Type Disambiguation

### UI Transaction Types vs. Database CLASS+TYPE

The Visual ERP system uses different terminology in the user interface compared to the underlying database schema. This table maps the relationship:

| UI Transaction Name | Database CLASS | Database TYPE | Direction | Effect on QOH | Common Usage |
|---------------------|----------------|---------------|-----------|---------------|--------------|
| **Receipt** (to Inventory) | R | I | In | `+1 * QTY` | Receiving purchased materials or finished goods from work orders |
| **Issue** (to Work Order) | I | O | Out | `-1 * QTY` | Issuing raw materials to work orders for production |
| **Adjust In** | A | I | In | `+1 * QTY` | Manual inventory increase (corrections, found inventory) |
| **Adjust Out** | A | O | Out | `-1 * QTY` | Manual inventory decrease (scrapped, lost, damaged) |
| **Issue Return** (Issue Rtn) | I | I | In | `+1 * QTY` | Returning unused materials from work order back to stockroom |
| **Receipt Return** | R | O | Out | `-1 * QTY` | Returning received materials to vendor or reversing WO receipt |

---

## Database Schema Reference

### Scenario Matrix

From the attached specification and database analysis:

| Scenario | Class | Type | Class Tag | Type Tag | Effect on QOH | Database Query Pattern |
|----------|-------|------|-----------|----------|---------------|------------------------|
| 1 | R | I | Released | In | `+1 * QTY` | `TYPE = 'I' AND CLASS = 'R'` |
| 2 | A | O | Adjust | Out | `-1 * QTY` | `TYPE = 'O' AND CLASS = 'A'` |
| 3 | A | I | Adjust | In | `+1 * QTY` | `TYPE = 'I' AND CLASS = 'A'` |
| 4 | I | O | Issue | Out | `-1 * QTY` | `TYPE = 'O' AND CLASS = 'I'` |
| 5 | I | I | Issue | In | `+1 * QTY` | `TYPE = 'I' AND CLASS = 'I'` |

**Additional Scenario (not in original spec):**
| Scenario 6 | R | O | Released | Out | `-1 * QTY` | `TYPE = 'O' AND CLASS = 'R'` |

---

## Key Terminology by Context

### 1. Raw Material Issuance to Work Orders

**User Interface Terms:**
- "**Issue**" - The transaction type selected in Inventory Transaction Entry
- "**Issue to Work Order**" - The action of relieving inventory and charging materials to production

**Database Values:**
- CLASS = `'I'` (Issue)
- TYPE = `'O'` (Out)
- Effect: **Decreases** Quantity on Hand by QTY

**Help File References:**
- "Issue Material to a work order" ([VMINVENTfrmIssue.md](VMINVENTfrmIssue.md))
- "Materials issued to Work Orders" ([Issue_to_a_Work_Order.md](Issue_to_a_Work_Order.md))
- "Issuing Materials to Work Orders" (main procedure)

**Business Process:**
1. Work Order Pick List is printed
2. Material is located in warehouse
3. Material is moved to production area
4. Material is scanned/entered to relieve inventory and apply to Work Order
5. Transaction creates: CLASS='I', TYPE='O'

**Related Fields:**
- `WORKORDER_BASE_ID`, `WORKORDER_LOT_ID`, `WORKORDER_SPLIT_ID`, `WORKORDER_SUB_ID`
- `OPERATION_SEQ_NO` - The operation requiring the material
- `REQ_PIECE_NO` - The material requirement card

---

### 2. Return of Issued Materials (Issue Return)

**User Interface Terms:**
- "**Issue Rtn**" or "**Issue Return**" - The transaction type in the UI
- "Returning issued materials" - The action description

**Database Values:**
- CLASS = `'I'` (Issue)
- TYPE = `'I'` (In)
- Effect: **Increases** Quantity on Hand by QTY

**Help File References:**
- "Returning Issued Materials" ([Returning_Issued_Materials.md](Returning_Issued_Materials.md))
- "For Return of Issued Material from a Work Order" ([For_Return_of_Issued_Material_from_a_Work_Order.md](For_Return_of_Issued_Material_from_a_Work_Order.md))

**Business Process:**
1. Material previously issued to work order
2. Material returned unused to stockroom
3. Reverses the original issue action
4. Transaction creates: CLASS='I', TYPE='I'

**Important Distinction:**
- **NOT** the same as "Receipt Return" (which is CLASS='R', TYPE='O')
- Issue Return = returning materials **TO** inventory **FROM** work order
- Receipt Return = returning materials **TO** vendor or reversing WO receipt

---

### 3. Receipt Transactions

#### 3a. Receipt to Inventory (from Purchase Order)

**User Interface Terms:**
- "**Receipt**" - Transaction type
- "Receipt to Inventory" - Receiving purchased goods

**Database Values:**
- CLASS = `'R'` (Released/Receipt)
- TYPE = `'I'` (In)
- Effect: **Increases** Quantity on Hand

**Related Fields:**
- `PURC_ORDER_ID`, `PURC_ORDER_LINE_NO`

#### 3b. Receipt from Work Order (Finished Goods)

**User Interface Terms:**
- "**Receipt by Work Order**" or "**Receipt by Part**"
- "Receiving Materials Into Inventory"

**Database Values:**
- CLASS = `'R'` (Released/Receipt)
- TYPE = `'I'` (In)
- Effect: **Increases** Quantity on Hand

**Related Fields:**
- `WORKORDER_BASE_ID`, `WORKORDER_LOT_ID`, `WORKORDER_SPLIT_ID`

---

### 4. Receipt Return Transactions

**User Interface Terms:**
- "**Receipt Return**" or "**Receipt Rtn**"
- "Return to Vendor" (for purchase returns)

**Database Values:**
- CLASS = `'R'` (Released/Receipt)
- TYPE = `'O'` (Out)
- Effect: **Decreases** Quantity on Hand

**Two Contexts:**
1. **Vendor Returns**: Material returned to supplier
2. **WO Receipt Reversal**: Moving finished goods back to work-in-process

---

## Common Confusion Points

### ⚠️ Disambiguation Needed

#### "Return" can mean TWO different things:

1. **Issue Return** (CLASS='I', TYPE='I')
   - Returns material **TO** inventory
   - **FROM** work order
   - **Increases** QOH
   - Unused raw materials going back to stockroom

2. **Receipt Return** (CLASS='R', TYPE='O')
   - Returns material **FROM** inventory
   - **TO** vendor or back to WIP
   - **Decreases** QOH
   - Defective goods, vendor returns, or receipt reversals

#### Visual Representation:

```
ISSUE RETURN (I+I):
   Work Order ──────> Inventory
   (returning unused raw materials)
   Effect: +QTY

RECEIPT RETURN (R+O):
   Inventory ──────> Vendor/WIP
   (returning defective or reversing receipt)
   Effect: -QTY
```

---

## Purchase Receipt Linked to Work Order

**Special Case**: When receiving a purchase order linked to a work order requirement:

**Two Transactions Are Created:**

1. **Receipt Transaction** (R+I)
   - Receives quantity into inventory
   - CLASS='R', TYPE='I'
   - Effect: +QTY

2. **Issue Transaction** (I+O)
   - Immediately issues to work order requirement
   - CLASS='I', TYPE='O'
   - Effect: -QTY

**Net Effect**: Material flows through inventory but may have zero net impact on QOH if quantities match.

---

## SQL Query Examples

### Calculate Net Effect on QOH

```sql
SELECT 
    TRANSACTION_ID,
    PART_ID,
    CLASS,
    TYPE,
    QTY,
    CASE
        WHEN TYPE = 'I' AND CLASS = 'R' THEN 1   -- Receipt
        WHEN TYPE = 'O' AND CLASS = 'I' THEN -1  -- Issue
        WHEN TYPE = 'O' AND CLASS = 'A' THEN -1  -- Adjust Out
        WHEN TYPE = 'I' AND CLASS = 'A' THEN 1   -- Adjust In
        WHEN TYPE = 'I' AND CLASS = 'I' THEN 1   -- Issue Return
        WHEN TYPE = 'O' AND CLASS = 'R' THEN -1  -- Receipt Return
        ELSE 0
    END * QTY AS Effect_on_QOH,
    CASE
        WHEN TYPE = 'I' AND CLASS = 'R' THEN 'Receipt to Inventory'
        WHEN TYPE = 'O' AND CLASS = 'I' THEN 'Issue to Work Order'
        WHEN TYPE = 'O' AND CLASS = 'A' THEN 'Adjust Out'
        WHEN TYPE = 'I' AND CLASS = 'A' THEN 'Adjust In'
        WHEN TYPE = 'I' AND CLASS = 'I' THEN 'Issue Return'
        WHEN TYPE = 'O' AND CLASS = 'R' THEN 'Receipt Return'
        ELSE 'Unknown'
    END AS Transaction_Description
FROM INVENTORY_TRANS
WHERE PART_ID = 'YOUR-PART-ID'
ORDER BY TRANSACTION_DATE;
```

### Find All Issues to Work Orders

```sql
SELECT 
    TRANSACTION_ID,
    PART_ID,
    WORKORDER_BASE_ID,
    WORKORDER_LOT_ID,
    OPERATION_SEQ_NO,
    REQ_PIECE_NO,
    QTY,
    TRANSACTION_DATE
FROM INVENTORY_TRANS
WHERE TYPE = 'O' 
  AND CLASS = 'I'  -- Issue Out
ORDER BY TRANSACTION_DATE DESC;
```

### Find All Issue Returns (Materials Returned from WO)

```sql
SELECT 
    TRANSACTION_ID,
    PART_ID,
    WORKORDER_BASE_ID,
    WORKORDER_LOT_ID,
    QTY,
    TRANSACTION_DATE
FROM INVENTORY_TRANS
WHERE TYPE = 'I' 
  AND CLASS = 'I'  -- Issue Return
ORDER BY TRANSACTION_DATE DESC;
```

---

## Related Documentation

### Internal Documentation
- [Material Requirements Flow](materiall_requirements_flow.md) - Core class/type definitions
- [Inventory Transactions Flow](Inventory_transactions_flow.md) - Data flow diagrams
- [Inventory_Transactions_Filtered.sql](Inventory_Transactions_Filtered.sql) - SQL implementation

### ERP Help Files

- [VMINVENTfrmIssue.md](../../../Help-md/VM/VMINVENTfrmIssue.md) - Issuing materials to work orders
- [Returning_Issued_Materials.md](../../../Help-md/VM/Returning_Issued_Materials.md) - Issue return procedures
- [For_Issue_of_Inventory_to_a_Work_Order.md](../../../Help-md/VM/For_Issue_of_Inventory_to_a_Work_Order.md) - Issue process details
- [For_Return_of_Issued_Material_from_a_Work_Order.md](../../../Help-md/VM/For_Return_of_Issued_Material_from_a_Work_Order.md) - Return process
- [Inventory_Transactions.md](../../../Help-md/VM/Inventory_Transactions.md) - Overview
- [Material_Issues.md](../../../Help-md/VM/Material_Issues.md) - Viewing work order issues

---

## Quick Reference Card

| Want to... | UI Action | CLASS | TYPE | QOH |
|------------|-----------|-------|------|-----|
| Receive purchased materials | Receipt | R | I | ↑ |
| Receive finished goods from WO | Receipt by WO | R | I | ↑ |
| Issue raw materials to WO | Issue | I | O | ↓ |
| Return unused materials from WO | Issue Rtn | I | I | ↑ |
| Return materials to vendor | Receipt Rtn | R | O | ↓ |
| Add inventory (correction) | Adjust In | A | I | ↑ |
| Remove inventory (scrap/loss) | Adjust Out | A | O | ↓ |

**Legend:** ↑ = Increases QOH | ↓ = Decreases QOH

---

## Version History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2025-12-18 | 1.0 | System | Initial creation - Disambiguation of inventory transaction terminology |

---

## Notes

- Always verify transaction CLASS and TYPE values in queries
- The UI may show "Issue Rtn" but database stores CLASS='I', TYPE='I'
- When discussing with users, use UI terminology
- When writing SQL, use database CLASS/TYPE codes
- The term "Return" is context-dependent - always specify Issue Return vs Receipt Return
