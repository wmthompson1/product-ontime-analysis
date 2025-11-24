from flask import Flask, request, jsonify, abort
import os
import sqlite3
import re

app = Flask(__name__)

AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")
DB_PATH = os.getenv("DB_PATH", "data/dev.sqlite")
MAX_ROWS = int(os.getenv("MAX_ROWS", "200"))

_SELECT_RE = re.compile(r"^\s*(SELECT|WITH|PRAGMA|EXPLAIN)\b", re.IGNORECASE)
_DISALLOWED_RE = re.compile(r";|\b(INSERT|UPDATE|DELETE|DROP|ALTER|ATTACH|DETACH|VACUUM)\b", re.IGNORECASE)


def require_auth():
    if AUTH_TOKEN:
        token = request.headers.get("Authorization", "")
        if token != f"Bearer {AUTH_TOKEN}":
            abort(401)


def get_conn():
    if not os.path.exists(DB_PATH):
        # create an empty sqlite file so endpoints return structured errors instead of file not found
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        open(DB_PATH, "a").close()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/schema")
def schema():
    require_auth()
    conn = get_conn()
    cur = conn.cursor()
    tables = []
    cur.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table','view') ORDER BY name")
    for row in cur.fetchall():
        name = row["name"]
        ttype = row["type"]
        cols = []
        try:
            cur2 = conn.execute(f"PRAGMA table_info('{name}')")
            for c in cur2.fetchall():
                cols.append({
                    "cid": c[0],
                    "name": c[1],
                    "type": c[2],
                    "notnull": bool(c[3]),
                    "dflt_value": c[4],
                    "pk": bool(c[5])
                })
        except Exception:
            cols = []
        tables.append({"name": name, "type": ttype, "columns": cols})
    return jsonify({"tables": tables})


@app.route("/query", methods=["POST"])
def query():
    require_auth()
    payload = request.get_json(force=True) or {}
    sql = payload.get("sql")
    if not sql:
        return jsonify({"error": "missing 'sql' in request body"}), 400
    if _DISALLOWED_RE.search(sql):
        return jsonify({"error": "Only read-only SELECT/EXPLAIN/PRAGMA queries are allowed."}), 400
    if not _SELECT_RE.match(sql):
        return jsonify({"error": "Only SELECT/WITH/PRAGMA/EXPLAIN queries are allowed."}), 400
    limit = int(payload.get("limit", MAX_ROWS))
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(sql)
        rows = cur.fetchmany(limit)
        columns = [desc[0] for desc in cur.description] if cur.description else []
        results = [dict(zip(columns, r)) for r in rows]
        return jsonify({"columns": columns, "rows": results, "count": len(results)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/explain", methods=["POST"])
def explain():
    require_auth()
    payload = request.get_json(force=True) or {}
    sql = payload.get("sql")
    if not sql:
        return jsonify({"error": "missing 'sql' in request body"}), 400
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("EXPLAIN QUERY PLAN " + sql)
        rows = [list(r) for r in cur.fetchall()]
        return jsonify({"plan": rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    PORT = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=PORT, debug=False)
