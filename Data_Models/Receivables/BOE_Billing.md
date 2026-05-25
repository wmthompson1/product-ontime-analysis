# Special Fees Origin - BOE Billing MFG Report

Based on the SQL code in [`SQL_Reports/BOE Billing/BOE_Billing_MFG.sql`](SQL_Reports/BOE BOE_Billing_MFG.sql ), **Special Fees** originate from **two distinct sources**:

---

## 1. Service Cost Special Fee (`@SPECIAL` variable)

**Special fee = Sum of 1. `Special`, and 2. Min Lot Fee if applicable**

**Condition:**
```sql
WHEN WO.ACT_SERVICE_COST > 0 THEN @SPECIAL
```

**Source:**
- **Variable:** `@SPECIAL` (declared at line 42)
- **Database:** `[sql-bi-1].LIVESupplemental.dbo.[BOE_Billing_Charges]`
- **Filter:** `WHERE [REPORT] = 'usp_BOE_BILLING_MFG'`
- **Column:** `SPECIAL`

**Business Rule:**
- If the Work Order (`WO.ACT_SERVICE_COST`) has **any service cost recorded** (value > 0), apply the special fee from the `BOE_Billing_Charges` configuration table
- This is a **configured rate** stored in the supplemental database, not a calculated value

**Declaration (line 42):**
```sql
DECLARE @SPECIAL FLOAT = (
    SELECT SPECIAL 
    FROM [sql-bi-1].LIVESupplemental.dbo.[BOE_Billing_Charges] 
    WHERE [REPORT] = 'usp_BOE_BILLING_MFG'
)
```

---

## 2. Plus Minimum Lot Special Fee (Fixed $175) if applicable

**Condition:**
```sql
WHEN TOTAL_SHIPPED_QTY < [Batch Qty] 
     AND CB.[Description] LIKE 'Stanchion%' 
THEN 175
```

**Source:**
- **Hardcoded Value:** `$175.00`
- **Reference Data:** `[sql-bi-1].LIVESupplemental.dbo.[BOE_Stanchion_Cargo_Bay]` (aliased as `CB`)

**Business Rule:**
- Applied when **Stanchion parts** are shipped in quantities **less than the standard batch size**
- This is a **minimum lot charge** for small-quantity Stanchion orders
- Documented in the `COMMENTS` field (lines 101-112):

```sql
CASE
    WHEN CB.[Description] LIKE 'Stanchion%' 
         AND COL.TOTAL_SHIPPED_QTY < 3.00
    THEN 'QTY ' + CAST(CAST(TOTAL_SHIPPED_QTY AS INT) AS NVARCHAR) 
         + ',MIN LOT,'
    ELSE '' 
END
```

### Special Fees (BOE Billing)
**Definition:** Additional charges applied to Boeing (BOE609) manufacturing orders based on service costs or minimum lot sizes  
**Components:**
1. **Service Cost Fee:** Variable rate applied when work order has external service costs
2. **Minimum Lot Fee:** Fixed $175 charge for Stanchion parts shipped below batch quantity (typically < 3 units)  
**Data Source:** `usp_BOE_BILLING_MFG` stored procedure  
**Configuration:** `[sql-bi-1].LIVESupplemental.dbo.BOE_Billing_Charges` (rates), `BOE_Stanchion_Cargo_Bay` (thresholds)  
**Related Terms:** Service Cost, Batch Quantity, Stanchion Parts



| 1.) |  |  |  |
| :---- | :---- | :---- | :---- |
| REPORT | DESCRIPTION | CHARGE | @SPECIAL |
| usp\_BOE\_Billing\_605 | BOE602 & BOE605 | 109 | NULL |
| usp\_BOE\_Billing\_FINISH | FINISH 609 | 112.87 | NULL |
| usp\_BOE\_Billing\_MFG | MFG 609 NO 5 AXIS | 110.96 | 200 |
| usp\_BOE\_Billing\_ASSY | ASSY 609 | 70.52 | 200 |
| usp\_BOE\_Billing\_5AXIS | MFG 609 5 AXIS | 107.28 | 200 |
| usp\_BOE\_Billing\_614 | BOLTBOARDS | 60 | NULL |
| usp\_BOE\_BILLING\_TUKWILA | DO NOT USE | 75 | NULL |
| usp\_BOE\_BILLING\_HELENA | DO NOT USE | 75 | NULL |
| usp\_BOE\_BILLING\_EME | BOEEME | 109 | NULL |
|  |  |  |  |
|  |  | ^^^ |  |
|  |  |  |  |
| 2.)  |  |  |  |
|  |  |  |  |
|         , CASE |  |  |  |
|             WHEN WO.ACT\_SERVICE\_COST \> 0 THEN @SPECIAL (see table) |  |  |  |
|             ELSE 0 |  |  |  |
|         END \+ CASE |  |  |  |
|             WHEN TOTAL\_SHIPPED\_QTY \< \[Batch Qty\] AND CB.\[Description\] LIKE 'Stanchion%' THEN 175 |  |  |  |
|             ELSE 0 |  |  |  |
|         END AS \[SPECIAL FEES\] |  |  |  |
|  |  |  |  |


