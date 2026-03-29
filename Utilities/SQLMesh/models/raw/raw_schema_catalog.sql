MODEL (
  name raw.schema_catalog,
  kind SEED (
    path '$root/seeds/raw_schema_catalog.csv'
  ),
  columns (
    table_name TEXT,
    column_name TEXT,
    data_type TEXT,
    is_nullable BOOLEAN,
    is_primary_key BOOLEAN,
    is_shadow_key BOOLEAN,
    semantic_concept TEXT
  ),
  grain (table_name, column_name)
);

/* Schema Catalog Seed */ /* Column-level metadata extracted from SQLMesh physical layer */ /* Used for semantic layer binding, type validation, and join safety checks */