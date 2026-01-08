# 10 - SQLMesh Best Practices

## Project Organization

### Recommended Structure

```
my-sqlmesh-project/
├── config.yaml              # Database connections
├── models/
│   ├── staging/             # Raw data cleaning
│   │   ├── stg_orders.sql
│   │   ├── stg_customers.sql
│   │   └── stg_products.sql
│   ├── intermediate/        # Business logic
│   │   ├── int_orders_enriched.sql
│   │   └── int_customer_metrics.sql
│   └── marts/               # Final analytics tables
│       ├── fct_orders.sql
│       ├── fct_revenue.sql
│       └── dim_customers.sql
├── seeds/                   # Static reference data
│   ├── country_codes.csv
│   └── product_categories.csv
├── tests/                   # Unit tests
│   ├── staging/
│   ├── intermediate/
│   └── marts/
├── macros/                  # Reusable SQL/Python
│   ├── __init__.py
│   └── date_utils.py
├── audits/                  # Custom data quality
│   └── freshness_check.sql
└── docs/                    # Documentation
    └── data_dictionary.md
```

### Naming Conventions

| Layer | Prefix | Example |
|-------|--------|---------|
| Sources | `src_` | `src_shopify_orders` |
| Staging | `stg_` | `stg_orders` |
| Intermediate | `int_` | `int_orders_enriched` |
| Fact tables | `fct_` | `fct_daily_revenue` |
| Dimension tables | `dim_` | `dim_customers` |
| Metrics | `mrt_` | `mrt_customer_ltv` |

### File Naming

- Use snake_case: `stg_orders.sql`
- Match model name to file name
- Group related models in subdirectories

## Model Design

### Keep Models Focused

```sql
-- Good: Single responsibility
MODEL (name staging.stg_orders);
SELECT 
  id AS order_id,
  user_id AS customer_id,
  amount_cents / 100.0 AS amount,
  created_at
FROM raw.orders;

-- Bad: Too many concerns
MODEL (name analytics.everything);
SELECT ... -- 500 lines of joins and transformations
```

### Use Appropriate Model Kinds

| Kind | Use Case |
|------|----------|
| `VIEW` | Small transformations, real-time needs |
| `FULL` | Small tables (<1M rows), dimension tables |
| `INCREMENTAL_BY_TIME_RANGE` | Large fact tables with timestamps |
| `INCREMENTAL_BY_UNIQUE_KEY` | Slowly changing dimensions |
| `SEED` | Static reference data |

### Limit Model Complexity

```sql
-- Good: Simple, readable
MODEL (name staging.stg_orders);
SELECT 
  id AS order_id,
  COALESCE(amount, 0) AS amount,
  created_at::DATE AS order_date
FROM raw.orders
WHERE status != 'cancelled';

-- Break complex logic into intermediate models
MODEL (name intermediate.int_orders_with_customer);
SELECT 
  o.*,
  c.customer_name,
  c.segment
FROM staging.stg_orders o
LEFT JOIN staging.stg_customers c ON o.customer_id = c.customer_id;
```

## Testing Strategy

### Test Coverage Pyramid

```
           /\
          /  \  End-to-End Tests
         /    \  (few, slow)
        /──────\
       /        \  Integration Tests
      /          \  (some)
     /────────────\
    /              \  Unit Tests
   /________________\  (many, fast)
```

### What to Test

1. **Business logic**: Calculations, aggregations
2. **Edge cases**: Nulls, empty strings, boundaries
3. **Data contracts**: Expected columns, types

```yaml
# tests/staging/test_stg_orders.yaml
test_null_amount_handling:
  model: staging.stg_orders
  inputs:
    raw.orders:
      - {id: 1, amount: null}
      - {id: 2, amount: 100}
  outputs:
    query: SELECT order_id, amount FROM staging.stg_orders
    rows:
      - {order_id: 1, amount: 0}      # Null becomes 0
      - {order_id: 2, amount: 100}

test_cancelled_orders_filtered:
  model: staging.stg_orders
  inputs:
    raw.orders:
      - {id: 1, status: 'completed'}
      - {id: 2, status: 'cancelled'}
  outputs:
    query: SELECT COUNT(*) AS cnt FROM staging.stg_orders
    rows:
      - {cnt: 1}
```

