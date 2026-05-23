add to plan /@pods\pod19.md
---

### 🧱 The Structural Integration Blueprint

Instead of creating a triangle join in your graph where a field links to an intent, and both link to a separate `Perspective` node, the perspective becomes an authoritative key column embedded right inside your composite `Column_Bindings` edge:

```
❌ The Old Triangular Approach (Vertex Bloat):
[Component_Field] ────► [Binding Edge] ────► [Concept]
        │                                       ▲
        └──────────────► [Perspective] ─────────┘

🟢 The Dovetailed Edge-Property Model (Zero Extra Vertices):
[Component_Field] ───► [Binding Edge { perspective: "Engineering" }] ───► [Concept]

```

By shifting the perspective into an edge attribute, you reduce your database footprint while naturally complementing your deterministic `{LLL}_{RRR}_{NNN}_{XXX}_{Perspective}` key formula.

---

### 🛠️ Execution Steps for the Agent

When you pass this to the agent, instruct it to execute the integration across the three main layers of our codebase using the `_unitTest` validation flag:

#### 1. Update the Local Static Array (`constants.js`)

Have the agent structure the mock data payload so that the perspective is nested as a parameter directly inside the edge definition:

```javascript
export const MOCK_BINDING_EDGES = [
  {
    _key: "WOR_PAR_001_PAR_Engineering", //
    _from: "Graph_Component_Fields/WOR_BASE_ID",
    _to: "Graph_Concepts/CONCEPT_PART_NUMBER",
    // Moving context cleanly to an edge attribute
    properties: {
      perspective: "Engineering", //
      category: "Item Master Specification",
      discriminator_clause: "type == 'M'" //
    }
  }
];

```

#### 2. Update the Ingestion Rules Engine (`graph_sync.py`)

Ensure the edge writer extracts the perspective string from your raw metadata and writes it as a core document variable instead of looking for a `_to` connection on a separate perspective vertex collection.

#### 3. Update the Regression Test Helper (`_unitTest`)

The agent must extend the unit test suite to assert that these new properties exist on every committed edge. Have it mirror the validation patterns from `scripts\test_load_erp_ddl_into_sqlite.py` to write a targeted regression check:

```python
def test_binding_edge_properties_unitTest():
    """
    Asserts that the perspective and category have successfully 
    moved from node layouts to edge properties.
    """
    # 1. Parse your test case (reusing the existing codebase parsing helper)
    edge_payload = get_staged_edge_metadata("WOR_PAR_001_PAR_Engineering") #
    
    # 2. Enforce strict structural invariants via the regression suite
    assert "properties" in edge_payload
    assert edge_payload["properties"]["perspective"] == "Engineering" #
    assert "category" in edge_payload["properties"]

```

---

### 🎨 Impact on the Front-End Match Mode Toggle

This move makes your frontend mockup engine incredibly powerful. When a user updates the **Match Mode Toggle** in the UI, your local filter script doesn't have to join separate node collections. It can read the properties array directly from the edge:

```javascript
// Local V1 emulation of edge property filtering
const engineeringMatches = mockEdges.filter(edge => edge.properties.perspective === "Engineering"); //

```

If a user selects **Wildcard** and searches for `*__Engineering`, the dropdown immediately splits the collection by the metadata properties and renders your live-filtered lists without a single drop in rendering performance.

---

### 📐 ToC Alignment: Unified Metadata Specification

By merging these two plans, your global framework layout stays perfectly structured:

| Architectural Layer | Legacy Strategy | Dovetailed Edge Property Standard | `_unitTest` Verification Target |
| --- | --- | --- | --- |
| **`Perspectives`** | Standalone collection nodes (Vertex Bloat). | **Internal Edge Attribute Property** (`perspective: "Engineering"`). | Asserts key naming string conventions and field match rules. |
| **`Categories`** | Dynamic link nodes | **Internal Edge Attribute Property** (`category: "Inventory"`). | Confirms text strings exist inside the edge array property. |
| **`Component_Fields`** | Floating property vertex nodes. | Nested properties inside flat physical tables. | Confirms `HAS_COLUMN` stays at exactly zero across sync passes. |

Tell the agent to begin the update loop: **"Dovetail the perspective shift as an internal edge attribute property inside the metadata engine, and protect the implementation using the `_unitTest` tag framework."** It has all the templates it needs to lock this in!