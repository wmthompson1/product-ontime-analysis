# SPARQL Getting Started 001 — Your First Query

A hands-on, runnable walkthrough. By the end you will have run a real SPARQL
query against the manufacturing database through Ontop, seen it return a real
number, and proven that number matches the governed SQL it is built on.

We use one query the project already ships:
`poc/ontop-ontology-poc/queries/routing_total_run_hours.rq` — "what is the total
routing-step run time scheduled across every work order?"

> Every command below is copy-pasteable and was run to produce the outputs shown.
> Run them **from the repository root** (`/home/runner/workspace`).

---

## 1. The one big idea

Ontop does **not** copy your data into a graph database. It is a *virtual*
knowledge graph. You ask a question in SPARQL (the query language for graphs),
and Ontop **rewrites your SPARQL into SQL**, runs that SQL against the ordinary
SQLite file (`manufacturing.db`), and hands the answer back as if a graph had
answered it.

```
 your SPARQL (.rq)                          plain SQLite
        │                                        ▲
        ▼                                        │
  ┌───────────┐   rewrites SPARQL → SQL   ┌──────────────┐
  │   Ontop   │ ───────────────────────► │ manufacturing │
  │ (virtual) │ ◄─────────────────────── │     .db        │
  └───────────┘        rows back          └──────────────┘
        │
        ▼
   CSV answer
```

No data is moved. No triplestore. The SQL database stays the single source of
truth; Ontop is only a **publishing / interoperability layer** on top of it.

---

## 2. The four ingredients of a query

Every Ontop query needs four inputs. Here are the real files for this showcase:

| Ingredient | What it is | File |
|---|---|---|
| **Ontology** (`.ttl`) | The vocabulary — the *nouns and adjectives* (`:Operation`, `:runHours`) | `poc/ontop-ontology-poc/ontology/shop_floor_routing.ttl` |
| **Mapping** (`.obda`) | Wires each vocabulary term to a **SQL SELECT** over real tables | `poc/ontop-ontology-poc/mapping/shop_floor_routing.obda` |
| **Properties** (`.properties`) | The database connection (JDBC URL) | `poc/ontop-ontology-poc/mapping/shop_floor_routing.properties` |
| **Query** (`.rq`) | The SPARQL question you want answered | `poc/ontop-ontology-poc/queries/routing_total_run_hours.rq` |

### The mapping is the heart of it

Open `mapping/shop_floor_routing.obda`. The key line says: for every row of this
SQL query, mint one `:Operation` and attach its `run_hrs` value as `:runHours`.

```
target   :operation/{rowid_pk} a :Operation ; :runHours {run_hrs}^^xsd:double ; ...
source   SELECT o.rowid_pk, o.wo_id, o.run_hrs, ...
         FROM operation o JOIN work_order wo ON wo.wo_id = o.wo_id
```

So the graph term `:runHours` is literally the `operation.run_hrs` column, exposed
through a governed two-table join (`operation JOIN work_order`). That join **is**
the governance — only operations that belong to a real work order are published.

---

## 3. The query, explained

`queries/routing_total_run_hours.rq`:

```sparql
PREFIX : <http://example.org/manufacturing/routing#>

SELECT (SUM(?run) AS ?totalRunHours) (COUNT(?op) AS ?operations)
WHERE {
  ?op :runHours ?run .
}
```

Read it as three parts:

- **`PREFIX : <…routing#>`** — a shorthand. `:runHours` means the full IRI
  `http://example.org/manufacturing/routing#runHours`. Prefixes just save typing.
- **`WHERE { ?op :runHours ?run . }`** — the *pattern* to match. `?op` and `?run`
  are variables (the `?` marks them). Read the line as a sentence:
  *"find every thing `?op` that has a `:runHours` value `?run`."* Each match is one
  routing operation and its run hours. This one-line pattern is called a **triple
  pattern** (subject — predicate — object).
- **`SELECT (SUM(?run) AS ?totalRunHours) (COUNT(?op) AS ?operations)`** — what to
  return. Add up all the `?run` values, and count how many `?op` matched.

