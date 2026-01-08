# SQLMesh Incremental Models

## Overview

Incremental models process only new/changed data, improving performance for large datasets.

## INCREMENTAL_BY_TIME_RANGE

Process data in time-based batches:

```sql
MODEL (
  name analytics.daily_events,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column event_date
  ),
  cron '@daily'
);

SELECT 
  event_id,
  user_id,
  event_type,
  event_date,
  created_at
FROM raw.events
WHERE event_date BETWEEN @start_ds AND @end_ds;
```

### Time Column Types

```sql
-- Date column
kind INCREMENTAL_BY_TIME_RANGE (
  time_column event_date
)

-- Timestamp column
kind INCREMENTAL_BY_TIME_RANGE (
  time_column created_at,
  time_data_type TIMESTAMP
)

-- Epoch seconds
kind INCREMENTAL_BY_TIME_RANGE (
  time_column event_epoch,
  time_data_type EPOCH
)
```

## INCREMENTAL_BY_UNIQUE_KEY

Upsert based on unique key:

```sql
MODEL (
  name analytics.customers,
  kind INCREMENTAL_BY_UNIQUE_KEY (
    unique_key id
  )
);

SELECT 
  id,
  name,
  email,
  updated_at
FROM raw.customers
WHERE updated_at >= @start_ds;
```

### Composite Keys

```sql
kind INCREMENTAL_BY_UNIQUE_KEY (
  unique_key (order_id, line_item_id)
)
```

## Built-in Variables

| Variable | Description |
|----------|-------------|
| `@start_ds` | Start date (inclusive) |
| `@end_ds` | End date (inclusive) |
| `@start_ts` | Start timestamp |
| `@end_ts` | End timestamp |
| `@execution_ds` | Current execution date |

## Backfill

```bash
# Backfill specific date range
sqlmesh run --start 2024-01-01 --end 2024-03-31

# Backfill from model's start date
sqlmesh plan --restate-model analytics.daily_events
```

## Lookback Window

Handle late-arriving data:

```sql
MODEL (
  name analytics.events,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column event_date,
    lookback 3  -- Process 3 extra days
  )
);
```

## Forward-Only Mode

Skip backfill for new models:

```sql
MODEL (
  name analytics.new_events,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column event_date,
    forward_only true
  )
);
```

## Delete+Insert Strategy

Replace entire partitions:

```sql
MODEL (
  name analytics.daily_summary,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column summary_date
  ),
  partitioned_by summary_date
);
```
