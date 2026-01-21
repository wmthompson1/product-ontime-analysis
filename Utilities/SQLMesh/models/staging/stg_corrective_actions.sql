MODEL (
  name staging.stg_corrective_actions,
  kind SEED (
    path '$root/seeds/corrective_actions.csv'
  ),
  columns (
    action_id TEXT,
    incident_id TEXT,
    action_type TEXT,
    description TEXT,
    assigned_to TEXT,
    open_date DATE,
    due_date DATE,
    close_date DATE,
    status TEXT,
    effectiveness_score DOUBLE,
    created_date TIMESTAMP
  ),
  grain (action_id),
  audits (
    UNIQUE_VALUES(columns = (action_id)),
    NOT_NULL(columns = (action_id))
  )
);