It is deliberately **scalar** (no `GROUP BY`) so Ontop's rewritten SQL stays
simple and SQLite-friendly.

---

## 4. Run it

### One-time setup (only if the toolchain is missing)

The query runs on the **Ontop command-line tool** (a Java program). It lives in
`poc/ontop-ontology-poc/tools/` and is **gitignored** (not committed). If that
folder is empty, download it once:

```bash
python3 replit_integrations/ontop_poc_setup.py
```

Check you are ready (this environment already has both):

```bash
java -version                                                   # need Java (JDK 19)
ls poc/ontop-ontology-poc/tools/ontop-cli-5.5.0/ontop           # the Ontop CLI
```

### The command

```bash
poc/ontop-ontology-poc/tools/ontop-cli-5.5.0/ontop query \
  -m poc/ontop-ontology-poc/mapping/shop_floor_routing.obda \
  -t poc/ontop-ontology-poc/ontology/shop_floor_routing.ttl \
  -p poc/ontop-ontology-poc/mapping/shop_floor_routing.properties \
  -q poc/ontop-ontology-poc/queries/routing_total_run_hours.rq
```

The five flags map one-to-one to the four ingredients (plus the sub-command):

| Flag | Ingredient |
|---|---|
| `query` | run in one-shot query mode |
| `-m` | **m**apping (`.obda`) |
| `-t` | on**t**ology (`.ttl`) |
| `-p` | **p**roperties (DB connection) |
| `-q` | the SPARQL **q**uery (`.rq`) |

Add `-o results.csv` to write the answer to a file instead of the screen.

### What you'll see

The first ~13 seconds is the Java VM booting and Ontop loading the mapping. Then,
on the **last line**, the answer:

```
totalRunHours,operations
669.55,502
```

**669.55 run hours across 502 routed operations.** That is your first answer from
a virtual knowledge graph. 🎉

> **The warnings are normal — ignore them.** Before the answer you'll see lines
> like these. None are errors in *your* query; they're Ontop describing the
> schema it found:
> - `Axiom does not belong to OWL 2 QL: … xsd:double` — Ontop's fast profile
>   doesn't formally model decimals; it still answers correctly.
> - `Cannot find table "service"/"part"/… for foreign key` — this mapping only
>   touches `operation` + `work_order`; foreign keys pointing at other tables are
>   simply not in play here.
> - `primary key … downgraded to a unique constraint` — a harmless note about a
>   nullable key column.

---

## 5. Prove the number is real (SPARQL == governed SQL)

The whole point of this project is that the graph answer must **equal** the
answer from the plain governed SQL it's built on. The mapping's join was
`operation JOIN work_order on wo_id`, so run exactly that in SQL — **read-only**:

```bash
sqlite3 -readonly hf-space-inventory-sqlgen/app_schema/manufacturing.db \
  "SELECT SUM(op.run_hrs), COUNT(*)
   FROM work_order wo JOIN operation op ON op.wo_id = wo.wo_id;"
```

Output:

```
669.55|502
```

Same numbers. The SPARQL path and the SQL path agree — that is a *parity proof*.
(Equivalent Python, also read-only:)

```bash
python3 -c "import sqlite3; c=sqlite3.connect('file:hf-space-inventory-sqlgen/app_schema/manufacturing.db?mode=ro', uri=True); print(c.execute('SELECT SUM(op.run_hrs), COUNT(*) FROM work_order wo JOIN operation op ON op.wo_id=wo.wo_id').fetchone())"
# -> (669.55, 502)
```

---

## 6. How the automated check wraps this

You just did by hand what `poc/ontop-ontology-poc/shop_floor_routing_parity_check.py`
does automatically. It:

1. takes a **read-only snapshot** of the live database (so it never even opens the
   live file for writing),