**Key Fields from `BOE_Stanchion_Cargo_Bay` table:**
- `[Batch Qty]` - Standard batch size threshold
- `[Description]` - Part type identifier (e.g., "Stanchion Panel", "Cargo Panel")

---

## Combined Special Fees Calculation

The **total Special Fees** is the **sum** of both conditions:

```sql
[SPECIAL FEES] = 
    /* Service Cost Fee (if applicable) */
    CASE WHEN WO.ACT_SERVICE_COST > 0 THEN @SPECIAL ELSE 0 END
    
    +  /* Minimum Lot Fee for Stanchions (if applicable) */
    CASE 
        WHEN TOTAL_SHIPPED_QTY < [Batch Qty] 
             AND CB.[Description] LIKE 'Stanchion%' 
        THEN 175 
        ELSE 0 
    END
```

---

## Configuration Tables Reference

### 1. `[sql-bi-1].LIVESupplemental.dbo.[BOE_Billing_Charges]`

**Purpose:** Stores configurable billing rates for BOE reports

**Key Columns:**
- `REPORT` - Report identifier (`'usp_BOE_BILLING_MFG'`)
- `CHARGE` - Standard hourly rate (used for `@CHARGE` variable)
- `SPECIAL` - Special fee rate (used for `@SPECIAL` variable)
- `SERVICE` - Service cost divisor (used for `@SERVICE` variable)

**Used in variables (lines 42-44):**
```sql
DECLARE @CHARGE FLOAT = (SELECT CHARGE FROM ...)
      , @SPECIAL FLOAT = (SELECT SPECIAL FROM ...)
      , @SERVICE FLOAT = (SELECT [SERVICE] FROM ...)
```

### 2. `[sql-bi-1].LIVESupplemental.dbo.[BOE_Stanchion_Cargo_Bay]`

**Purpose:** Defines fixed-hour pricing and batch quantities for special part types

**Key Columns:**
- `[PART NUMBER]` - Part identifier
- `[Description]` - Part type (e.g., "Stanchion Panel", "Cargo Panel")
- `[Mfg_Unit Setup Hours]` - Fixed setup hours per unit
- `[Mfg_Unit Run Hours]` - Fixed run hours per unit
- `[Batch Qty]` - Standard batch size threshold

**Join (line 172):**
```sql
LEFT OUTER JOIN [sql-bi-1].LIVESupplemental.dbo.[BOE_Stanchion_Cargo_Bay] CB 
    ON CB.[PART NUMBER] = COL.PART_ID
```

---

## Business Context

### Service Cost Special Fee
- Applies to work orders that incurred **external service costs** (e.g., outsourced operations, special processing)
- Rate is **centrally configured** to allow easy updates without code changes
- Triggers billing of a **premium fee** for orders requiring special services

### Minimum Lot Special Fee ($175)
- **Only applies to Stanchion parts** (not Cargo Panels or other parts)
- Compensates for setup costs when shipping **below-batch quantities**
- Example: If `[Batch Qty] = 3` and customer orders only 1 Stanchion, the $175 fee applies
- This is a **business policy decision** to discourage small-lot orders or recover fixed costs

---

## Related Policies

### Comments Field Logic (line 101-112)
When a minimum lot fee is charged, the report adds a comment:
```
"QTY 1,MIN LOT,FIXED HOURS"
```

This appears in the `[COMMENTS]` column to explain the charge on the invoice.

---

## Summary Table

| Fee Type | Amount | Condition | Source |
|----------|--------|-----------|--------|
| **Service Cost Fee** | `@SPECIAL` (variable) | `WO.ACT_SERVICE_COST > 0` | `LIVESupplemental.dbo.BOE_Billing_Charges.SPECIAL` |
| **Min Lot Fee (Stanchion)** | `$175.00` (hardcoded) | `TOTAL_SHIPPED_QTY < [Batch Qty]` AND part is Stanchion | Business rule (hardcoded) |

**Note:** Both fees can apply to the same order (additive).

---

## Recommendations for Documentation

### Add to Business Glossary
Update [`Collaboration/Business_Glossary/README.md`]README.md ) with:

```markdown
### Special Fees (BOE Billing)
**Definition:** Additional charges applied to Boeing (BOE609) manufacturing orders based on service costs or minimum lot sizes  
**Components:**
1. **Service Cost Fee:** Variable rate applied when work order has external service costs
2. **Minimum Lot Fee:** Fixed $175 charge for Stanchion parts shipped below batch quantity (typically < 3 units)  
**Data Source:** `usp_BOE_BILLING_MFG` stored procedure  
**Configuration:** `[sql-bi-1].LIVESupplemental.dbo.BOE_Billing_Charges` (rates), `BOE_Stanchion_Cargo_Bay` (thresholds)  
**Related Terms:** Service Cost, Batch Quantity, Stanchion Parts
```

---

**Need clarification on:**
1. Current value of `@SPECIAL` in the `BOE_Billing_Charges` table?
2. Should the $175 minimum lot fee be moved to the configuration table for easier maintenance?
3. Are there other parts besides Stanchions that should have minimum lot fees?