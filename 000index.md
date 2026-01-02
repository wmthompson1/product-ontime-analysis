```markdown
cd bbb/20241019\ Python/
cd bbb/20241019\ Python/

cd /workspaces/20241019 Python/000index.md

/workspaces/20241019 Python/.env

---------------

the repo venv setup which does:

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

Or 
----------------
the repo helper script: run venv_setup.sh 
```

### 1. Create virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Run the application

## Running the app
To restart later: run .[venv_setup.sh](http://_vscodecontentref_/2) python3 .venv true 
then PORT=5000 
.venv/bin/python hf-space-inventory-sqlgen/app.py

## Running the app 1
PORT=5000 .venv/bin/python hf-space-inventory-sqlgen/app.py &> hf_app.out &

## Running the app 2
sleep 1 && curl -sS -D - http://127.0.0.1:5000/mcp/discover | head -n 20

## Running the app 3
sleep 1 && tail -n +1 hf_app.out | sed -n '1,120p'

## Running the app 4 (troubleshooting)
curl -sS http://127.0.0.1:5000/mcp/discover | python -m json.tool


## stopping the app
Stop the server: run 
pkill -f [app.py](http://_vscodecontentref_/2)" or kill <pid> (I can stop it for you if you want).

## stop the app 1
pkill -f 'hf-space-inventory-sqlgen/app.py' || pkill -f uvicorn || true
sleep 1

## stop the app 2
pgrep -af 'hf-space-inventory-sqlgen/app.py' || pgrep -af uvicorn || true

## stop the app 3 (verify non-response)
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5000/mcp/discover || echo 'no-response'

## ArangoDB Reminder


(Login: `root` and the password in your `.env` / `ARANGO_PASSWORD`.)
## TODO: schema/ folder

- Create a `schema/` folder (separate from the Gradio UI code) to hold canonical
	schema artifacts: table DDL, candidate keys, sample rows, and mapping metadata.
- Populate with a `README.md` and per-table YAML/JSON files that include `candidate_keys`.
cd "/workspaces/20241019 Python/"
cd /workspaces/20241019 Python/000index.md

/workspaces/20241019 Python/.env