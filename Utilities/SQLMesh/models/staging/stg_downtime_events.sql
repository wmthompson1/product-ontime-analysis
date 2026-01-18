MODEL (
  name staging.stg_downtime_events,
  kind SEED (
    path '$root/seeds/downtime_events.csv'
  ),
  grain (event_id),
  audits (
    UNIQUE_VALUES(columns = (event_id)),
    NOT_NULL(columns = (event_id))
  )
);
