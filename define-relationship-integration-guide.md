# Define Relationship Tab — Integration Guide

This document lists every file, object, and backend endpoint required to add the
**Define Data Relationship** panel to the private repo's app.

---

## 1. Frontend Source Files

All four files live in
`artifacts/mockup-sandbox/src/components/mockups/graph-relationship/`.
Copy the whole directory as a unit.

| File | Purpose |
|---|---|
| `DefineRelationship.tsx` | Root React component — all UI, state, and API calls |
| `graphApi.ts` | Two helper functions: `undoEdge()` and `fetchGraphStats()` |
| `entityDisplay.ts` | Types (`EntityRecord`, `GroupedResults`, `SearchResult`) and `getFirstEntityDisplay()` helper |
| `fixtures.ts` | Mock/fallback data used when the API is unavailable during development |

### Entry point wiring (Vite standalone build)

| File | Purpose |
|---|---|
| `artifacts/mockup-sandbox/src/define-relationship-main.tsx` | Vite entry point — mounts `<DefineRelationship />` into `#root` |
| `artifacts/mockup-sandbox/index-define-relationship.html` | HTML shell (`<div id="root">`) used as Rollup input |
| `artifacts/mockup-sandbox/src/index.css` | Tailwind base styles imported by the entry point |

> If you are embedding the component inside an existing React app instead of building it standalone, you only need the four component files above — not the entry point or HTML shell.

---

## 2. Vite Build Config (standalone build only)

File: `artifacts/mockup-sandbox/vite.define-relationship.config.ts`

Key settings to replicate in your repo:

```ts
{
  base: "/define-relationship/",
  build: {
    outDir: "<your-static-dir>/define-relationship",
    emptyOutDir: true,              // wipes the output dir on each build
    rollupOptions: {
      input: "index-define-relationship.html",
    },
  },
}
```

**Important:** `emptyOutDir: true` deletes `index.html` on every build.
The output file is named `index-define-relationship.html`.
Your server must check for that filename as a fallback when `index.html` is absent
(see Section 4 — Static File Serving).

Build command:
```bash
cd artifacts/mockup-sandbox
npx vite build --config vite.define-relationship.config.ts
```

---

## 3. Static Build Output

After building, three files land in `<your-static-dir>/define-relationship/`:

```
index-define-relationship.html          ← HTML shell (no index.html)
assets/index-define-relationship-[hash].js
assets/index-define-relationship-[hash].css
```

The hash in the JS/CSS filenames changes on every build; the HTML shell always
references the correct hash automatically.

---

## 4. Static File Serving (backend)

Both the FastAPI app and the Flask proxy need a route that checks for
`index-define-relationship.html` when `index.html` is not present.

### FastAPI / app.py pattern

```python
_dr_static = os.path.join(os.path.dirname(__file__), "static", "define-relationship")

def _dr_index_html() -> str | None:
    for name in ("index.html", "index-define-relationship.html"):
        path = os.path.join(_dr_static, name)
        if os.path.isfile(path):
            with open(path, "r") as f:
                return f.read()
    return None

@app.get("/define-relationship/", response_class=HTMLResponse)
async def serve_define_relationship_root():
    html = _dr_index_html()
    if html:
        return html
    raise HTTPException(status_code=404, detail="Define Relationship build not found")

@app.get("/define-relationship/{path:path}")
async def serve_define_relationship_asset(path: str):
    from fastapi.responses import FileResponse
    import mimetypes
    file_path = os.path.join(_dr_static, path)
    if os.path.isfile(file_path):
        mime, _ = mimetypes.guess_type(file_path)
        return FileResponse(file_path, media_type=mime or "application/octet-stream")
    html = _dr_index_html()
    if html:
        return HTMLResponse(html)
    raise HTTPException(status_code=404, detail="Not found")
```

### Flask / main.py pattern

