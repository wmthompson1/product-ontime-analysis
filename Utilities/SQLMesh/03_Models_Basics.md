# SQLMesh Models Basics

## Model Structure

SQLMesh models use inline metadata (no separate YAML files):

```sql
MODEL (
  name schema_name.model_name,
  kind FULL,
  cron '@daily',
  grain id,
  audits (
    UNIQUE_VALUES(columns = (id)),
    NOT_NULL(columns = (id))
  )
);

SELECT 
  id,
  name,
  amount / 100 AS amount_dollars
FROM source_table;
```

## Model Kinds

### FULL
Rebuilds entire table each run:
```sql
MODEL (
  name analytics.daily_summary,
  kind FULL
);
```

### VIEW
Creates a database view:
```sql
MODEL (
  name analytics.current_inventory,
  kind VIEW
);
```

### INCREMENTAL_BY_TIME_RANGE
Processes data in time-based batches:
```sql
MODEL (
  name analytics.events,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column event_date
  )
);

SELECT *
FROM raw_events
WHERE event_date BETWEEN @start_ds AND @end_ds;
```

### INCREMENTAL_BY_UNIQUE_KEY
Upserts based on unique key:
```sql
MODEL (
  name analytics.customers,
  kind INCREMENTAL_BY_UNIQUE_KEY (
    unique_key id
  )
);
```

### SEED
Loads static data from CSV:
```sql
MODEL (
  name staging.countries,
  kind SEED (
    path '../seeds/countries.csv'
  )
);
```

## Built-in Variables

- `@start_ds` / `@end_ds` - Date range boundaries
- `@execution_ds` - Current execution date
- `@this_model` - Current model reference

## Model Metadata Options

```sql
MODEL (
  name my_schema.my_model,
  kind FULL,
  cron '@daily',                    -- Schedule
  grain (id, date),                 -- Primary key columns
  owner 'data-team',                -- Owner
  description 'Daily sales summary',
  tags ['finance', 'sales'],
  audits (
    UNIQUE_VALUES(columns = (id)),
    NOT_NULL(columns = (id, amount))
  )
);
```

## Referencing Other Models

```sql
MODEL (name analytics.enriched_orders);

SELECT 
  o.*,
  c.name AS customer_name
FROM analytics.orders AS o
LEFT JOIN analytics.customers AS c ON o.customer_id = c.id;
```
