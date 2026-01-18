# SQLMesh Project Setup

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
mkdir my-sqlmesh-project
cd my-sqlmesh-project
sqlmesh init duckdb
```

This scaffolds:
```
my-sqlmesh-project/
├── config.yaml           # Database connection + model defaults
├── models/               # SQL model definitions
├── seeds/                # CSV/JSON data files
├── tests/                # Unit test files
├── macros/               # Reusable SQL logic
└── audits/               # Data quality audits
```

## Project Configuration (config.yaml)

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
      password: mypassword
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
      user: <username>
      password: <password>
      account: <account>
      warehouse: <warehouse>
      database: MYDB
      role: <role>

default_gateway: snowflake

model_defaults:
  dialect: snowflake
  start: 2024-01-01
```

## Environment Variables

Use environment variables for sensitive credentials:

```yaml
gateways:
  prod:
    connection:
      type: postgres
      host: ${POSTGRES_HOST}
      user: ${POSTGRES_USER}
      password: ${POSTGRES_PASSWORD}
      database: ${POSTGRES_DB}
```

## Multiple Environments

```yaml
gateways:
  dev:
    connection:
      type: duckdb
      database: dev.duckdb
  
  prod:
    connection:
      type: postgres
      host: prod-server.com
      # ...

default_gateway: dev
```

Switch environments:
```bash
sqlmesh plan --gateway prod
```
