# SQLMesh Best Practices

## Project Organization

### Folder Structure
```
project/
├── config.yaml
├── models/
│   ├── staging/           # Raw data cleaning
│   ├── intermediate/      # Business logic
│   └── marts/             # Final analytics tables
├── seeds/                 # Static reference data
├── tests/                 # Unit tests
├── macros/                # Reusable SQL
└── audits/                # Custom data quality checks
```

### Naming Conventions
- Use snake_case for model names
- Prefix staging models with `stg_`
- Prefix intermediate models with `int_`
- Use domain prefixes for marts: `fct_`, `dim_`

## Model Design

### Keep Models Focused
```sql
-- Good: Single responsibility
MODEL (name staging.stg_orders);
SELECT id, customer_id, amount, created_at
FROM raw.orders;

MODEL (name intermediate.int_orders_enriched);
SELECT o.*, c.name AS customer_name
FROM staging.stg_orders o
JOIN staging.stg_customers c ON o.customer_id = c.id;
```

### Use Appropriate Model Kinds
- `VIEW` for lightweight transformations
- `FULL` for small dimension tables
- `INCREMENTAL_BY_TIME_RANGE` for large fact tables
- `SEED` for static reference data

## Testing

### Test Coverage
1. Test all critical business logic
2. Test edge cases
3. Test data quality assumptions

```yaml
test_order_amounts:
  model: staging.stg_orders
  inputs:
    raw.orders:
      - {id: 1, amount: null}
      - {id: 2, amount: 100}
  outputs:
    rows:
      - {id: 2, amount: 100}  # Null filtered out
```

### Run Tests in CI
```bash
sqlmesh test --verbose
```

## Data Quality

### Use Audits Liberally
```sql
MODEL (
  name marts.fct_orders,
  audits (
    UNIQUE_VALUES(columns = (order_id)),
    NOT_NULL(columns = (order_id, customer_id, order_date)),
    FORALL(criteria = (amount >= 0)),
    NUMBER_OF_ROWS(threshold = 100)
  )
);
```

### Create Custom Audits
```sql
-- audits/valid_date_range.sql
AUDIT (name valid_date_range);

SELECT *
FROM @this_model
WHERE order_date > CURRENT_DATE
   OR order_date < '2020-01-01';
```

## Performance

### Partition Large Tables
```sql
MODEL (
  name analytics.events,
  kind INCREMENTAL_BY_TIME_RANGE(time_column event_date),
  partitioned_by event_date
);
```

### Use Incremental Where Possible
- Time-series data: `INCREMENTAL_BY_TIME_RANGE`
- Slowly changing dimensions: `INCREMENTAL_BY_UNIQUE_KEY`

### Limit Backfills
```sql
MODEL (
  name analytics.recent_events,
  start '2024-01-01'  # Don't backfill before this
);
```

## Deployment

### Use Virtual Environments
```bash
# Develop in isolation
sqlmesh plan dev

# Test thoroughly
sqlmesh test

# Promote to prod
sqlmesh plan
```

### CI/CD Pipeline
```yaml
# .github/workflows/sqlmesh.yml
steps:
  - run: pip install sqlmesh
  - run: sqlmesh test
  - run: sqlmesh plan --auto-apply
```

## Documentation

### Add Descriptions
```sql
MODEL (
  name marts.fct_orders,
  description 'Fact table containing all completed orders with enriched customer data',
  owner 'analytics-team'
);
```

### Use Tags
```sql
MODEL (
  name marts.fct_orders,
  tags ['finance', 'critical', 'pii']
);
```
