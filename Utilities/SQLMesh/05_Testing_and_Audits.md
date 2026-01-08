# SQLMesh Testing and Audits

## Unit Tests

SQLMesh tests verify model logic without hitting the database.

### Test File Structure
```
tests/
└── test_my_model.yaml
```

### Example Test
```yaml
test_customer_aggregation:
  model: analytics.customer_summary
  inputs:
    analytics.orders:
      - {customer_id: 1, amount: 100, order_date: '2024-01-01'}
      - {customer_id: 1, amount: 200, order_date: '2024-01-02'}
      - {customer_id: 2, amount: 150, order_date: '2024-01-01'}
  outputs:
    query: |
      SELECT customer_id, total_amount
      FROM analytics.customer_summary
      ORDER BY customer_id
    rows:
      - {customer_id: 1, total_amount: 300}
      - {customer_id: 2, total_amount: 150}
```

### Generate Test Scaffolding
```bash
sqlmesh create_test analytics.my_model \
  --query staging.source_data \
  "SELECT * FROM staging.source_data LIMIT 5"
```

### Run Tests
```bash
sqlmesh test                    # All tests
sqlmesh test my_model          # Specific model
sqlmesh test --verbose         # Detailed output
```

## Audits (Data Quality Checks)

### Built-in Audits

Define in MODEL block:
```sql
MODEL (
  name analytics.orders,
  audits (
    UNIQUE_VALUES(columns = (id)),
    NOT_NULL(columns = (id, customer_id, amount)),
    ACCEPTED_VALUES(column = status, is_in = ('pending', 'completed', 'cancelled')),
    FORALL(criteria = (amount > 0)),
    NUMBER_OF_ROWS(threshold = 1000)
  )
);
```

### Custom Audits

Create in `audits/` directory:

```sql
-- audits/positive_amounts.sql
AUDIT (
  name positive_amounts,
  blocking true
);

SELECT *
FROM @this_model
WHERE amount <= 0;
```

Use in models:
```sql
MODEL (
  name analytics.orders,
  audits (
    positive_amounts
  )
);
```

### Audit Options

| Audit | Description |
|-------|-------------|
| `UNIQUE_VALUES` | Check column uniqueness |
| `NOT_NULL` | Check for null values |
| `ACCEPTED_VALUES` | Validate against allowed values |
| `FORALL` | Custom boolean condition |
| `NUMBER_OF_ROWS` | Minimum row count |
| `ACCEPTED_RANGE` | Numeric range validation |

### Run Audits
```bash
sqlmesh audit                  # All models
sqlmesh audit analytics.orders # Specific model
```

### Blocking vs Non-blocking

```sql
AUDIT (
  name my_audit,
  blocking true   -- Fails the pipeline if audit fails
);
```
