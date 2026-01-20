MODEL (
  name staging.stg_users,
  kind FULL
);

SELECT
  id,
  name,
  email
FROM raw.users;
