# SQLMesh Column-Level Lineage

## Overview

SQLMesh provides column-level lineage tracking, showing exactly which source columns flow into each output column.

## Viewing Lineage

### Command Line
```bash
# View DAG for all models
sqlmesh dag

# View lineage for specific model
sqlmesh dag analytics.customer_summary
```

### Web UI
```bash
sqlmesh ui
```

Navigate to the Lineage tab to see interactive column-level lineage.

## How It Works

SQLMesh parses SQL and tracks:
- Direct column references
- Transformations and expressions
- Joins and aggregations
- Window functions

### Example Model
```sql
MODEL (name analytics.order_summary);

SELECT 
  o.customer_id,
  c.customer_name,
  SUM(o.amount) AS total_amount,
  COUNT(*) AS order_count
FROM staging.orders o
JOIN staging.customers c ON o.customer_id = c.id
GROUP BY o.customer_id, c.customer_name;
```

### Resulting Lineage
```
analytics.order_summary.customer_id
  └── staging.orders.customer_id

analytics.order_summary.customer_name
  └── staging.customers.customer_name

analytics.order_summary.total_amount
  └── staging.orders.amount (SUM)

analytics.order_summary.order_count
  └── staging.orders.* (COUNT)
```

## Impact Analysis

When you run `sqlmesh plan`, lineage shows:
- Which downstream models are affected
- Which columns specifically change
- Whether changes are breaking

### Example Output
```
Directly Modified:
  └── staging.products (FULL)
      └── column: price (new formula)

Indirectly Modified:
  └── analytics.revenue (column: total_revenue)
  └── reporting.daily_sales (column: product_revenue)
```

## Lineage Metadata

Access lineage programmatically:

```python
from sqlmesh import Context

ctx = Context(paths=["."])
model = ctx.get_model("analytics.order_summary")

# Get column lineage
for column, sources in model.column_lineage.items():
    print(f"{column}:")
    for source in sources:
        print(f"  <- {source}")
```

## Benefits

1. **Change Impact** - Know exactly what breaks before deploying
2. **Data Discovery** - Trace data back to sources
3. **Documentation** - Auto-generated data dictionary
4. **Debugging** - Find where transformations occur
5. **Compliance** - PII tracking and data governance
