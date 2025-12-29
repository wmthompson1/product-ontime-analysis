# Docker Compose (development)

This repository provides a simple, developer-friendly `docker-compose.yml` at the repository root to run a local development stack (Postgres + ArangoDB).

Quick overview

Getting started (local machine)

1. Copy `.env.example` to `.env` and fill in any required values (do NOT commit `.env`).

```bash
cp .env.example .env
# edit .env and set ARANGO_ROOT_PASSWORD, DATABASE_HOST, etc.
```

2. Start the stack

```bash
docker compose up -d
# view logs
docker compose logs -f arangodb
```

3. Verify services

```bash
# check containers
docker ps --filter "name=arangodb" --filter "name=postgres"
# ArangoDB HTTP API (replace creds from .env)
curl -u root:${ARANGO_ROOT_PASSWORD:-arangopass} http://localhost:8529/_api/version
```

Notes about running inside containers vs host

Persisting the schema graph (quick)

1. With the stack running and `.env` configured, run the persister from your host (preferred) or inside the workspace container:

```bash
# host
set -a && source .env && set +a
python3 scripts/persist_to_arango.py

# or inside the workspace container (if you use devcontainer), ensure DATABASE_HOST=http://host.docker.internal:8529
```

2. The persister will create node and edge collections and (by default) register the gharial graph. Use `--no-register` to skip registration if you prefer to run registration separately.

Graph registration helper

Cleaning up

```bash
docker compose down
docker volume ls
docker volume rm product_ontime_pgdata product_ontime_arangodata  # only if you intend to remove persisted data
```

Troubleshooting

Best practices
Note: this repository already lists `.env*` in `.gitignore`. Prefer setting `DATABASE_PASSWORD` in your local `.env` (or CI secrets). The root `docker-compose.yml` uses `DATABASE_PASSWORD` as the source for ArangoDB's root password by default.
