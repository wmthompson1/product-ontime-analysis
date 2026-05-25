# Inventory Transaction CLASS+TYPE Matrix

This table shows the mapping between UI operations and database CLASS/TYPE field combinations in the INVENTORY_TRANS table.

| Scenario | CLASS | TYPE | Class Tag | Type Tag | Purc Order ID | Work Order | Effect on QOH | UI Label | Notes |
|----------|-------|------|-----------|----------|---------------|------------|---------------|----------|-------|
| 1 | R | I | Released | In | 12345 | | +QTY | Receipt | Purchase order receipt |
| 2 | A | O | Adjust | Out | | | -QTY | Adjust Out | Inventory adjustment (decrease) |
| 3 | A | I | Adjust | In | | | +QTY | Adjust In | Inventory adjustment (increase) |
| 4 | I | O | Issue | Out | | 565656 | -1 * QTY | Issue | Issue material to work order |
| 5 | I | I | Issue | In | | 565656 | +1 * QTY | Issue Rtn | Return issued material to stockroom |

## Summary

### CLASS Values
- **R** = Released (receipt from purchase order)
- **A** = Adjust (inventory adjustments)
- **I** = Issue (work order material movements)

### TYPE Values
- **I** = In (increases QOH - Quantity on Hand)
- **O** = Out (decreases QOH - Quantity on Hand)

### Scenarios
1. **Receipt by Work Order (R+I)**: Receiving finished goods into inventory from production
2. **Adjust Out (A+O)**: Manual decrease of inventory (scrap, loss, etc.)
3. **Adjust In (A+I)**: Manual increase of inventory (found material, correction, etc.)
4. **Issue Material (I+O)**: Issue raw materials to work order for production
5. **Issue Return (I+I)**: Return unused materials from work order back to stockroom

## Database Schema

```sql
-- Simplified INVENTORY_TRANS structure
CREATE TABLE INVENTORY_TRANS (
    TRANS_NO INT PRIMARY KEY,
    CLASS CHAR(1) NOT NULL,     -- R, A, or I
    TYPE CHAR(1) NOT NULL,      -- I or O
    PART_ID VARCHAR(30),
    QUANTITY DECIMAL(18,4),
    WORK_ORDER VARCHAR(30),
    PURC_ORDER_ID VARCHAR(30),
    -- ... other fields
);
```

## Related Documentation
- [Material Requirements Flow](materiall_requirements_flow.md) - Detailed CLASS+TYPE definitions
- [Inventory Transaction Terminology Guide](Inventory_Transaction_Terminology_Guide.md) - Complete terminology reference
- [Issue Material to Work Order](Issue_Material_to_Work_Order.md) - I+O operation guide
- [Issue Return to Stockroom](Issue_Return_to_Stockroom.md) - I+I operation guide
