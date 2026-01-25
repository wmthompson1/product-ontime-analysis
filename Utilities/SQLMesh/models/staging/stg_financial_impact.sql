MODEL (
  name staging.stg_financial_impact,
  kind SEED (
    path '$root/seeds/financial_impact.csv'
  ),
  columns (
    impact_id TEXT,
    source_type TEXT,
    source_id TEXT,
    impact_type TEXT,
    impact_date DATE,
    direct_cost DOUBLE,
    indirect_cost DOUBLE,
    recovery_amount DOUBLE,
    approved_by TEXT,
    created_date TIMESTAMP
  ),
  grain (impact_id),
  audits (
    UNIQUE_VALUES(columns = (impact_id)),
    NOT_NULL(columns = (impact_id))
  )
);
