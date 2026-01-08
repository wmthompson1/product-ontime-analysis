# 05 - SQLMesh Testing and Audits

## Overview

SQLMesh provides two layers of data quality:
1. **Unit Tests**: Verify transformation logic before deployment
2. **Audits**: Validate data quality after execution

## Unit Tests

### Test File Structure

Tests live in the `tests/` directory as YAML files:

```
tests/
├── test_orders.yaml
├── test_customers.yaml
└── staging/
    └── test_raw_orders.yaml
```

### Basic Test Structure

```yaml
test_order_aggregation:
  model: analytics.order_summary
  inputs:
    staging.orders:
      - {order_id: 1, customer_id: 100, amount: 50.00}
      - {order_id: 2, customer_id: 100, amount: 75.00}
      - {order_id: 3, customer_id: 200, amount: 25.00}
  outputs:
    query: |
      SELECT customer_id, total_amount
      FROM analytics.order_summary
      ORDER BY customer_id
    rows:
      - {customer_id: 100, total_amount: 125.00}
      - {customer_id: 200, total_amount: 25.00}
```

### Test Components

| Component | Description |
|-----------|-------------|
| `model` | The model being tested |
| `inputs` | Mock data for upstream models |
| `outputs.query` | SQL to query the result |
| `outputs.rows` | Expected output rows |

### Multiple Tests Per File

```yaml
test_positive_amounts:
  model: analytics.orders
  inputs:
    staging.raw_orders:
      - {id: 1, amount: 100}
      - {id: 2, amount: -50}
  outputs:
    query: SELECT COUNT(*) AS cnt FROM analytics.orders
    rows:
      - {cnt: 1}

test_null_handling:
  model: analytics.orders
  inputs:
    staging.raw_orders:
      - {id: 1, amount: null}
      - {id: 2, amount: 100}
  outputs:
    query: SELECT id, amount FROM analytics.orders WHERE amount IS NOT NULL
    rows:
      - {id: 2, amount: 100}
```

### Testing Incremental Models

```yaml
test_incremental_orders:
  model: analytics.daily_orders
  inputs:
    staging.orders:
      - {order_id: 1, order_date: '2024-01-15', amount: 100}
      - {order_id: 2, order_date: '2024-01-16', amount: 200}
  vars:
    start_ds: '2024-01-15'
    end_ds: '2024-01-15'
  outputs:
    query: SELECT order_id, amount FROM analytics.daily_orders
    rows:
      - {order_id: 1, amount: 100}
```

### Generate Test Scaffolding

```bash
# Auto-generate test from real data
sqlmesh create_test analytics.orders \
  --query staging.raw_orders \
  "SELECT * FROM staging.raw_orders LIMIT 5"
```

### Run Tests

```bash
# Run all tests
sqlmesh test

# Run specific model tests
sqlmesh test analytics.orders

# Verbose output
sqlmesh test --verbose
```

## Audits (Data Quality Checks)

### Built-in Audits

Define audits in the MODEL block:

```sql
MODEL (
  name analytics.orders,
  kind FULL,
  audits (
    UNIQUE_VALUES(columns = (order_id)),
    NOT_NULL(columns = (order_id, customer_id, amount)),
    ACCEPTED_VALUES(column = status, is_in = ('pending', 'shipped', 'delivered')),
    FORALL(criteria = (amount > 0)),
    NUMBER_OF_ROWS(threshold = 100)
  )
);
```

### Audit Types

| Audit | Description | Example |
|-------|-------------|---------|
| `UNIQUE_VALUES` | Check column uniqueness | `UNIQUE_VALUES(columns = (id))` |
| `NOT_NULL` | Check for null values | `NOT_NULL(columns = (id, name))` |
| `ACCEPTED_VALUES` | Validate against allowed values | `ACCEPTED_VALUES(column = status, is_in = ('a', 'b'))` |
| `FORALL` | Custom boolean condition | `FORALL(criteria = (amount > 0))` |
| `NUMBER_OF_ROWS` | Minimum row count | `NUMBER_OF_ROWS(threshold = 1000)` |
| `ACCEPTED_RANGE` | Numeric range validation | `ACCEPTED_RANGE(column = pct, min_v = 0, max_v = 100)` |

### Custom Audits

Create reusable audits in `audits/` directory:

```sql
-- audits/valid_date_range.sql
AUDIT (
  name valid_date_range,
  blocking true
);

SELECT *
FROM @this_model
WHERE order_date > CURRENT_DATE
   OR order_date < '2020-01-01';
```

Use in models:

```sql
MODEL (
  name analytics.orders,
  audits (
    valid_date_range,
    UNIQUE_VALUES(columns = (id))
  )
);
```

### Parameterized Audits

```sql
-- audits/freshness_check.sql
AUDIT (
  name freshness_check,
  defaults (
    max_age_hours = 24
  )
);

SELECT *
FROM @this_model
WHERE updated_at < CURRENT_TIMESTAMP - INTERVAL '@max_age_hours hours';
```

Use with parameters:

```sql
MODEL (
  name analytics.orders,
  audits (
    freshness_check(max_age_hours = 12)
  )
);
```

### Blocking vs Non-blocking

```sql
AUDIT (
  name critical_check,
  blocking true    -- Fails pipeline if audit fails
);

AUDIT (
  name warning_check,
  blocking false   -- Logs warning but continues
);
```

### Run Audits

```bash
# Run all audits
sqlmesh audit

# Audit specific model
sqlmesh audit analytics.orders

# Verbose output
sqlmesh audit --verbose
```

## Best Practices

### Testing

1. **Test edge cases**: Nulls, empty strings, boundary values
2. **Test business logic**: Aggregations, calculations, filters
3. **Keep tests focused**: One behavior per test
4. **Use realistic data**: Mirror production patterns

### Audits

1. **Start with basics**: UNIQUE_VALUES, NOT_NULL on key columns
2. **Add business rules**: FORALL for domain constraints
3. **Use blocking audits** for critical data quality issues
4. **Monitor trends**: Track audit failures over time

## Next Steps

Continue to [06_Incremental_Models.md](06_Incremental_Models.md) for advanced incremental patterns.
