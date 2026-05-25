Searched for text `split` (`**/Business_Glossary/*.md`), no results

Read [](file:///c%3A/Users/williamt/source/skillsinc/skills-inc-org/SQL-Projects/Collaboration/Business_Glossary)

Read [](file:///c%3A/Users/williamt/source/skillsinc/skills-inc-org/SQL-Projects/Collaboration/Business_Glossary/README.md#1-1), lines 1 to 100

Searched for text `composite key` (`**/*.md`), 9 results

Searched for text `BASE_ID` (`**/*.md`), 20 results

In this repository and the underlying **Infor Visual Manufacturing** ERP system, a **Work Order Split** represents a subset or a "branch" of an original parent work order that has been separated into its own tracking ID.

### Definition of a Work Order Split
A split occurs when a portion of the quantity on a single work order needs to be tracked independently from the original batch. This typically happens for one of three reasons:
1.  **Partial Completion**: Part of the batch is finished and needs to move to the next operation or shipping, while the rest is delayed.
2.  **Quality Issues**: Some units are set aside for rework (NCR/NCM process), while the "good" units continue through production.
3.  **Expediting**: A small quantity of a larger order is prioritized to meet an urgent customer need.

### Data Representation
In the database (specifically the `WORK_ORDER` table), a Work Order is identified by a **Composite Key**. The `SPLIT_ID` is a mandatory part of this identity:

| Field | Description | Example |
| :--- | :--- | :--- |
| **TYPE** | Work order category (e.g., M for Master W for Work Order) | `M` |
| **BASE_ID** | The main order number | `12345` |
| **LOT_ID** | Used for grouping related orders | `1` |
| **SPLIT_ID** | **The unique branch/split identifier** | `0`, `1`, `A`, etc. |
| **SUB_ID** | Subordinate indicatore (0 is end item) | `0` |

### Key Technical Rules for Splits
*   **The "0" Split**: By default, every work order starts as **Split 0**. If you see `SPLIT_ID = '0'`, it means the order has never been split.
*   **Inheritance**: When a split is created (e.g., Split 1 from Split 0), it usually inherits the same `BASE_ID` and `LOT_ID`, but carries a portion of the original `ORDER_QTY`.
*   **Joining Logic**: Because of splits, you cannot join tables (like `OPERATION` or `LABOR_TICKET`) to `WORK_ORDER` using only the `BASE_ID`. You **must** include the `SPLIT_ID` in your join criteria to avoid multiplying results or pulling data from the wrong branch of the order.

### Example in the Codebase
As seen in work_order_operations_flow.md:
```sql
-- Correct join pattern including Split
JOIN dbo.WORK_ORDER a 
  ON i.WORKORDER_BASE_ID = a.BASE_ID
 AND i.WORKORDER_LOT_ID = a.LOT_ID 
 AND i.WORKORDER_SPLIT_ID = a.SPLIT_ID -- This ensures you hit the specific split
```

In summary, a **Work Order Split** is a way to maintain the genealogy of a production order while allowing physical quantities to move through the factory at different speeds or with different statuses.