#!/usr/bin/env bash
set -euo pipefail
# scripts/register_graph.sh
# Register the gharial graph wiring for the persisted schema collections.

# Load .env if present
if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a; . .env; set +a
fi

DATABASE_HOST="${DATABASE_HOST:-http://localhost:8529}"
DATABASE_USERNAME="${DATABASE_USERNAME:-root}"
DATABASE_PASSWORD="${DATABASE_PASSWORD:-}"
DATABASE_NAME="${DATABASE_NAME:-manufacturing_graphs}"
GRAPH_NAME="${GRAPH_NAME:-manufacturing_schema_v1}"

if [ -z "${DATABASE_PASSWORD}" ]; then
  echo "Warning: DATABASE_PASSWORD is empty. Provide credentials or set in .env"
fi

URL="$DATABASE_HOST/_db/$DATABASE_NAME/_api/gharial"

echo "Registering graph '$GRAPH_NAME' in database '$DATABASE_NAME' on host $DATABASE_HOST"

PAYLOAD=$(cat <<JSON
{
  "name": "${GRAPH_NAME}",
  "edgeDefinitions": [
    {
      "collection": "${GRAPH_NAME}_edges",
      "from": ["${GRAPH_NAME}_nodes"],
      "to": ["${GRAPH_NAME}_nodes"]
    }
  ],
  "orphanCollections": []
}
JSON
)

curl -sS -u "${DATABASE_USERNAME}:${DATABASE_PASSWORD}" -H "Content-Type: application/json" \
  -X POST "$URL" -d "$PAYLOAD" | jq .

echo "Done."
