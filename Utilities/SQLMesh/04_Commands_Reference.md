# 04 - SQLMesh Commands Reference

## Core Workflow Commands

### sqlmesh plan

The most important command - previews and applies changes:

```bash
# Plan for production environment
sqlmesh plan

# Plan for specific environment
sqlmesh plan dev
sqlmesh plan staging

# Auto-apply without prompts
sqlmesh plan --auto-apply

# Dry run (preview only, no apply)
sqlmesh plan --dry-run

# Skip backfill (deploy without running)
sqlmesh plan --skip-backfill

# Restate specific models (force rebuild)
sqlmesh plan --restate-model analytics.orders

# Select specific models
sqlmesh plan --select-model analytics.orders

# Include downstream models
sqlmesh plan --select-model analytics.orders+
```

### sqlmesh run

Execute models on schedule:

```bash
# Run all due models
sqlmesh run

# Run for specific date range
sqlmesh run --start 2024-01-01 --end 2024-03-31

# Run specific models
sqlmesh run --select-model analytics.orders

# Ignore cron (run everything)
sqlmesh run --ignore-cron
```

### sqlmesh test

Run unit tests:

```bash
# Run all tests
sqlmesh test

# Run tests for specific model
sqlmesh test analytics.orders

# Verbose output
sqlmesh test --verbose

# Run specific test file
sqlmesh test tests/test_orders.yaml
```

## Development Commands

### sqlmesh init

Initialize new project:

```bash
sqlmesh init duckdb       # DuckDB (local)
sqlmesh init postgres     # PostgreSQL
sqlmesh init snowflake    # Snowflake
sqlmesh init bigquery     # BigQuery
sqlmesh init dbt          # From dbt project
```

### sqlmesh create_test

Generate test scaffolding:

```bash
# Create test from query
sqlmesh create_test analytics.orders \
  --query staging.raw_orders \
  "SELECT * FROM staging.raw_orders LIMIT 5"

# With specific columns
sqlmesh create_test analytics.orders \
  --query staging.raw_orders \
  "SELECT id, amount FROM staging.raw_orders WHERE id IN (1,2,3)"
```

### sqlmesh diff

Compare environments:

```bash
# Compare dev to prod
sqlmesh diff dev prod

# Compare specific model
sqlmesh diff dev prod --model analytics.orders
```

### sqlmesh table_diff

Compare table data:

```bash
sqlmesh table_diff analytics.orders dev prod

# With row limit
sqlmesh table_diff analytics.orders dev prod --limit 100
```

## Visualization Commands

### sqlmesh dag

View lineage DAG:

```bash
# View all models
sqlmesh dag

# Specific model and dependencies
sqlmesh dag analytics.orders

# Export to file
sqlmesh dag --file lineage.svg
sqlmesh dag --file lineage.png
```

### sqlmesh ui

Launch web interface (deprecated - use VS Code):

```bash
sqlmesh ui
sqlmesh ui --port 8080
sqlmesh ui --host 0.0.0.0
```

### sqlmesh render

Preview rendered SQL:

```bash
# Render model SQL
sqlmesh render analytics.orders

# Render for specific date
sqlmesh render analytics.orders --start 2024-01-01 --end 2024-01-31
```

## Information Commands

### sqlmesh info

Show project information:

```bash
sqlmesh info
```

### sqlmesh audit

Run data quality audits:

```bash
# Run all audits
sqlmesh audit

# Audit specific model
sqlmesh audit analytics.orders

# Verbose output
sqlmesh audit --verbose
```

### sqlmesh fetchdf

Query and return DataFrame:

```bash
# Run query
sqlmesh fetchdf "SELECT * FROM analytics.orders LIMIT 10"

# Query specific environment
sqlmesh fetchdf "SELECT COUNT(*) FROM analytics.orders" --gateway prod
```

### sqlmesh evaluate

Evaluate model without persisting:

```bash
sqlmesh evaluate analytics.orders
sqlmesh evaluate analytics.orders --start 2024-01-01 --end 2024-01-31
```

## Environment Management

### sqlmesh invalidate

Remove environment:

```bash
sqlmesh invalidate dev
sqlmesh invalidate staging
```

### sqlmesh clean

Clean up old snapshots:

```bash
sqlmesh clean
```

### sqlmesh migrate

Run state migrations:

```bash
sqlmesh migrate
```

## Common Flags

| Flag | Description |
|------|-------------|
| `--gateway` | Select connection gateway |
| `--start` | Start date for backfill |
| `--end` | End date for backfill |
| `--auto-apply` | Skip confirmation prompts |
| `--dry-run` | Preview without applying |
| `--verbose` | Detailed output |
| `--select-model` | Target specific model |
| `--help` | Show command help |

## Command Shortcuts

```bash
# Common aliases
alias sm="sqlmesh"
alias smp="sqlmesh plan"
alias smr="sqlmesh run"
alias smt="sqlmesh test"
```

## CI/CD Commands

```bash
# For CI pipelines
sqlmesh plan --auto-apply --skip-tests
sqlmesh test --verbose
sqlmesh audit

# Generate artifacts
sqlmesh dag --file lineage.svg
```

## Next Steps

Continue to [05_Testing_and_Audits.md](05_Testing_and_Audits.md) to learn about testing.
