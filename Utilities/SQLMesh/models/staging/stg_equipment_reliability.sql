MODEL (
  name staging.stg_equipment_reliability,
  kind SEED (
    path '$root/seeds/equipment_reliability.csv'
  ),
  columns (
    reliability_id TEXT,
    equipment_id TEXT,
    measurement_period DATE,
    mtbf_hours DOUBLE,
    target_mtbf DOUBLE,
    failure_count INTEGER,
    operating_hours DOUBLE,
    reliability_score DOUBLE,
    created_date TIMESTAMP
  ),
  grain (reliability_id),
  audits (
    UNIQUE_VALUES(columns = (reliability_id)),
    NOT_NULL(columns = (reliability_id))
  )
);
