MODEL (
  name staging.stg_daily_deliveries,
  kind SEED (
    path '$root/seeds/daily_deliveries.csv'
  ),
  grain (delivery_id),
  audits (
    UNIQUE_VALUES(columns = (delivery_id)),
    NOT_NULL(columns = (delivery_id))
  )
);
