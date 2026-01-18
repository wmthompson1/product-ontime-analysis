# 09 - SQLMesh dbt Migration Guide

## Overview

SQLMesh can:
1. Run dbt projects directly
2. Support gradual migration
3. Import dbt configurations

## Why Migrate?

| Feature | dbt | SQLMesh |
|---------|-----|---------|
| **Metadata** | Separate YAML files | Inline in SQL |
| **Validation** | Runtime (in warehouse) | Compile-time |
| **Environments** | Clone data | Virtual (no duplication) |
| **Python models** | Remote execution | Local or remote |
| **Unit tests** | v1.8+ (external) | Built-in, fast |
| **Lineage** | Table-level | Column-level |
| **Transpilation** | No | Yes (10+ dialects) |
| **State management** | External (dbt Cloud) | Built-in |

## Install dbt Support

```bash
pip install "sqlmesh[dbt]"
```

## Migration Strategies

### Strategy 1: Side-by-Side (Recommended)

Run dbt and SQLMesh together during transition.

```bash
# Initialize SQLMesh in dbt project
cd my-dbt-project
sqlmesh init dbt
```

This creates a `config.yaml` that reads your dbt configuration.

### Strategy 2: Full Migration

Convert all dbt models to SQLMesh format.

## Converting Models

### dbt Model

```sql
-- models/staging/stg_orders.sql
{{
  config(
    materialized='table',
    schema='staging'
  )
}}

SELECT 
  id AS order_id,
  user_id AS customer_id,
  amount,
  created_at
FROM {{ source('raw', 'orders') }}
WHERE amount > 0
```

With schema YAML:

```yaml
# models/staging/schema.yml
models:
  - name: stg_orders
    description: Staged orders with positive amounts
    columns:
      - name: order_id
        description: Unique order identifier
        tests:
          - unique
          - not_null
```

### SQLMesh Equivalent

```sql
-- models/staging/stg_orders.sql
MODEL (
  name staging.stg_orders,
  kind FULL,
  description 'Staged orders with positive amounts',
  grain order_id,
  audits (
    UNIQUE_VALUES(columns = (order_id)),
    NOT_NULL(columns = (order_id))
  ),
  columns (
    order_id 'Unique order identifier'
  )
);

SELECT 
  id AS order_id,
  user_id AS customer_id,
  amount,
  created_at
FROM raw.orders
WHERE amount > 0;
```

## Jinja to SQLMesh

### ref() Function

```sql
-- dbt
SELECT * FROM {{ ref('stg_orders') }}

-- SQLMesh
SELECT * FROM staging.stg_orders
```

### source() Function

```sql
-- dbt
SELECT * FROM {{ source('raw', 'orders') }}

-- SQLMesh
SELECT * FROM raw.orders
```

### is_incremental()

```sql
-- dbt
{% if is_incremental() %}
WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}

-- SQLMesh
MODEL (
  name analytics.orders,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column updated_at
  )
);

SELECT *
FROM raw.orders
WHERE updated_at BETWEEN @start_ds AND @end_ds;
```

### var() Function

```sql
-- dbt
WHERE created_at >= '{{ var("start_date") }}'

-- SQLMesh (use config or built-in variables)
MODEL (
  start '2024-01-01'
);

WHERE created_at >= @start_ds
```

### Custom Macros

```sql
-- dbt macros/generate_schema_name.sql
{% macro generate_surrogate_key(columns) %}
  md5(concat({% for col in columns %}{{ col }}{% if not loop.last %}, {% endif %}{% endfor %}))
{% endmacro %}

-- SQLMesh macros/generate_surrogate_key.py
from sqlmesh import macro

@macro()
def generate_surrogate_key(evaluator, *columns):
    cols = ", ".join(str(c) for c in columns)
    return f"md5(concat({cols}))"
```

## Test Migration

### dbt Tests

```yaml
# schema.yml
models:
  - name: orders
    columns:
      - name: id
        tests:
          - unique
          - not_null
      - name: amount
        tests:
          - positive_value  # custom test
```

### SQLMesh Audits

```sql
MODEL (
  name analytics.orders,
  audits (
    UNIQUE_VALUES(columns = (id)),
    NOT_NULL(columns = (id)),
    FORALL(criteria = (amount > 0))  -- replaces custom test
  )
);
```

### dbt Unit Tests (v1.8+)

```yaml
# tests/test_orders.yml
unit_tests:
  - name: test_order_calculation
    model: orders
    given:
      - input: ref('raw_orders')
        rows:
          - {id: 1, amount: 100}
```

### SQLMesh Unit Tests

```yaml
# tests/test_orders.yaml
test_order_calculation:
  model: analytics.orders
  inputs:
    staging.raw_orders:
      - {id: 1, amount: 100}
  outputs:
    query: SELECT id, amount FROM analytics.orders
    rows:
      - {id: 1, amount: 100}
```

## Configuration Migration

### dbt_project.yml

```yaml
# dbt
name: my_project
version: '1.0.0'
config-version: 2

vars:
  start_date: '2024-01-01'

models:
  my_project:
    staging:
      +materialized: view
    marts:
      +materialized: table
```

### SQLMesh config.yaml

```yaml
# SQLMesh
gateways:
  default:
    connection:
      type: snowflake
      # connection details

model_defaults:
  dialect: snowflake
  start: 2024-01-01
  cron: '@daily'
```

## Running Both

During migration, run both systems:

```bash
# Run dbt models
dbt run

# Run SQLMesh models
sqlmesh run

# Or let SQLMesh handle dbt models
sqlmesh plan  # Includes dbt models via sqlmesh init dbt
```

## Migration Checklist

- [ ] Install `sqlmesh[dbt]`
- [ ] Run `sqlmesh init dbt`
- [ ] Test dbt models via SQLMesh
- [ ] Convert models incrementally
- [ ] Migrate tests to SQLMesh format
- [ ] Update CI/CD pipelines
- [ ] Train team on SQLMesh commands
- [ ] Remove dbt when complete

## Best Practices

1. **Migrate incrementally**: Convert one model at a time
2. **Start with staging**: Simpler models first
3. **Keep dbt running**: Dual-run during transition
4. **Test thoroughly**: Compare outputs between systems
5. **Document differences**: Note behavioral changes

## Next Steps

Continue to [10_Best_Practices.md](10_Best_Practices.md) for project organization tips.
