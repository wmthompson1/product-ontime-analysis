# 02 - SQLMesh Project Setup

## test 01/12/26
# Install
pip install --upgrade sqlmesh

# From mac terminal, go to project root and run plan
cd "/Users/williamthompson/bbb/20241019 Python"
sqlmesh plan --gateway local
# If you need more logs:
SQLMESH_LOG_LEVEL=DEBUG sqlmesh plan --gateway local

## Initialize a New Project

```bash
# Create project directory
mkdir my-sqlmesh-project
cd my-sqlmesh-project

# Initialize with DuckDB (local development)
sqlmesh init duckdb
```

### Available Templates

```bash
sqlmesh init duckdb      # Local development
sqlmesh init postgres    # PostgreSQL
sqlmesh init snowflake   # Snowflake
sqlmesh init bigquery    # BigQuery
sqlmesh init databricks  # Databricks
sqlmesh init redshift    # Redshift
sqlmesh init spark       # Apache Spark
sqlmesh init dbt         # Import existing dbt project
```

## Project Structure

After initialization, you'll have:

```
my-sqlmesh-project/
├── config.yaml           # Database connections & settings
├── models/               # SQL model definitions
│   ├── full_model.sql
│   ├── incremental_model.sql
│   └── seed_model.sql
├── seeds/                # Static CSV/JSON data
│   └── seed_data.csv
├── tests/                # Unit tests
│   └── test_full_model.yaml
├── macros/               # Reusable SQL macros
│   └── __init__.py
├── audits/               # Data quality checks
│   └── assert_positive_order_ids.sql
└── logs/                 # Execution logs
```

## Configuration (config.yaml)

### DuckDB (Local Development)

```yaml
gateways:
  local:
    connection:
      type: duckdb
      database: db.duckdb

default_gateway: local

model_defaults:
  dialect: duckdb
  start: 2024-01-01
  cron: '@daily'
```

### PostgreSQL

```yaml
gateways:
  postgres:
    connection:
      type: postgres
      host: localhost
      port: 5432
      user: myuser
      password: ${POSTGRES_PASSWORD}  # Environment variable
      database: mydb

default_gateway: postgres

model_defaults:
  dialect: postgres
  start: 2024-01-01
```

### Snowflake

```yaml
gateways:
  snowflake:
    connection:
      type: snowflake
      account: ${SNOWFLAKE_ACCOUNT}
      user: ${SNOWFLAKE_USER}
      password: ${SNOWFLAKE_PASSWORD}
      warehouse: COMPUTE_WH
      database: MY_DATABASE
      role: MY_ROLE

default_gateway: snowflake

model_defaults:
  dialect: snowflake
  start: 2024-01-01
```

### BigQuery

```yaml
gateways:
  bigquery:
    connection:
      type: bigquery
      project: my-gcp-project
      location: US
      # Uses default application credentials

default_gateway: bigquery

model_defaults:
  dialect: bigquery
  start: 2024-01-01
```

## Environment Variables

Use `${VAR_NAME}` syntax to reference environment variables:

```yaml
gateways:
  prod:
    connection:
      type: postgres
      host: ${DB_HOST}
      user: ${DB_USER}
      password: ${DB_PASSWORD}
      database: ${DB_NAME}
```

Set variables in your shell or `.env` file:

```bash
export DB_HOST=prod-server.example.com
export DB_USER=analytics
export DB_PASSWORD=secret123
export DB_NAME=warehouse
```

## Multiple Gateways

Configure different environments:

```yaml
gateways:
  dev:
    connection:
      type: duckdb
      database: dev.duckdb
  
  staging:
    connection:
      type: postgres
      host: staging-db.example.com
      # ...
  
  prod:
    connection:
      type: snowflake
      account: my-account
      # ...

default_gateway: dev
```

Switch between gateways:

```bash
sqlmesh plan --gateway staging
sqlmesh run --gateway prod
```

## Model Defaults

Configure default behavior for all models:

```yaml
model_defaults:
  dialect: duckdb           # SQL dialect
  start: 2024-01-01         # Backfill start date
  cron: '@daily'            # Default schedule
  owner: data-team          # Default owner
  tags:
    - analytics
```

## Linting Rules

Enable SQL linting:

```yaml
linter:
  enabled: true
  rules:
    - ambiguousorinvalidcolumn
    - invalidselectstarexpansion
    - noambiguousprojections
    - nounreferencedctes
```

## Recommended Directory Organization

For larger projects:

```
my-project/
├── config.yaml
├── models/
│   ├── staging/           # Raw data cleaning
│   │   ├── stg_orders.sql
│   │   └── stg_customers.sql
│   ├── intermediate/      # Business logic
│   │   └── int_orders_enriched.sql
│   └── marts/             # Final analytics
│       ├── fct_orders.sql
│       └── dim_customers.sql
├── seeds/
│   └── country_codes.csv
├── tests/
│   ├── staging/
│   └── marts/
├── macros/
│   └── date_utils.py
└── audits/
    └── custom_audits.sql
```

## Verify Setup

```bash
# Check project info
sqlmesh info

# Validate configuration
sqlmesh plan --dry-run
```

## Next Steps

Continue to [03_Models_Basics.md](03_Models_Basics.md) to learn about creating models.
