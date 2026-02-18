/*
cd /Users/williamthompson/bbb/20241019\ Python/Utilities/SQLMesh && sqlmesh fetchdf "SELECT action_id, incident_id, open_date, close_date, due_date FROM staging.stg_corrective_actions WHERE action_id <= 10 ORDER BY action_id"
*/
sqlmesh fetchdf "SELECT action_id, incident_id, open_date, close_date, due_date FROM staging.stg_corrective_actions WHERE action_id <= '10' ORDER BY action_id"

sqlmesh fetchdf "FROM staging.stg_corrective_actions"

sqlmesh fetchdf "SELECT node_id, concept_id, label, created_at FROM raw__dev.schema_nodes ORDER BY node_id LIMIT 10"

Physical tables use __dev suffix in development environment
Tables need to be backfilled first: sqlmesh plan → type y
Run queries with: sqlmesh fetchdf "SELECT ..."
Queries use actual seed column names from CSV files

sqlmesh fetchdf \
"SELECT \
    node_id, \
    concept_id, \
    label, \
    created_at \
FROM raw__dev.schema_nodes \
ORDER BY node_id \
LIMIT 10"