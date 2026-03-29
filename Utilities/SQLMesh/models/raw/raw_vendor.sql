/* DAG 1.1 — raw vendor table ingested from pre-stage SQL Server (faux Faker seed). */ /* PII: vendor.id  →  masked in staging.stg_vendor before any downstream consumption. */
MODEL (
  name raw.raw_vendor,
  kind SEED (
    path '$root/seeds/vendor_seed.csv'
  ),
  columns (
    id TEXT,
    name TEXT,
    contact_email TEXT,
    country TEXT
  ),
  grain (
    id
  ),
  audits (UNIQUE_VALUES(columns = (
      id
    )), NOT_NULL(columns = (
      id
  )))
)