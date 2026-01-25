MODEL (
  name staging.stg_non_conformant_materials,
  kind SEED (
    path '$root/seeds/non_conformant_materials.csv'
  ),
  columns (
    ncm_id TEXT,
    incident_date DATE,
    product_line TEXT,
    supplier_id TEXT,
    material_type TEXT,
    defect_description TEXT,
    quantity_affected INTEGER,
    severity TEXT,
    root_cause TEXT,
    cost_impact DOUBLE,
    status TEXT,
    created_date TIMESTAMP
  ),
  grain (ncm_id),
  audits (
    UNIQUE_VALUES(columns = (ncm_id)),
    NOT_NULL(columns = (ncm_id))
  )
);
