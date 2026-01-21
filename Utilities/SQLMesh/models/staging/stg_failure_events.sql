MODEL (
  name staging.stg_failure_events,
  kind SEED (
    path '$root/seeds/failure_events.csv'
  ),
  grain (failure_id),
  audits (
    UNIQUE_VALUES(columns = (failure_id)),
    NOT_NULL(columns = (failure_id))
  )
);
