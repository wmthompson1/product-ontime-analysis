MODEL (
  name staging.stg_corrective_actions,
  kind SEED (
    path '$root/seeds/corrective_actions.csv'
  ),
  grain (action_id),
  audits (
    UNIQUE_VALUES(columns = (action_id)),
    NOT_NULL(columns = (action_id))
  )
);