2. calls the exact same Ontop command through a tiny helper, `run_sparql()`:

   ```python
   def run_sparql(props, query_file, out_csv):
       cmd = [ONTOP, "query", "-m", MAPPING, "-t", ONTOLOGY,
              "-p", props, "-q", query_file, "-o", out_csv]
       res = subprocess.run(cmd, capture_output=True, text=True, cwd=POC_DIR)
       if res.returncode != 0:
           raise SystemExit(f"ontop query failed for {query_file}")
       return out_csv
   ```

3. runs the governed SQL on the same snapshot, and
4. **asserts** the two answers are equal (failing loudly if they ever drift).

Run the whole thing end-to-end:

```bash
python3 poc/ontop-ontology-poc/shop_floor_routing_parity_check.py
```

> `run_sparql()` shells out to the Ontop **CLI** — it does *not* hit an HTTP
> endpoint. (There *is* a separate live-HTTP-endpoint demo in
> `sparql_endpoint.py` + `endpoint_smoke_test.py`, but the parity checks use the
> CLI subprocess route shown here.)

---

## 7. Try it yourself

1. **Change the fact.** Copy the query and swap `:runHours` for `:setupHours`
   (both are defined in the `.ttl`). Re-run — you now get total *setup* hours.

2. **Ask about one work order.** Run the sibling query:

   ```bash
   poc/ontop-ontology-poc/tools/ontop-cli-5.5.0/ontop query \
     -m poc/ontop-ontology-poc/mapping/shop_floor_routing.obda \
     -t poc/ontop-ontology-poc/ontology/shop_floor_routing.ttl \
     -p poc/ontop-ontology-poc/mapping/shop_floor_routing.properties \
     -q poc/ontop-ontology-poc/queries/work_order_step_count.rq
   ```

   It counts the routing steps of work order **WO-240003** (answer: **6**).
   Open that `.rq` and notice this line:

   ```sparql
   ?op :partOfWorkOrder <http://example.org/manufacturing/routing#workorder/WO-240003> .
   ```

   **Gotcha worth remembering:** that work-order IRI contains a `/`
   (`…#workorder/WO-240003`). A `/` is illegal inside a prefixed name, so you
   **cannot** write it as `:workorder/WO-240003` — you must spell out the full IRI
   in angle brackets `< >`, as shown. This bites everyone once.

3. **Break it on purpose.** Change `SUM(?run)` to `SUM(?nope)` (an undefined
   variable) and re-run. Watch how the answer changes — a good way to feel how the
   `WHERE` pattern drives the result.

---

## 8. Read-only safety (why you can experiment freely)

- The manual properties file opens the database with `?open_mode=1`
  (`SQLITE_OPEN_READONLY`), and Ontop only ever issues `SELECT`s.
- The automated parity check goes further: it reads from a throwaway **snapshot**,
  never the live file.
- The SQL verification commands above use `-readonly` / `?mode=ro`.

So nothing here can modify your data — query away.

---

## Where things live

- **Learning notes (this folder):** `poc/sparql-getting-started/`
- **Runnable POC:** `poc/ontop-ontology-poc/`
  - `ontology/` — the `.ttl` vocabularies
  - `mapping/` — the `.obda` mappings + `.properties`
  - `queries/` — the `.rq` SPARQL queries
  - `*_parity_check.py` — the automated SPARQL-vs-SQL proofs
  - `tools/` — the downloaded Ontop CLI (gitignored)
- **Setup:** `replit_integrations/ontop_poc_setup.py`
- **Full POC docs:** `poc/ontop-ontology-poc/README.md`

## Next steps / ideas

- Read the `README.md` in `poc/ontop-ontology-poc/` for all six governed
  showcases (capacity, routing, inventory, on-time delivery, OEE, demand).
- Learn the `OPTIONAL { }` pattern (SPARQL's LEFT JOIN) — see the on-time delivery
  showcase for how "absence of data" is handled safely.
- Try the live HTTP endpoint: `python3 poc/ontop-ontology-poc/sparql_endpoint.py`
  then POST SPARQL to `http://127.0.0.1:8090/sparql`.
