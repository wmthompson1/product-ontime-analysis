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

## Running the app
To restart later: run .[venv_setup.sh](http://_vscodecontentref_/1) python3 .venv true then PORT=5000 .venv/bin/python hf-space-inventory-sqlgen/app.py.

## ArangoDB Reminder


(Login: `root` and the password in your `.env` / `ARANGO_PASSWORD`.)
## TODO: schema/ folder

- Create a `schema/` folder (separate from the Gradio UI code) to hold canonical
	schema artifacts: table DDL, candidate keys, sample rows, and mapping metadata.
- Populate with a `README.md` and per-table YAML/JSON files that include `candidate_keys`.
cd "/workspaces/20241019 Python/"
cd /workspaces/20241019 Python/000index.md

/workspaces/20241019 Python/.env