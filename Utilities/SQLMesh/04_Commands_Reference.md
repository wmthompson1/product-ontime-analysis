# SQLMesh Commands Reference

## Core Workflow Commands

### sqlmesh plan
Preview and apply changes:
```bash
sqlmesh plan              # Plan for prod environment
sqlmesh plan dev          # Plan for dev environment
sqlmesh plan --auto-apply # Auto-apply without prompts
```

### sqlmesh run
Execute scheduled models:
```bash
sqlmesh run               # Run all due models
sqlmesh run --start 2024-01-01 --end 2024-01-31
```

### sqlmesh test
Run unit tests:
```bash
sqlmesh test              # All tests
sqlmesh test my_model     # Specific model tests
```

## Development Commands

### sqlmesh init
Initialize new project:
```bash
sqlmesh init duckdb       # With DuckDB
sqlmesh init postgres     # With PostgreSQL
sqlmesh init snowflake    # With Snowflake
```

### sqlmesh create_test
Generate test scaffolding:
```bash
sqlmesh create_test my_schema.my_model \
  --query my_schema.source_table \
  "SELECT * FROM my_schema.source_table LIMIT 5"
```

### sqlmesh diff
Compare environments:
```bash
sqlmesh diff dev prod
```

## Visualization Commands

### sqlmesh dag
View lineage DAG:
```bash
sqlmesh dag               # All models
sqlmesh dag my_model      # Specific model lineage
```

### sqlmesh ui
Launch web interface:
```bash
sqlmesh ui                # Default port 8000
sqlmesh ui --port 8080    # Custom port
```

## Information Commands

### sqlmesh info
Show project info:
```bash
sqlmesh info
```

### sqlmesh audit
Run data quality audits:
```bash
sqlmesh audit             # All audits
sqlmesh audit my_model    # Specific model
```

### sqlmesh fetchdf
Query and return DataFrame:
```bash
sqlmesh fetchdf "SELECT * FROM my_table LIMIT 10"
```

## Environment Management

### Virtual Environments
```bash
sqlmesh plan dev          # Create/update dev environment
sqlmesh plan staging      # Create/update staging
sqlmesh invalidate dev    # Invalidate dev environment
```

### Gateway Selection
```bash
sqlmesh plan --gateway prod
sqlmesh run --gateway snowflake_prod
```

## Common Flags

| Flag | Description |
|------|-------------|
| `--gateway` | Select connection gateway |
| `--start` | Start date for backfill |
| `--end` | End date for backfill |
| `--auto-apply` | Skip confirmation prompts |
| `--verbose` | Detailed output |
| `--help` | Show command help |
