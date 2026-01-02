#!/usr/bin/env bash
set -euo pipefail

# Wrapper stored in `.github/scripts/check-arango-env.sh` so GitHub Actions
# workflow can call it. The real check lives at `scripts/check_arango_env.sh`.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHECK_SCRIPT="$REPO_ROOT/scripts/check_arango_env.sh"

if [ ! -f "$CHECK_SCRIPT" ]; then
  echo "ERROR: expected $CHECK_SCRIPT to exist."
  exit 2
fi

if [ ! -x "$CHECK_SCRIPT" ]; then
  chmod +x "$CHECK_SCRIPT" || true
fi

exec "$CHECK_SCRIPT" "$@"