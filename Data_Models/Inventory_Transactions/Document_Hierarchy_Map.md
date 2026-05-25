# Inventory Transaction Entry - Documentation Hierarchy

## Top Level Page

**File:** `VMINVENT_APLfrmInventoryEntry.md`  
**Header:** "Using Inventory Transaction Entry"  
**Location:** `Documentation/Help-md/VM/VMINVENT_APLfrmInventoryEntry.md`

---

## Document Hierarchy Map

### Level 1: Main Entry Point
```
VMINVENT_APLfrmInventoryEntry.md
└── "Using Inventory Transaction Entry"
```

### Level 2: Six Basic Operations (Linked from Main Page)

#### 1. Receipt of Fabricated Material into Inventory

**Two Variants:**

**1a. Receipt by Work Order**
- **Link Text:** "by work order"
- **Target File:** `Receiving_Materials_Into_Inventory.md`
- **Header:** "Receiving Materials by Work Order"
- **Database:** CLASS='R', TYPE='I' (Scenario 1)

**1b. Receipt by Part**
- **Link Text:** "by part"
- **Target File:** `Receiving_by_Part.md`
- **Header:** "Receiving by Part"
- **Database:** CLASS='R', TYPE='I' (Scenario 1)

---

#### 2. Issue Material to a Work Order

- **Link Text:** "Issue Material to a work order."
- **Target File:** `VMINVENTfrmIssue.md`
- **Header:** "Issuing Materials to Work Orders"
- **Database:** CLASS='I', TYPE='O' (Scenario 4)
- **Our Detail Doc:** `Issue_Material_to_Work_Order.md` ✓

**Sub-links from VMINVENTfrmIssue.md:**
- Links to: `VMINVENT_APLfrmIssue.md` (Issue By Exception feature)

---

#### 3. Adjust Material Into Inventory

- **Link Text:** "Adjust material into inventory (add material to inventory)."
- **Target File:** `Adjusting_Materials.md`
- **Header:** "Adjusting Materials"
- **Database:** CLASS='A', TYPE='I' (Scenario 3)

---

#### 4. Receipt Return

- **Link Text:** "Receipt return (returns a material to the work order)"
- **Target File:** `Returning_Received_Materials.md`
- **Header:** "Returning Received Materials"
- **Database:** CLASS='R', TYPE='O' (Scenario 6)

---

#### 5. Issue Return

- **Link Text:** "Issue return (return an issued material to the stockroom)"
- **Target File:** `Returning_Issued_Materials.md`
- **Header:** "Returning Issued Materials"
- **Database:** CLASS='I', TYPE='I' (Scenario 5)
- **Our Detail Doc:** `Issue_Return_to_Stockroom.md` ✓

---

#### 6. Adjust Material Out of Inventory

