# SQLMesh dbt Migration Guide

## Overview

SQLMesh can run dbt projects directly and supports gradual migration.

## Install dbt Support

```bash
pip install "sqlmesh[dbt]"
```

## Initialize from dbt Project

```bash
# Point to existing dbt project
sqlmesh init dbt --path /path/to/dbt/project
```

## Hybrid Mode

Run dbt and SQLMesh models together:

```
my_project/
├── dbt_project.yml          # Existing dbt config
├── models/                  # dbt models (still work)
│   └── staging/
├── sqlmesh_models/          # New SQLMesh models
│   └── analytics/
└── config.yaml              # SQLMesh config
```

## Key Differences

| Feature | dbt | SQLMesh |
|---------|-----|---------|
| Metadata | YAML files | Inline in SQL |
| Tests | YAML + SQL | YAML |
| Validation | Runtime | Compile-time |
| Environments | Clone data | Virtual pointers |
| Python models | Remote | Local or remote |
| Lineage | Table-level | Column-level |
| Transpilation | No | Yes (10+ dialects) |

## Converting dbt Models

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
  id,
  customer_id,
  amount
FROM {{ ref('raw_orders') }}
WHERE amount > 0
```

### SQLMesh Equivalent
```sql
-- models/staging/stg_orders.sql
MODEL (
  name staging.stg_orders,
  kind FULL,
  audits (
    FORALL(criteria = (amount > 0))
  )
);

SELECT 
  id,
  customer_id,
  amount
FROM raw.orders
WHERE amount > 0;
```

## Jinja Conversion

### dbt Jinja
```sql
{% if is_incremental() %}
WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}
```

### SQLMesh Built-in
```sql
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

## Migration Strategy

1. **Phase 1**: Install SQLMesh alongside dbt
2. **Phase 2**: Run `sqlmesh init dbt`
3. **Phase 3**: Convert models incrementally
4. **Phase 4**: Migrate tests
5. **Phase 5**: Remove dbt when complete

## Running Both

```bash
# Run dbt models
dbt run

# Run SQLMesh models
sqlmesh run

# Or let SQLMesh handle both
sqlmesh plan
```
