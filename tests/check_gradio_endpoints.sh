#!/usr/bin/env bash
set -euo pipefail
BASE="http://127.0.0.1:5000"

echo "1) Schema Tab - Refresh table list"
curl -sS "$BASE/mcp/tools/get_db_tables" | python -m json.tool || true

echo "\n2) Schema Tab - View all tables (DDL count)"
curl -sS "$BASE/mcp/tools/get_all_ddl" | python - <<'PY'
import sys,json
j=json.load(sys.stdin)
if isinstance(j.get('tables',[]), list):
    print('tables_count:', len(j.get('tables',[])))
elif isinstance(j.get('ddl',{}), dict):
    print('ddl_count:', len(j.get('ddl',{})))
else:
    print('unknown structure')
PY

echo "\n3) Ground Truth SQL - list categories"
curl -sS "$BASE/mcp/tools/get_saved_categories" | python -m json.tool || true

echo "\n4) Ground Truth SQL - fetch queries for quality_control"
curl -sS "$BASE/mcp/tools/get_saved_queries?category_id=quality_control" | python -m json.tool || true

echo "\n5) Copilot Context - assemble preview (fetch a couple of DDLs + first query)"
# get table list
TABLES_JSON=$(curl -sS "$BASE/mcp/tools/get_db_tables" || echo '{}')
TABLE1=$(echo "$TABLES_JSON" | python - <<'PY'
import sys,json
j=json.load(sys.stdin)
if j.get('tables'):
    print(j['tables'][0])
else:
    print('')
PY
)
TABLE2=$(echo "$TABLES_JSON" | python - <<'PY'
import sys,json
j=json.load(sys.stdin)
if j.get('tables') and len(j['tables'])>1:
    print(j['tables'][1])
else:
    print('')
PY
)

if [ -n "$TABLE1" ]; then
  echo "-- DDL for $TABLE1 --"
  curl -sS --get "$BASE/mcp/tools/get_table_ddl" --data-urlencode "table_name=$TABLE1" | python -m json.tool || true
fi
if [ -n "$TABLE2" ]; then
  echo "\n-- DDL for $TABLE2 --"
  curl -sS --get "$BASE/mcp/tools/get_table_ddl" --data-urlencode "table_name=$TABLE2" | python -m json.tool || true
fi

echo "\n-- Ground truth example (quality_control first query) --"
curl -sS "$BASE/mcp/tools/get_saved_queries?category_id=quality_control" | python - <<'PY'
import sys,json
j=json.load(sys.stdin)
qs=j.get('queries',[])
if qs:
    print(qs[0]['name'])
    print('\n'+qs[0]['sql'])
else:
    print('no queries found')
PY


echo "\nTest script complete. If table list is empty, ensure the app has a live DB connection and that the DB contains the schema."