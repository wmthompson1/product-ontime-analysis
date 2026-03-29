/* DAG 1.2 — staging.stg_part */ /* Applies masking rule: hash_sha256(pref_vendor)  per masking_matrix.csv row 1.2. */ /* pref_vendor_id must match staging.stg_vendor.vendor_id (referential integrity */ /* is preserved because both sides apply sha256 deterministically). */ /* buyer_email is NOT masked here — it becomes DAG 1.3 upon matrix update. */
MODEL (
  name staging.stg_part,
  kind FULL,
  columns (
    part_no TEXT,
    description TEXT,
    pref_vendor_id TEXT, /* sha256(raw.pref_vendor)  — PII-safe FK */
    unit_cost DOUBLE,
    buyer_email TEXT, /* not yet in matrix; unmasked until DAG 1.3 is certified */
    _dag_no TEXT,
    _masked_at TIMESTAMP
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
      pref_vendor_id
    ))
  )
);

SELECT
  p.part_no,
  p.description,
  SHA256(p.pref_vendor) AS pref_vendor_id,
  p.unit_cost,
  p.buyer_email,
  '1.2' AS _dag_no,
  CURRENT_TIMESTAMP AS _masked_at
FROM raw.raw_part AS p
/* Guard: only promote parts whose vendor has been certified in stg_vendor */
INNER JOIN staging.stg_vendor AS v
  ON SHA256(p.pref_vendor) = v.vendor_id