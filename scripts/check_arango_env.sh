#!/usr/bin/env bash
set -euo pipefail

# scripts/check_arango_env.sh
# Purpose: detect legacy Arango env vars that start with the prefix
# "database_" (case-insensitive) in the repository `.env` file and
# the current shell environment. Exit non-zero if any are found.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"

found=0

echo "Checking for legacy 'database_' prefixed variables (case-insensitive)"
echo "Repository root: $REPO_ROOT"

if [ -f "$ENV_FILE" ]; then
  echo "Scanning $ENV_FILE"
  env_matches="$(grep -E -i '^[[:space:]]*database_' "$ENV_FILE" || true)"
  if [ -n "$env_matches" ]; then
    echo "Found legacy keys in $ENV_FILE:"
    echo "$env_matches" | sed 's/^/  /'
    found=1
  else
    echo "No legacy keys found in $ENV_FILE"
  fi
else
  echo "$ENV_FILE not found; skipping file check"
fi

echo "Scanning current shell environment"
env_vars="$(env | grep -E -i '^database_' || true)"
if [ -n "$env_vars" ]; then
  echo "Found legacy environment variables in current shell:"
  echo "$env_vars" | sed 's/^/  /'
  found=1
else
  echo "No legacy environment variables found in current shell"
fi

if [ "$found" -eq 1 ]; then
  echo "\nERROR: Legacy 'database_' prefixed variables were found. Please rename to the canonical ARANGO_ or other project-specific prefix."
  exit 1
fi

echo "\nOK: No legacy 'database_' variables detected."
exit 0
