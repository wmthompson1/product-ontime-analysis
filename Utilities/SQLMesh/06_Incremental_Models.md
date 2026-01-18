# 06 - SQLMesh Incremental Models

## Why Incremental?

Incremental models process only new or changed data, providing:
- **Performance**: Process GBs instead of TBs
- **Cost savings**: Less compute time = lower cloud bills
- **Faster iterations**: Quick development cycles

## INCREMENTAL_BY_TIME_RANGE

Process data in time-based batches:

```sql
MODEL (
  name analytics.daily_events,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column event_date
  ),
  cron '@daily',
  start '2024-01-01'
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
-- DATE column (default)
kind INCREMENTAL_BY_TIME_RANGE (
  time_column order_date
)

-- TIMESTAMP column
kind INCREMENTAL_BY_TIME_RANGE (
  time_column created_at,
  time_data_type TIMESTAMP
)

-- Unix epoch (seconds)
kind INCREMENTAL_BY_TIME_RANGE (
  time_column event_epoch,
  time_data_type EPOCH
)

-- Unix epoch (milliseconds)
kind INCREMENTAL_BY_TIME_RANGE (
  time_column event_ms,
  time_data_type EPOCH_MILLIS
)
```

### Batch Size

Control processing window:

```sql
kind INCREMENTAL_BY_TIME_RANGE (
  time_column event_date,
  batch_size 7  -- Process 7 days at a time
)
```

### Lookback Window

Handle late-arriving data:

```sql
kind INCREMENTAL_BY_TIME_RANGE (
  time_column event_date,
  lookback 3  -- Reprocess last 3 days
)
```

## INCREMENTAL_BY_UNIQUE_KEY

Upsert (insert/update) based on unique key:

```sql
MODEL (
  name analytics.customers,
  kind INCREMENTAL_BY_UNIQUE_KEY (
    unique_key customer_id
  ),
  cron '@daily'
);

SELECT 
  customer_id,
  name,
  email,
  address,
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

### With Time Filter

Combine unique key with time-based filtering:

```sql
MODEL (
  name analytics.orders,
  kind INCREMENTAL_BY_UNIQUE_KEY (
    unique_key order_id,
    time_column updated_at
  )
);

SELECT 
  order_id,
  status,
  amount,
  updated_at
FROM raw.orders
WHERE updated_at BETWEEN @start_ds AND @end_ds;
```

## Built-in Variables

| Variable | Type | Description |
|----------|------|-------------|
| `@start_ds` | DATE | Start of processing window (inclusive) |
| `@end_ds` | DATE | End of processing window (inclusive) |
| `@start_ts` | TIMESTAMP | Start timestamp |
| `@end_ts` | TIMESTAMP | End timestamp |
| `@execution_ds` | DATE | Current execution date |
| `@execution_ts` | TIMESTAMP | Current execution timestamp |

### Using Variables Correctly

```sql
-- Good: Use built-in variables for filtering
WHERE event_date BETWEEN @start_ds AND @end_ds

-- Good: Exclude current day (data may be incomplete)
WHERE event_date BETWEEN @start_ds AND @end_ds
  AND event_date < @execution_ds

-- Bad: Hardcoded dates
WHERE event_date >= '2024-01-01'
```

## Backfill

### Initial Backfill

```bash
# Backfill from model's start date
sqlmesh plan --auto-apply
```

### Restate (Force Rebuild)

```bash
# Reprocess specific model
sqlmesh plan --restate-model analytics.events

# Reprocess date range
sqlmesh run --start 2024-01-01 --end 2024-03-31
```

### Forward-Only Mode

Skip backfill for new models:

```sql
MODEL (
  name analytics.new_events,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column event_date,
    forward_only true
  ),
  start '2024-01-01'
);
```

## Partitioning

Improve query performance with partitions:

```sql
MODEL (
  name analytics.daily_orders,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column order_date
  ),
  partitioned_by order_date
);
```

### Multiple Partition Columns

```sql
partitioned_by (order_date, region)
```

## Delete+Insert Strategy

Replace entire partitions (more efficient for some warehouses):

```sql
MODEL (
  name analytics.hourly_metrics,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column metric_hour
  ),
  partitioned_by DATE(metric_hour)
);

-- Each run replaces the entire day's partition
```

## Merge Strategy

For INCREMENTAL_BY_UNIQUE_KEY, control merge behavior:

```sql
MODEL (
  name analytics.product_inventory,
  kind INCREMENTAL_BY_UNIQUE_KEY (
    unique_key product_id,
    when_matched UPDATE,
    when_not_matched INSERT
  )
);
```

## Best Practices

1. **Choose the right strategy**:
   - Time-series data → `INCREMENTAL_BY_TIME_RANGE`
   - Slowly changing dimensions → `INCREMENTAL_BY_UNIQUE_KEY`

2. **Handle late-arriving data**:
   - Use `lookback` parameter
   - Or schedule reprocessing jobs

3. **Partition large tables**:
   - Match partition to time_column
   - Enables partition pruning

4. **Monitor backfill progress**:
   - Check logs for batch completion
   - Use `sqlmesh info` to see model state

## Next Steps

Continue to [07_Virtual_Environments.md](07_Virtual_Environments.md) to learn about isolated development.
