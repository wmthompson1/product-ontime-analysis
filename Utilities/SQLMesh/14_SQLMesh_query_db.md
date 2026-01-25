## 14 - Query duckDB

SQLMesh uses schema prefixes. Here's how to query:

For prod environment:

```
sqlmesh fetchdf "SELECT * FROM raw.corrective_actions"
```

For dev environment:

```
sqlmesh fetchdf "SELECT * FROM raw__dev.corrective_actions"
```
List all tables:

```
sqlmesh fetchdf "SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema LIKE '%raw%' OR table_schema LIKE '%staging%'"
```

The information_schema query shows 83 tables across raw, raw__dev, staging, and staging__dev schemas.