/* DAG 1.2 — raw part table ingested from pre-stage SQL Server (faux Faker seed). */ /* PII: part.pref_vendor (FK → vendor.id) →  masked in staging.stg_part. */ /* Note: buyer_email is present but becomes DAG 1.3 when matrix is updated. */
MODEL (
  name raw.raw_part,
  kind SEED (
    path '$root/seeds/part_seed.csv'
  ),
  columns (
    part_no TEXT,
    description TEXT,
    pref_vendor TEXT,
    unit_cost DOUBLE,
    buyer_email TEXT
  ),
  grain (
    part_no
  ),
  audits (
    UNIQUE_VALUES(columns = (
      part_no
    )),
    NOT_NULL(columns = (
      part_no
    )),
    NOT_NULL(columns = (
      pref_vendor
    ))
  )
)