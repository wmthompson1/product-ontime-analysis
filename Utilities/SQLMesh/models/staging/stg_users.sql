MODEL (
  name staging.stg_users,
  kind SEED (
    path '$root/seeds/users.csv'
  ),
  grain (user_id),
  audits (
    UNIQUE_VALUES(columns = (user_id)),
    NOT_NULL(columns = (user_id))
  )
);
