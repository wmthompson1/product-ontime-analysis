MODEL (
  name staging.stg_manufacturing_acronyms,
  kind SEED (
    path '$root/seeds/manufacturing_acronyms.csv'
  ),
  columns (
    acronym_id TEXT,
    acronym TEXT,
    full_name TEXT,
    category TEXT,
    description TEXT,
    created_date TIMESTAMP
  ),
  grain (acronym_id),
  audits (
    UNIQUE_VALUES(columns = (acronym_id)),
    NOT_NULL(columns = (acronym_id))
  )
);