```python
_DR_STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "hf-space-inventory-sqlgen", "static", "define-relationship")

def _dr_index_name():
    for name in ("index.html", "index-define-relationship.html"):
        if os.path.isfile(os.path.join(_DR_STATIC, name)):
            return name
    return None

@app.route('/define-relationship')
def dr_redirect():
    return redirect('/define-relationship/', code=302)

@app.route('/define-relationship/')
def dr_index():
    name = _dr_index_name()
    if name:
        return send_from_directory(_DR_STATIC, name)
    return "Define Relationship build not found", 404

@app.route('/define-relationship/<path:path>')
def dr_asset(path):
    full = os.path.join(_DR_STATIC, path)
    if os.path.isfile(full):
        return send_from_directory(_DR_STATIC, path)
    name = _dr_index_name()
    if name:
        return send_from_directory(_DR_STATIC, name)
    return "Define Relationship build not found", 404
```

---

## 5. Backend API Endpoints

All endpoints live in `hf-space-inventory-sqlgen/app.py`.
The frontend calls them all at the `/mcp/tools/` prefix.

### Read endpoints

| Method | Path | Handler | Returns |
|---|---|---|---|
| `GET` | `/mcp/tools/list_schema_tables` | `list_schema_tables()` | `{ matches_found, grouped_results: { "<ERP_INSTANCE_NAME>": [{table_name, qualified_name}] } }` |
| `GET` | `/mcp/tools/get_intents` | `get_intents(category?)` | `{ intents: [{intent_name, category, description}] }` |
| `GET` | `/mcp/tools/get_concepts` | `get_concepts(domain?, concept_type?)` | `{ concepts: [{concept_name, domain, concept_type}] }` |
| `GET` | `/mcp/tools/get_entity_categories` | `get_entity_categories()` | `{ categories: [string] }` — the 11 domain pill-bar labels |
| `GET` | `/mcp/tools/graph_stats` | `get_graph_stats()` | `{ total_edges, arango_available, collections: {name: count}, sqlite_bridge_rows }` |

### Write endpoints

| Method | Path | Handler | Purpose |
|---|---|---|---|
| `POST` | `/mcp/tools/commit_edge` | `commit_edge(CommitEdgeRequest)` | Create or upsert an edge / bridge document |
| `DELETE` | `/mcp/tools/commit_edge?edge_id=<handle>` | `delete_commit_edge(edge_id)` | Undo an edge by its ArangoDB document handle |

### `CommitEdgeRequest` Pydantic model

```python
class CommitEdgeRequest(BaseModel):
    predicate: str           # routing key — see table below
    source_id: str           # UI display label, e.g. "production_orders (ERP_Instance_1)"
    target_id: str
    intent: Optional[str] = None
    perspective: Optional[str] = None
    category: Optional[str] = None
    explanation: Optional[str] = None
    binding_key: Optional[str] = None
    concept_anchor: Optional[str] = None
    from_column: Optional[str] = None
    to_column: Optional[str] = None
```

### Predicate routing inside `commit_edge`

| Predicate(s) | Destination | ArangoDB collection |
|---|---|---|
| `ELEVATES` | ArangoDB | `elevates` (weight = +1) |
| `SUPPRESSES` | ArangoDB | `elevates` (weight = −1) |
| `BOUND_TO` | ArangoDB | `bound_to` |
| `HAS_COLUMN` | ArangoDB | `HAS_COLUMN` |
| `FOREIGN_KEY` | ArangoDB | `FOREIGN_KEY` |
| `MAPS_TO_CONCEPT` / `CAN_MEAN` | ArangoDB | `CAN_MEAN` |
| `OPERATES_WITHIN` | SQLite → ArangoDB sync | `schema_intent_perspectives` → `Perspective_Intents` |
| `USES_DEFINITION` | SQLite → ArangoDB sync | `schema_perspective_concepts` → `Perspective_Concepts` |

### Deletion allowlist

The `DELETE` handler only permits undo on these collections:

```python
_ALLOWED_EDGE_COLLECTIONS = frozenset({
    "elevates", "bound_to", "HAS_COLUMN", "FOREIGN_KEY", "CAN_MEAN",
})
```

SQLite-backed bridge rows (`OPERATES_WITHIN`, `USES_DEFINITION`) use the
`sqlite:…` edge_id prefix and follow a separate deletion path.

---

## 6. ArangoDB Collections

### Vertex collections (read by `_resolve_arango_handle`)