### Run Tests in CI

```bash
# Pre-commit
sqlmesh test --verbose

# In CI pipeline
sqlmesh test
sqlmesh audit
```

## Data Quality

### Essential Audits

```sql
MODEL (
  name marts.fct_orders,
  audits (
    -- Primary key integrity
    UNIQUE_VALUES(columns = (order_id)),
    NOT_NULL(columns = (order_id, customer_id, order_date)),
    
    -- Business rules
    FORALL(criteria = (amount >= 0)),
    FORALL(criteria = (quantity > 0)),
    
    -- Referential integrity
    FORALL(criteria = (customer_id IN (SELECT customer_id FROM dim_customers))),
    
    -- Freshness
    NUMBER_OF_ROWS(threshold = 100)
  )
);
```

### Custom Audit Library

```sql
-- audits/freshness_check.sql
AUDIT (
  name freshness_check,
  defaults (max_hours = 24)
);

SELECT *
FROM @this_model
WHERE updated_at < CURRENT_TIMESTAMP - INTERVAL '@max_hours hours';

-- audits/no_future_dates.sql
AUDIT (name no_future_dates);

SELECT *
FROM @this_model
WHERE order_date > CURRENT_DATE;
```

## Performance Optimization

### Partition Large Tables

```sql
MODEL (
  name analytics.events,
  kind INCREMENTAL_BY_TIME_RANGE(time_column event_date),
  partitioned_by event_date
);
```

### Use Incremental Where Possible

```sql
-- Instead of FULL for large tables
MODEL (
  name analytics.daily_metrics,
  kind INCREMENTAL_BY_TIME_RANGE(time_column metric_date),
  cron '@daily'
);
```

### Limit Backfills

```sql
MODEL (
  name analytics.recent_events,
  start '2024-01-01'  -- Don't backfill before this
);
```

### Batch Size Control

```sql
kind INCREMENTAL_BY_TIME_RANGE(
  time_column event_date,
  batch_size 7  -- Process 7 days at a time
)
```

## Development Workflow

### Use Virtual Environments

```bash
# Always develop in named environment
sqlmesh plan dev

# Test thoroughly
sqlmesh test
sqlmesh audit

# Compare to production
sqlmesh diff dev prod

# Promote when ready
sqlmesh plan
```

### Code Review Checklist

- [ ] Model has appropriate kind
- [ ] Audits defined for key columns
- [ ] Tests cover business logic
- [ ] Column descriptions added
- [ ] No SELECT *
- [ ] Joins are explicit (LEFT, INNER)
- [ ] Filters are appropriate
- [ ] Performance considered for large tables

## Documentation

### In-Model Documentation

```sql
MODEL (
  name marts.fct_orders,
  description 'Daily order fact table with enriched customer data',
  owner 'analytics-team',
  tags ['finance', 'daily', 'critical'],
  columns (
    order_id 'Unique order identifier from source system',
    customer_id 'Foreign key to dim_customers',
    order_date 'Date order was placed (UTC)',
    amount 'Order total in USD'
  )
);
```

### README in Project

```markdown
# Analytics Data Models

## Quick Start
sqlmesh plan dev
sqlmesh test

## Model Layers
- `staging/`: Raw data cleaning
- `intermediate/`: Business logic
- `marts/`: Analytics-ready tables

## Contacts
- Data Team: data-team@company.com
```

## CI/CD Integration

### GitHub Actions

```yaml
name: SQLMesh CI
on: [pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install sqlmesh
      - run: sqlmesh test
      - run: sqlmesh audit
      - run: sqlmesh plan --dry-run
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: sqlmesh-test
        name: SQLMesh Tests
        entry: sqlmesh test
        language: system
        pass_filenames: false
```

## Next Steps

Continue to [11_VSCode_Extension.md](11_VSCode_Extension.md) for IDE integration.
