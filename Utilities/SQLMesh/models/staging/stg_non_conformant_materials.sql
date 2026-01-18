MODEL (
  name staging.stg_non_conformant_materials,
  kind SEED (
    path '$root/seeds/non_conformant_materials.csv'
  ),
  grain (ncm_id),
  audits (
    UNIQUE_VALUES(columns = (ncm_id)),
    NOT_NULL(columns = (ncm_id))
  )
);
