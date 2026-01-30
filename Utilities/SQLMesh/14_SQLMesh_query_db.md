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

## How It Works


**sqlmesh plan dev** - Creates/updates dev environment with your changes

Physical tables created in raw__dev, staging__dev schemas
Virtual layer points dev views to those tables
sqlmesh plan prod - Promotes dev to prod

If data already exists (non-breaking change): Virtual layer promotion only
If breaking change: Backfills physical tables, then promotes
Key insight: The "virtual layer" is what makes this efficient. When you promote non-breaking changes (like adding columns, renaming), SQLMesh just updates the view definitions pointing to the same physical data - no expensive data copying.

Your local promotion showed this perfectly:

"SKIP: No physical layer updates" = data unchanged
"Promoting 11 snapshots" = virtual layer views updated to match dev
This is the "digital twin" pattern - safe development with virtual environments before touching prod.