| Collection | Key format | Contents |
|---|---|---|
| `intents` | `intent_name` | Analytical intent nodes |
| `concepts` | `concept_name` | Abstract concept nodes |
| `bindings` | `binding_key` | Approved SQL snippet nodes |
| `{ARANGO_DB}_node` | `table_<table_name>` | ERP table / atomic nodes |

### Edge collections

| Collection | Connects | Written by predicate |
|---|---|---|
| `elevates` | intents → concepts | `ELEVATES`, `SUPPRESSES` |
| `bound_to` | intents → bindings | `BOUND_TO` |
| `HAS_COLUMN` | node → node | `HAS_COLUMN` |
| `FOREIGN_KEY` | node → node | `FOREIGN_KEY` |
| `CAN_MEAN` | node → concepts | `MAPS_TO_CONCEPT`, `CAN_MEAN` |

### Bridge document collections (Perspective Bridge Model)

Perspective lives as a **property on bridge rows**, not as a vertex collection.

| Collection | SQLite source table | Written by predicate |
|---|---|---|
| `Perspective_Intents` | `schema_intent_perspectives` | `OPERATES_WITHIN` |
| `Perspective_Concepts` | `schema_perspective_concepts` | `USES_DEFINITION` |

---

## 7. SQLite Tables Referenced

Database: `hf-space-inventory-sqlgen/app_schema/manufacturing.db`

| Table | Used by |
|---|---|
| `schema_nodes` | `list_schema_tables` — source of ERP table list |
| `schema_intents` | `get_intents`, `commit_edge` OPERATES_WITHIN path |
| `schema_concepts` | `get_concepts`, `commit_edge` USES_DEFINITION path |
| `schema_perspectives` | `get_entity_categories`, `commit_edge` bridge paths |
| `schema_entity_categories` | `get_entity_categories` — pill-bar domain labels |
| `schema_intent_perspectives` | Source of truth for `Perspective_Intents` |
| `schema_perspective_concepts` | Source of truth for `Perspective_Concepts` |

---

## 8. Environment Variables

| Variable | Default | Used by |
|---|---|---|
| `ERP_INSTANCE_NAME` | `ERP_Instance_1` | `list_schema_tables` — group key in search results |
| `ARANGO_HOST` | — | ArangoDB connection URL (with port) |
| `ARANGO_USER` | — | ArangoDB username |
| `ARANGO_ROOT_PASSWORD` | — | ArangoDB password |
| `ARANGO_DB` | `manufacturing_graph` | Database name and named-graph name |

---

## 9. NPM / Build Dependencies

These packages are required in `artifacts/mockup-sandbox/package.json` to build
the standalone bundle:

```
react, react-dom
@vitejs/plugin-react
@tailwindcss/vite
tailwindcss
vite
typescript
```

The component itself has no runtime dependencies beyond React and the Tailwind
CSS utility classes already bundled by the build step.

---

## 10. Checklist: Adding to the Private Repo

- [ ] Copy `src/components/mockups/graph-relationship/` (4 files)
- [ ] Copy `index-define-relationship.html` and `src/define-relationship-main.tsx` (standalone build only)
- [ ] Copy or replicate `vite.define-relationship.config.ts` with correct `outDir`
- [ ] Run `npx vite build --config vite.define-relationship.config.ts`
- [ ] Add static-serve routes to FastAPI/Flask using the `_dr_index_html()` / `_dr_index_name()` pattern
- [ ] Add all 7 `GET`/`POST`/`DELETE` `/mcp/tools/` endpoint handlers
- [ ] Add `CommitEdgeRequest` Pydantic model
- [ ] Add `_parse_entity_name()` and `_resolve_arango_handle()` helper functions
- [ ] Confirm ArangoDB collections exist (`elevates`, `bound_to`, `HAS_COLUMN`, `FOREIGN_KEY`, `CAN_MEAN`, `Perspective_Intents`, `Perspective_Concepts`)
- [ ] Confirm SQLite tables exist (Section 7)
- [ ] Set `ERP_INSTANCE_NAME`, `ARANGO_HOST`, `ARANGO_USER`, `ARANGO_ROOT_PASSWORD`, `ARANGO_DB` environment variables
