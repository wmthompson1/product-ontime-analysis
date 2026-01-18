MODEL (
  name staging.stg_production_schedule,
  kind SEED (
    path '$root/seeds/production_schedule.csv'
  ),
  grain (schedule_id),
  audits (
    UNIQUE_VALUES(columns = (schedule_id)),
    NOT_NULL(columns = (schedule_id))
  )
);
