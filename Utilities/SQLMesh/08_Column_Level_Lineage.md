# 08 - SQLMesh Column-Level Lineage

## What is Column-Level Lineage?

Column-level lineage tracks exactly which source columns flow into each output column, including transformations applied.

```
Source Table                    Target Table
┌─────────────┐                ┌─────────────────┐
│ orders      │                │ order_summary   │
├─────────────┤                ├─────────────────┤
│ order_id    │───────────────▶│ order_id        │
│ amount      │──┬─────────────▶│ total_amount   │
│ amount      │──┘   SUM()     │                 │
│ customer_id │──┬─────────────▶│ order_count    │
│ (all rows)  │──┘   COUNT()   │                 │
└─────────────┘                └─────────────────┘
```

## Why It Matters

1. **Impact Analysis**: Know exactly what breaks before deploying
2. **Data Discovery**: Trace data back to original sources
3. **Compliance**: Track PII and sensitive data flow
4. **Debugging**: Understand where transformations occur
5. **Documentation**: Auto-generated data dictionary

## Viewing Lineage

### Command Line

```bash
# View DAG for all models
sqlmesh dag

# View specific model lineage
sqlmesh dag analytics.order_summary

# Export to file
sqlmesh dag --file lineage.svg
sqlmesh dag --file lineage.png
```

### VS Code Extension

1. Open a model file
2. Click "Lineage" tab at bottom
3. Explore interactive column-level graph

### Web UI (Deprecated)

```bash
sqlmesh ui
```

Navigate to Lineage tab for interactive exploration.

## How SQLMesh Tracks Lineage

SQLMesh parses SQL and tracks:

### Direct References

```sql
SELECT 
  order_id,           -- Direct: orders.order_id → order_summary.order_id
  customer_id         -- Direct: orders.customer_id → order_summary.customer_id
FROM orders;
```

### Transformations

```sql
SELECT 
  order_id,
  amount * 1.1 AS amount_with_tax,  -- Transform: orders.amount → amount_with_tax
  UPPER(name) AS customer_name      -- Transform: customers.name → customer_name
FROM orders
JOIN customers ON orders.customer_id = customers.id;
```

### Aggregations

```sql
SELECT 
  customer_id,
  SUM(amount) AS total_amount,     -- Aggregate: orders.amount → total_amount
  COUNT(*) AS order_count          -- Aggregate: orders.* → order_count
FROM orders
GROUP BY customer_id;
```

### Window Functions

```sql
SELECT 
  order_id,
  amount,
  SUM(amount) OVER (PARTITION BY customer_id) AS customer_total
  -- Window: orders.amount, orders.customer_id → customer_total
FROM orders;
```

### CASE Statements

```sql
SELECT 
  order_id,
  CASE 
    WHEN amount > 1000 THEN 'high'
    WHEN amount > 100 THEN 'medium'
    ELSE 'low'
  END AS order_tier
  -- Conditional: orders.amount → order_tier
FROM orders;
```

## Impact Analysis

When you run `sqlmesh plan`, lineage shows downstream effects:

```
$ sqlmesh plan

Directly Modified:
├── staging.orders (FULL)
│   └── column: amount (formula changed)
│
Indirectly Modified (downstream):
├── analytics.order_summary
│   └── column: total_amount (depends on staging.orders.amount)
├── analytics.customer_metrics
│   └── column: avg_order_value (depends on staging.orders.amount)
└── reporting.daily_revenue
    └── column: revenue (depends on analytics.order_summary.total_amount)
```

## Breaking vs Non-Breaking Changes

### Breaking Changes

- Removing a column
- Changing column data type
- Renaming a column

```
WARNING: Breaking change detected!
  staging.orders.discount_amount (removed)
    └── Used by: analytics.order_summary.net_amount
    └── Used by: reporting.margin_report.discount_total
```

### Non-Breaking Changes

- Adding a column
- Changing transformation logic (same output type)
- Adding filters

## Programmatic Access

Access lineage via Python:

```python
from sqlmesh import Context

# Load project
ctx = Context(paths=["./"])

# Get model
model = ctx.get_model("analytics.order_summary")

# Access column lineage
for column_name, sources in model.column_lineage.items():
    print(f"{column_name}:")
    for source in sources:
        print(f"  ← {source.model}.{source.column}")
        if source.transformation:
            print(f"    (via {source.transformation})")
```

## Lineage Metadata in Models

Add documentation that appears in lineage:

```sql
MODEL (
  name analytics.order_summary,
  description 'Daily order aggregations by customer',
  columns (
    customer_id 'Unique customer identifier',
    total_amount 'Sum of all order amounts',
    order_count 'Number of orders placed'
  )
);
```

## Use Cases

### Data Governance

Track sensitive data:

```sql
MODEL (
  name analytics.customer_pii,
  tags ['pii', 'gdpr'],
  columns (
    email 'PII: Customer email address',
    phone 'PII: Customer phone number'
  )
);
```

Query PII flow:

```bash
# Find all models using PII columns
sqlmesh dag --tag pii
```

### Root Cause Analysis

When data looks wrong:

1. Open the affected model in VS Code
2. Click on the suspicious column
3. Trace upstream to find the source
4. Identify where the issue was introduced

### Change Impact Assessment

Before modifying a column:

1. Run `sqlmesh plan --dry-run`
2. Review "Indirectly Modified" models
3. Notify downstream consumers
4. Plan coordinated deployment

## Best Practices

1. **Add column descriptions**: Documents lineage automatically
2. **Use meaningful column names**: Makes lineage graphs readable
3. **Keep transformations simple**: Complex logic obscures lineage
4. **Review lineage before PRs**: Catch unintended downstream effects
5. **Tag sensitive data**: Enable compliance tracking

## Next Steps

Continue to [09_dbt_Migration.md](09_dbt_Migration.md) to learn about migrating from dbt.