- **Link Text:** "Adjust material out of inventory (subtracts from inventory)"
- **Target File:** `Adjusting_Materials.md`
- **Header:** "Adjusting Materials" (same file as #3)
- **Database:** CLASS='A', TYPE='O' (Scenario 2)

---

## Complete File Tree Structure

```
📘 Inventory Transaction Entry Documentation
│
├── LEVEL 0: Index/Landing Pages
│   ├── Inventory_Transaction_Entry_Index.md (our GitBook index)
│   └── Inventory_Transaction_Terminology_Guide.md (our disambiguation guide)
│
├── LEVEL 1: Main Entry Point (ERP Help)
│   └── VMINVENT_APLfrmInventoryEntry.md ⭐ TOP LEVEL
│       └── "Using Inventory Transaction Entry"
│
├── LEVEL 2: Six Operations (ERP Help + Our Details)
│   │
│   ├── 📁 Operation 1: Receipt of Fabricated Material
│   │   ├── Receiving_Materials_Into_Inventory.md (by work order)
│   │   ├── Receiving_by_Part.md (by part)
│   │   └── Receipt_by_Part_Inventory_Transaction_Entry.md
│   │
│   ├── 📁 Operation 2: Issue Material to WO
│   │   ├── VMINVENTfrmIssue.md (ERP help)
│   │   ├── Issue_Material_to_Work_Order.md ✓ (our detail doc)
│   │   └── VMINVENT_APLfrmIssue.md (Issue by Exception)
│   │
│   ├── 📁 Operation 3: Adjust In
│   │   ├── Adjusting_Materials.md (ERP help)
│   │   └── For_Adjust_In_or_Adjust_Out_from_Inventory.md
│   │
│   ├── 📁 Operation 4: Receipt Return
│   │   ├── Returning_Received_Materials.md (ERP help)
│   │   └── For_Receipt_Return_of_Finished_Goods.md
│   │
│   ├── 📁 Operation 5: Issue Return
│   │   ├── Returning_Issued_Materials.md (ERP help)
│   │   ├── Issue_Return_to_Stockroom.md ✓ (our detail doc)
│   │   ├── For_Return_of_Issued_Material_from_a_Work_Order.md
│   │   └── Issue_Returning_Piece_Tracked_Parts_to_Inventory.md
│   │
│   └── 📁 Operation 6: Adjust Out
│       ├── Adjusting_Materials.md (same as Operation 3)
│       └── For_Adjust_In_or_Adjust_Out_from_Inventory.md
│
├── LEVEL 3: Supporting Topics
│   ├── Creating_Inventory_Transactions.md (from Shipping Entry)
│   ├── Inventory_Transactions.md (from Purchase Receipt)
│   ├── Move_Requests_in_Inventory_Transaction_Entry.md
│   ├── Creating_Move_Requests_in_Inventory_Transaction_Entry.md
│   └── For_Issue_of_Inventory_to_a_Work_Order.md (traceability)
│
└── LEVEL 4: Database/Technical Documentation
    ├── materiall_requirements_flow.md (schema definitions)
    ├── Inventory_transactions_flow.md (data flow)
    ├── Inventory_Transactions_Filtered.sql (queries)
    └── Inventory - Transactions AI Review.sql
```

---

## Link Mapping for GitBook

### Recommended GitBook Page Structure

**1. Landing Page:**
- **Title:** "Inventory Transaction Entry"
- **File:** Use `Inventory_Transaction_Entry_Index.md` as template
- **Link to:** `VMINVENT_APLfrmInventoryEntry.md` (actual ERP help)

**2. Six Operation Pages (one per transaction type):**

Each should link to:
- ERP help file (existing .md)
- Our detailed documentation (where created)
- Related database schema docs

---

## Navigation Links (Corrected for GitBook)

### From Index Page to ERP Help Files:

```markdown
## Six Basic Operations

### 1. Receipt of Fabricated Material into Inventory

**ERP Help Files:**
- [Receipt by Work Order](../Help-md/VM/Receiving_Materials_Into_Inventory.md)
- [Receipt by Part](../Help-md/VM/Receiving_by_Part.md)
- [Receipt by Part Inventory Transaction Entry](../Help-md/VM/Receipt_by_Part_Inventory_Transaction_Entry.md)

**Database:** CLASS='R', TYPE='I' | Effect: +QTY

---

### 2. Issue Material to a Work Order

**ERP Help Files:**
- [Issuing Materials to Work Orders](../Help-md/VM/VMINVENTfrmIssue.md)
- [Issue by Exception](../Help-md/VM/VMINVENT_APLfrmIssue.md)

**Detailed Documentation:**
- [Issue Material to Work Order - Complete Guide](Issue_Material_to_Work_Order.md) ✓

**Database:** CLASS='I', TYPE='O' | Effect: -QTY

---

### 3. Adjust Material Into Inventory

**ERP Help Files:**
- [Adjusting Materials](../Help-md/VM/Adjusting_Materials.md)
- [For Adjust In or Adjust Out from Inventory](../Help-md/VM/For_Adjust_In_or_Adjust_Out_from_Inventory.md)

**Database:** CLASS='A', TYPE='I' | Effect: +QTY

---

### 4. Receipt Return (Return to Work Order)

**ERP Help Files:**
- [Returning Received Materials](../Help-md/VM/Returning_Received_Materials.md)
- [For Receipt Return of Finished Goods](../Help-md/VM/For_Receipt_Return_of_Finished_Goods.md)

**Database:** CLASS='R', TYPE='O' | Effect: -QTY

---

### 5. Issue Return (Return to Stockroom)

**ERP Help Files:**
- [Returning Issued Materials](../Help-md/VM/Returning_Issued_Materials.md)
- [For Return of Issued Material from a Work Order](../Help-md/VM/For_Return_of_Issued_Material_from_a_Work_Order.md)

**Detailed Documentation:**
- [Issue Return to Stockroom - Complete Guide](Issue_Return_to_Stockroom.md) ✓

**Database:** CLASS='I', TYPE='I' | Effect: +QTY

---

### 6. Adjust Material Out of Inventory

**ERP Help Files:**
- [Adjusting Materials](../Help-md/VM/Adjusting_Materials.md) (same as #3)

**Database:** CLASS='A', TYPE='O' | Effect: -QTY
```

---

## Cross-Reference: UI Screenshot to Files

From the attached screenshot showing the "Using Inventory Transaction Entry" page:

| Screenshot Link | Actual Filename | Our Doc |
|-----------------|-----------------|---------|
| "by work order" | `Receiving_Materials_Into_Inventory.md` | - |
| "by part" | `Receiving_by_Part.md` | - |
| "Issue Material to a work order" | `VMINVENTfrmIssue.md` | `Issue_Material_to_Work_Order.md` ✓ |
| "Adjust material into inventory" | `Adjusting_Materials.md` | - |
| "Receipt return" | `Returning_Received_Materials.md` | - |
| "Issue return" | `Returning_Issued_Materials.md` | `Issue_Return_to_Stockroom.md` ✓ |
| "Adjust material out of inventory" | `Adjusting_Materials.md` | - |

---

## Files We Created

✓ **`Inventory_Transaction_Entry_Index.md`** - GitBook landing page  
✓ **`Inventory_Transaction_Terminology_Guide.md`** - Disambiguation reference  
✓ **`Issue_Material_to_Work_Order.md`** - Detailed guide for Scenario 4  
✓ **`Issue_Return_to_Stockroom.md`** - Detailed guide for Scenario 5  
✓ **`materiall_requirements_flow.md`** - Updated schema definitions  

---

## Next Steps for Complete GitBook

### Option 1: Create Additional Detail Pages

Create detailed documentation for operations 1, 3, 4, and 6:
- `Receipt_by_Work_Order_Detail.md`
- `Receipt_by_Part_Detail.md`
- `Adjust_Material_In_Detail.md`
- `Adjust_Material_Out_Detail.md`
- `Receipt_Return_Detail.md`

### Option 2: Link Directly to ERP Help

Use existing ERP help files as-is and supplement with:
- Database schema notes
- SQL examples
- Workflow diagrams

---

## Recommended GitBook TOC

```yaml
- Inventory Transaction Entry:
  - Overview: Inventory_Transaction_Entry_Index.md
  - ERP Main Help: ../Help-md/VM/VMINVENT_APLfrmInventoryEntry.md
  
  - Receipt Transactions:
    - Receipt by Work Order: ../Help-md/VM/Receiving_Materials_Into_Inventory.md
    - Receipt by Part: ../Help-md/VM/Receiving_by_Part.md
  
  - Issue Transactions:
    - Issue to Work Order: Issue_Material_to_Work_Order.md
    - Issue by Exception: ../Help-md/VM/VMINVENT_APLfrmIssue.md
    - ERP Help: ../Help-md/VM/VMINVENTfrmIssue.md
  
  - Return Transactions:
    - Issue Return (to Stockroom): Issue_Return_to_Stockroom.md
    - Receipt Return (to WIP): ../Help-md/VM/Returning_Received_Materials.md
    - ERP Help - Issue Return: ../Help-md/VM/Returning_Issued_Materials.md
  
  - Adjustment Transactions:
    - Adjusting Materials: ../Help-md/VM/Adjusting_Materials.md
    - Adjust In/Out Details: ../Help-md/VM/For_Adjust_In_or_Adjust_Out_from_Inventory.md
  
  - Reference:
    - Terminology Guide: Inventory_Transaction_Terminology_Guide.md
    - Schema Definitions: materiall_requirements_flow.md
    - Data Flow: Inventory_transactions_flow.md
```

---

## Summary

**Top-Level File:** `VMINVENT_APLfrmInventoryEntry.md`  
**Location:** `Documentation/Help-md/VM/`  
**Our Index:** `Inventory_Transaction_Entry_Index.md`  
**Our Detailed Docs:** 2 of 6 operations completed (Issues)  
**Linking Strategy:** Hybrid - use ERP help where it exists, supplement with our detailed guides
