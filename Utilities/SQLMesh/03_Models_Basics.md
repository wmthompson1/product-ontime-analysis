# 03 - SQLMesh Models Basics

## What is a Model?

A SQLMesh model is a SQL file that:
1. Defines metadata in a `MODEL()` block
2. Contains a SELECT statement that transforms data
3. Produces a table or view in your data warehouse

## Model Anatomy

```sql
MODEL (
  name schema_name.model_name,    -- Required: fully qualified name
  kind FULL,                       -- Required: materialization type
  cron '@daily',                   -- Schedule (optional)
  grain id,                        -- Primary key (optional)
  owner 'data-team',               -- Owner (optional)
  description 'Model description', -- Documentation (optional)
  audits (                         -- Data quality checks (optional)
    UNIQUE_VALUES(columns = (id)),
    NOT_NULL(columns = (id))
  )
);

-- SQL SELECT statement
SELECT 
  id,
  name,
  amount / 100 AS amount_dollars
FROM source_schema.source_table;
```

## Model Kinds

### FULL

Rebuilds the entire table on each run:

```sql
MODEL (
  name analytics.daily_summary,
  kind FULL,
  cron '@daily'
);

SELECT 
  order_date,
  COUNT(*) AS order_count,
  SUM(amount) AS total_amount
FROM staging.orders
GROUP BY order_date;
```

**Use when:**
- Small to medium tables
- Complete rebuild is acceptable
- Data doesn't have a clear time dimension

### VIEW

Creates a database view (no physical table):

```sql
MODEL (
  name analytics.current_inventory,
  kind VIEW
);

SELECT 
  product_id,
  product_name,
  quantity_on_hand
FROM staging.inventory
WHERE quantity_on_hand > 0;
```

**Use when:**
- Real-time data needed
- Small transformations
- No storage overhead desired

### INCREMENTAL_BY_TIME_RANGE

Processes data in time-based batches:

```sql
MODEL (
  name analytics.events,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column event_date
  ),
  cron '@daily'
);

SELECT 
  event_id,
  user_id,
  event_type,
  event_date
FROM raw.events
WHERE event_date BETWEEN @start_ds AND @end_ds;
```

**Use when:**
- Large fact tables
- Data has a timestamp/date column
- Only new data needs processing

### INCREMENTAL_BY_UNIQUE_KEY

Upserts based on a unique key:

```sql
MODEL (
  name analytics.customers,
  kind INCREMENTAL_BY_UNIQUE_KEY (
    unique_key customer_id
  )
);

SELECT 
  customer_id,
  name,
  email,
  updated_at
FROM raw.customers
WHERE updated_at >= @start_ds;
```

**Use when:**
- Slowly changing dimensions
- Upsert logic needed
- Deduplication required

### SEED

Loads static data from CSV/JSON:

```sql
MODEL (
  name staging.country_codes,
  kind SEED (
    path '../seeds/countries.csv'
  )
);
```

**Use when:**
- Reference data
- Lookup tables
- Static configuration

### EMBEDDED

Inline CTE (not materialized):

```sql
MODEL (
  name staging.cte_helper,
  kind EMBEDDED
);

SELECT id, name FROM source;
```

## Built-in Variables

| Variable | Type | Description |
|----------|------|-------------|
| `@start_ds` | DATE | Start of processing window |
| `@end_ds` | DATE | End of processing window |
| `@start_ts` | TIMESTAMP | Start timestamp |
| `@end_ts` | TIMESTAMP | End timestamp |
| `@execution_ds` | DATE | Current execution date |
| `@execution_ts` | TIMESTAMP | Current execution timestamp |
| `@this_model` | STRING | Current model name |

### Using Variables

```sql
MODEL (
  name analytics.daily_orders,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column order_date
  )
);

SELECT 
  order_id,
  order_date,
  amount
FROM raw.orders
WHERE order_date BETWEEN @start_ds AND @end_ds
  AND order_date < @execution_ds;  -- Exclude today
```

## Model Metadata Options

```sql
MODEL (
  name schema.model_name,
  kind FULL,
  
  -- Scheduling
  cron '@daily',                    -- Cron expression
  start '2024-01-01',               -- Backfill start date
  
  -- Documentation
  description 'Model description',
  owner 'team-name',
  tags ['finance', 'critical'],
  
  -- Data quality
  grain (id, date),                 -- Primary key columns
  audits (
    UNIQUE_VALUES(columns = (id)),
    NOT_NULL(columns = (id, amount)),
    FORALL(criteria = (amount > 0))
  ),
  
  -- Physical options
  partitioned_by order_date,        -- Partition column
  clustered_by customer_id,         -- Cluster column
  
  -- Dependencies
  depends_on [external.table],      -- External dependencies
  
  -- Storage
  storage_format PARQUET            -- Output format
);
```

## Referencing Other Models

Simply use the fully qualified model name:

```sql
MODEL (name analytics.enriched_orders);

SELECT 
  o.order_id,
  o.amount,
  c.customer_name,
  p.product_name
FROM analytics.orders AS o
LEFT JOIN analytics.customers AS c ON o.customer_id = c.id
LEFT JOIN analytics.products AS p ON o.product_id = p.id;
```

SQLMesh automatically:
- Detects dependencies
- Builds models in correct order
- Tracks column-level lineage

## SQL Dialect Support

SQLMesh transpiles SQL across dialects:

```sql
-- Write in DuckDB syntax
SELECT 
  DATE_TRUNC('month', order_date) AS month,
  COUNT(*) AS orders
FROM orders
GROUP BY 1;

-- Automatically transpiled to Snowflake, BigQuery, etc.
```

## Next Steps

Continue to [04_Commands_Reference.md](04_Commands_Reference.md) to learn SQLMesh commands.
