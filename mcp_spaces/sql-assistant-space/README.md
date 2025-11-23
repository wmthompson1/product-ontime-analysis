# SQL Assistant MCP Space

Purpose
- Small MCP Space that exposes a read-only HTTP API for schema discovery, safe SELECT queries, and EXPLAIN plans against a developer SQLite snapshot.

Security
- This Space is intended for dev/test use only. Do NOT point it at production data.
- Use the `AUTH_TOKEN` input (stored via MCP inputs or secrets) and send requests with `Authorization: Bearer <token>`.

Files
- `app.py` — Flask app exposing `/health`, `/schema`, `/query`, `/explain`.
- `Dockerfile`, `requirements.txt` — container settings.
- `space.json` — suggested manifest for registering the Space with MCP.

Run locally (dev)
1. Create a dev DB, e.g.:
```bash
python - <<'PY'
import sqlite3
conn=sqlite3.connect('data/dev.sqlite')
cur=conn.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, email TEXT)')
cur.execute("INSERT INTO users(name,email) VALUES('Alice','a@example.com')")
conn.commit()
conn.close()
PY
```
2. Run locally:
```bash
export AUTH_TOKEN=changeme
export DB_PATH=data/dev.sqlite
pip install -r requirements.txt
python app.py
```
3. Example query:
```bash
curl -s -H "Authorization: Bearer changeme" -H "Content-Type: application/json" \
  -d '{"sql":"SELECT * FROM users"}' http://localhost:8080/query
```

Pack as container
```bash
docker build -t sql-assistant-space:local .
docker run -e AUTH_TOKEN=changeme -e DB_PATH=/app/data/dev.sqlite -p 8080:8080 sql-assistant-space:local
```

Register with MCP
- Push the image to your registry and create a Space that uses the image and exposes port 8080.
- Add `AUTH_TOKEN` and `DB_PATH` as secure inputs when you register the Space. Use a dev-only SQLite snapshot inside the image or mounted volume.

Next steps / integrations
- Add an MCP tool that submits queries from VS Code UI to this Space.
- Add a simple web UI to the Space for interactive exploration.
