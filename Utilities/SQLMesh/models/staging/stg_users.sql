MODEL (
  name staging.stg_users,
  kind SEED (
    path '$root/seeds/users.csv'
  ),
  columns (
    user_id TEXT,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    role TEXT,
    department TEXT,
    hire_date DATE,
    is_active TEXT,
    created_date TIMESTAMP
  ),
  grain (user_id),
  audits (
    UNIQUE_VALUES(columns = (user_id)),
    NOT_NULL(columns = (user_id))
  )
);
