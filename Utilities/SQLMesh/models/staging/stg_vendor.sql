/* DAG 1.1 — staging.stg_vendor */ /* Applies masking rule: hash_sha256(id)  per masking_matrix.csv row 1.1. */ /* vendor_id is the masked surrogate; original id is never promoted downstream. */
MODEL (
  name staging.stg_vendor,
  kind FULL,
  columns (
    vendor_id TEXT, /* sha256(raw.id)  — PII-safe surrogate */
    name TEXT,
    contact_email TEXT,
    country TEXT,
    _dag_no TEXT,
    _masked_at TIMESTAMP
  ),
  grain (
    vendor_id
  ),
  audits (UNIQUE_VALUES(columns = (
      vendor_id
    )), NOT_NULL(columns = (
      vendor_id
  )))
);

SELECT
  LOWER(SHA256(CAST(id AS VARCHAR))) AS vendor_id,
  name,
  contact_email,
  country,
  '1.1' AS _dag_no,
  CURRENT_TIMESTAMP AS _masked_at
FROM raw.raw_vendor