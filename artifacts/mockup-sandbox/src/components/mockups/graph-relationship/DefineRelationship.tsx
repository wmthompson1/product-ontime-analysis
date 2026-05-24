import { useState, useEffect } from "react";
import {
  ChevronRight,
  ChevronDown,
  Database,
  GitBranch,
  Search,
  Circle,
  RefreshCw,
  Plus,
  Pencil,
  X,
} from "lucide-react";

// Pill bar now scopes the workspace by Perspective/Category (was: edge predicate filter).
// Picking a Category here means "I'm building relationships within this domain scope" — and the
// active Category becomes an edge property on every relationship you create (architectural roadmap:
// categories migrate FROM nodes TO edge properties).
type CategoryScope = string;

// Varied accent palette for the 11 perspectives + neutral for ALL.
const CATEGORY_COLORS: Record<string, string> = {
  ALL: "bg-slate-600 text-slate-100",
  Customer_Order: "bg-blue-700 text-blue-100",
  Demand_Forecast: "bg-indigo-700 text-indigo-100",
  Engineering: "bg-cyan-700 text-cyan-100",
  General_Ledger: "bg-emerald-700 text-emerald-100",
  Inventory_Transactions: "bg-teal-700 text-teal-100",
  Manufacturing: "bg-amber-700 text-amber-100",
  Parts: "bg-orange-700 text-orange-100",
  Payables: "bg-rose-700 text-rose-100",
  Receivables: "bg-pink-700 text-pink-100",
  Visual_Admin: "bg-violet-700 text-violet-100",
  Work_Orders: "bg-fuchsia-700 text-fuchsia-100",
};

const EDGE_MEANINGS: Record<string, string> = {
  FOREIGN_KEY: "Defined as: structural referential integrity link between ERP tables. Table-Scoped. NOT GLOBAL MEANING.",
  ELEVATES: "Defined as: Intent promotes this Concept when routing a question. Semantic weight = 1. NOT GLOBAL MEANING.",
  SUPPRESSES: "Defined as: Intent demotes this Concept when routing a question. Semantic weight = -1. NOT GLOBAL MEANING.",
  MAPS_TO_CONCEPT: "Defined as: ERP table is bridged to a semantic Concept node. MAPS_TO_CONCEPT bridge. NOT GLOBAL MEANING.",
  OPERATES_WITHIN: "Defined as: Intent is scoped to a Perspective domain (e.g. quality, finance). NOT GLOBAL MEANING.",
  HAS_COLUMN: "Defined as: Structural edge linking table node to its atomic column node. NOT GLOBAL MEANING.",
  BOUND_TO: "Defined as: Binding resolves to an APPROVED SME SQL snippet for this Concept. NOT GLOBAL MEANING.",
};

const SOURCE_ENTITIES = [
  "production_orders (ERP_Instance_1)",
  "quality_events (ERP_Instance_1)",
  "equipment_metrics (ERP_Instance_1)",
  "downtime_events (ERP_Instance_1)",
  "suppliers (ERP_Instance_1)",
];

type MatchMode = "Contains" | "Starts with" | "Wildcard" | "Regex";

const MATCH_MODES: MatchMode[] = ["Contains", "Starts with", "Wildcard", "Regex"];

type EntityRecord = { table_name: string; qualified_name: string };
type GroupedResults = Record<string, EntityRecord[]>;
type SearchResult = { matches_found: number; grouped_results: GroupedResults };

const MOCK_SEARCH_DATA: SearchResult = {
  matches_found: 12,
  grouped_results: {
    ERP_Instance_1: [
      { table_name: "production_orders", qualified_name: "dbo.PRODUCTION_ORDERS" },
      { table_name: "work_orders", qualified_name: "dbo.WORK_ORDERS" },
      { table_name: "order_lines", qualified_name: "dbo.ORDER_LINES" },
      { table_name: "quality_events", qualified_name: "dbo.QUALITY_EVENTS" },
      { table_name: "equipment_metrics", qualified_name: "dbo.EQUIPMENT_METRICS" },
      { table_name: "downtime_events", qualified_name: "dbo.DOWNTIME_EVENTS" },
      { table_name: "suppliers", qualified_name: "dbo.SUPPLIERS" },
      { table_name: "production_lines", qualified_name: "dbo.PRODUCTION_LINES" },
    ],
    semantic_layer: [
      { table_name: "orders_concept", qualified_name: "concepts/orders_concept" },
      { table_name: "quality_intent", qualified_name: "intents/quality_intent" },
      { table_name: "downtime_perspective", qualified_name: "perspectives/downtime_perspective" },
      { table_name: "suppliers_binding", qualified_name: "bindings/suppliers_binding" },
    ],
  },
};

function searchEntities(
  query: string,
  mode: MatchMode = "Contains",
  data: SearchResult = MOCK_SEARCH_DATA,
): SearchResult {
  if (!query) return data;
  const normalized = query.toLowerCase();
  const filteredGroups: GroupedResults = {};
  let total = 0;

  for (const [source, records] of Object.entries(data.grouped_results)) {
    const matched = records.filter((item) => {
      const target = item.table_name.toLowerCase();
      switch (mode) {
        case "Starts with":
          return target.startsWith(normalized);
        case "Wildcard": {
          const escaped = normalized.replace(/[.+?^${}()|[\]\\]/g, "\\$&");
          const pattern = "^" + escaped.replace(/\*/g, ".*") + "$";
          try {
            return new RegExp(pattern).test(target);
          } catch {
            return false;
          }
        }
        case "Regex":
          try {
            return new RegExp(query).test(item.table_name);
          } catch {
            return false;
          }
        case "Contains":
        default:
          return target.includes(normalized);
      }
    });
    if (matched.length > 0) {
      filteredGroups[source] = matched;
      total += matched.length;
    }
  }
  return { matches_found: total, grouped_results: filteredGroups };
}

// TARGET_ENTITIES removed — superseded by MOCK_SEARCH_DATA.grouped_results.
// The grouped results list renders items as `"${rec.table_name} (${source})"`,
// so selectedTarget must use that same format (see useState initializer below).

const PREDICATES = [
  "FOREIGN_KEY",
  "ELEVATES",
  "SUPPRESSES",
  "MAPS_TO_CONCEPT",
  "OPERATES_WITHIN",
  "HAS_COLUMN",
  "BOUND_TO",
];

// NOTE: Categories === Perspectives === Intent Categories (same concept, UI label is "Categories").
// Architectural roadmap: Categories will move FROM being nodes TO being edge properties.
// Constraint: an Intent can only belong to ONE Category (single membership).
const CATEGORIES = [
  "Customer_Order",
  "Demand_Forecast",
  "Engineering",
  "General_Ledger",
  "Inventory_Transactions",
  "Manufacturing",
  "Parts",
  "Payables",
  "Receivables",
  "Visual_Admin",
  "Work_Orders",
];

// Ordered top-to-bottom: Categories first (top-level organizing concept), then the entities it scopes.
const GRAPH_ENTITIES: Array<{ name: string; children?: string[] }> = [
  { name: "Categories", children: CATEGORIES },
  { name: "Intents" },
  { name: "Concepts" },
  { name: "Bindings" },
];

// Mock intent set — three representative intents so we can demo the (intent, perspective)
// composite identity rule. Real list comes from the intents collection in v2.
const INTENTS = ["Avoid_Cost", "Quality_Defect", "Throughput_Boost"];

// Mock concept set — base concept names (perspective suffix emerges from the composite).
// Real list comes from `schema_concepts` / reviewer_manifest.json (e.g. DEFECTSEVERITYCOST,
// DEFECTSEVERITYQUALITY → same concept "DefectSeverity" resolved per perspective).
const CONCEPTS = ["DefectSeverity", "DeliveryPerformance", "OEE"];

// Edge ID convention (locked in conversation):
//   {LLL}_{RRR}_{XXX}_{NNN}_{Perspective}
//     LLL = first 3 of source table (uppercase)
//     RRR = first 3 of target table (uppercase)
//     XXX = first 3 of intent name  (uppercase)  ← adjacent to NNN so the counter
//     NNN = zero-padded collision counter           clearly disambiguates intent collisions
//     Perspective = the scoping category
// Composite IS the identity — the bridge-table row in `Perspective_Intents` is this edge.
function assembleEdgeId(
  source: string,
  target: string,
  intent: string,
  perspective: string,
  seq: number = 1
): string {
  const seg = (s: string) => s.replace(/[^a-zA-Z]/g, "").slice(0, 3).toUpperCase();
  const n = String(seq).padStart(3, "0");
  const persp = perspective === "ALL" ? "—" : perspective;
  return `${seg(source)}_${seg(target)}_${seg(intent)}_${n}_${persp}`;
}

// Concept bridge rows have a simpler 3-segment shape — no source/target tables, because
// a Concept is an abstract definition scoped by Perspective only:
//   {CCC}_{NNN}_{Perspective}
// e.g. DEF_001_Engineering   (DefectSeverity, in Engineering perspective)
// This is the row key for `Perspective_Concepts`.
function assembleConceptEdgeId(
  concept: string,
  perspective: string,
  seq: number = 1
): string {
  const seg = (s: string) => s.replace(/[^a-zA-Z]/g, "").slice(0, 3).toUpperCase();
  const n = String(seq).padStart(3, "0");
  const persp = perspective === "ALL" ? "—" : perspective;
  return `${seg(concept)}_${n}_${persp}`;
}

const DATA_TYPES = [
  "production_orders",
  "quality_events",
  "equipment_metrics",
  "downtime_events",
  "suppliers",
];

// ---------------------------------------------------------------------------
// DRAFT ARANGO LAYER — not yet connected to ArangoDB.
// Each function maps to a named query in docs/arango_graph_queries_new.md.
// When wiring the real connection, replace each function body with a
// fetch() call to the corresponding /mcp/tools/... endpoint or direct AQL.
// The component initialises its state from these stubs via useEffect so
// the swap-in is a single-function body change per stub.
// ---------------------------------------------------------------------------

// M1 — Load entity namespaces (grouped results for both entity panels)
// Calls /mcp/tools/list_schema_tables (proxied to Flask app on :8080).
// Throws on non-OK HTTP status so the caller can catch and fall back to mock.
async function fetchEntityNamespaces(): Promise<SearchResult> {
  const res = await fetch("/mcp/tools/list_schema_tables");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  if (!data.grouped_results) throw new Error("Unexpected response shape");
  return data as SearchResult;
}

// M2 — Load intent list (Choose Intent dropdown)
// Live: GET /mcp/tools/get_intents → {intents: [{intent_name, ...}]}
async function fetchIntents(): Promise<string[]> {
  const res = await fetch("/mcp/tools/get_intents");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  if (!Array.isArray(data.intents)) throw new Error("Unexpected response shape");
  return data.intents.map((i: { intent_name: string }) => i.intent_name).sort();
}

// M3 — Load concept list (Choose Concept dropdown)
// Live: GET /mcp/tools/get_concepts → {concepts: [{concept_name, ...}]}
async function fetchConcepts(): Promise<string[]> {
  const res = await fetch("/mcp/tools/get_concepts");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  if (!Array.isArray(data.concepts)) throw new Error("Unexpected response shape");
  return data.concepts.map((c: { concept_name: string }) => c.concept_name).sort();
}

// M4 — Load category/perspective list (pill bar)
// Live: GET /mcp/tools/get_perspectives → {perspectives: [{perspective_name, ...}]}
async function fetchCategories(): Promise<string[]> {
  const res = await fetch("/mcp/tools/get_perspectives");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  if (!Array.isArray(data.perspectives)) throw new Error("Unexpected response shape");
  return ["ALL", ...data.perspectives.map((p: { perspective_name: string }) => p.perspective_name).sort()];
}

// M5 — Resolve Perspective_Intents bridge key for (intent, perspective)
// Real: FOR row IN Perspective_Intents FILTER row.perspective==@p FILTER row.intent==@i RETURN row._key
async function fetchIntentBridgeKey(intent: string, perspective: string): Promise<string | null> {
  if (perspective === "ALL") return null;
  const seg3 = (s: string) => s.replace(/[^a-zA-Z]/g, "").slice(0, 3).toUpperCase();
  return `${seg3(intent)}_001_${perspective}`;
}

// M6 — Resolve Perspective_Concepts bridge key for (concept, perspective)
// Real: FOR row IN Perspective_Concepts FILTER row.perspective==@p FILTER row.concept==@c RETURN row._key
async function fetchConceptBridgeKey(concept: string, perspective: string): Promise<string | null> {
  if (perspective === "ALL") return null;
  const seg3 = (s: string) => s.replace(/[^a-zA-Z]/g, "").slice(0, 3).toUpperCase();
  return `${seg3(concept)}_001_${perspective}`;
}

// M7 — Commit new edge ("Add to Graph" button)
// Live: POST /mcp/tools/commit_edge with predicate-routing (docs/arango_graph_queries_new.md § M7)
async function commitEdge(
  predicate: string,
  sourceId: string,
  targetId: string,
  intent: string,
  perspective: string,
): Promise<{ ok: boolean; message: string }> {
  const res = await fetch("/mcp/tools/commit_edge", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      predicate,
      source_id: sourceId,
      target_id: targetId,
      intent: intent || null,
      perspective: perspective === "ALL" ? null : perspective,
    }),
  });
  const data = await res.json();
  if (!res.ok) return { ok: false, message: data.detail ?? data.error ?? `HTTP ${res.status}` };
  return { ok: true, message: data.message ?? `Edge committed: ${data.edge_id ?? "ok"}` };
}

// ---------------------------------------------------------------------------

function NavItem({ icon, active }: { icon: React.ReactNode; active?: boolean }) {
  return (
    <div
      className={`w-10 h-10 flex items-center justify-center rounded cursor-pointer ${
        active ? "bg-slate-600 text-white" : "text-slate-400 hover:text-slate-200"
      }`}
    >
      {icon}
    </div>
  );
}

export function DefineRelationship() {
  const [activeCategory, setActiveCategory] = useState<CategoryScope>("ALL");
  const [selectedSource, setSelectedSource] = useState(SOURCE_ENTITIES[0]);
  const [selectedPredicate, setSelectedPredicate] = useState("FOREIGN_KEY");
  const [selectedIntent, setSelectedIntent] = useState(INTENTS[0]);
  const [selectedConcept, setSelectedConcept] = useState(CONCEPTS[0]);
  const [selectedTarget, setSelectedTarget] = useState(
    (() => {
      const firstSource = Object.keys(MOCK_SEARCH_DATA.grouped_results)[0];
      const firstRec = MOCK_SEARCH_DATA.grouped_results[firstSource][0];
      return `${firstRec.table_name} (${firstSource})`;
    })()
  );
  const [dataTypesOpen, setDataTypesOpen] = useState(true);
  const [graphEntitiesOpen, setGraphEntitiesOpen] = useState(true);
  const [expandedEntities, setExpandedEntities] = useState<Record<string, boolean>>({
    Categories: true,
  });
  const [sourceSearch, setSourceSearch] = useState("");
  const [sourceMode, setSourceMode] = useState<MatchMode>("Contains");
  const [sourceModeOpen, setSourceModeOpen] = useState(false);
  const [targetSearch, setTargetSearch] = useState("");
  const [targetMode, setTargetMode] = useState<MatchMode>("Contains");
  const [targetModeOpen, setTargetModeOpen] = useState(false);

  // Draft Arango data — populated by stubs on mount; swap stub bodies to connect real Arango.
  // See docs/arango_graph_queries_new.md for the AQL behind each fetch function.
  const [entityNamespaces, setEntityNamespaces] = useState<SearchResult>(MOCK_SEARCH_DATA);
  const [intents, setIntents] = useState<string[]>(["Avoid_Cost", "Quality_Defect", "Throughput_Boost"]);
  const [concepts, setConcepts] = useState<string[]>(["DefectSeverity", "DeliveryPerformance", "OEE"]);
  const [categories, setCategories] = useState<string[]>(CATEGORIES);

  // Loading / API reachability state for entity panels.
  const [isLoadingEntities, setIsLoadingEntities] = useState(true);
  const [apiWarning, setApiWarning] = useState<string | null>(null);

  useEffect(() => {
    setIsLoadingEntities(true);
    fetchEntityNamespaces()
      .then((live) => {
        setEntityNamespaces(live);
        setApiWarning(null);
        // If the current source/target selections are not present in live data,
        // reset them to the first available live item so the UI stays consistent.
        const allLiveItems: string[] = [];
        for (const [src, recs] of Object.entries(live.grouped_results)) {
          for (const rec of recs) {
            allLiveItems.push(`${rec.table_name} (${src})`);
          }
        }
        if (allLiveItems.length > 0) {
          setSelectedSource((prev) => (allLiveItems.includes(prev) ? prev : allLiveItems[0]));
          setSelectedTarget((prev) => (allLiveItems.includes(prev) ? prev : allLiveItems[0]));
        }
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : String(err);
        setApiWarning(`Live schema unavailable (${msg}) — showing mock data.`);
      })
      .finally(() => setIsLoadingEntities(false));

    fetchIntents().then(setIntents).catch(() => { /* keep mock fallback */ });
    fetchConcepts().then(setConcepts).catch(() => { /* keep mock fallback */ });
    fetchCategories().then(setCategories).catch(() => { /* keep mock fallback */ });
  }, []);

  const sourceResults = searchEntities(sourceSearch, sourceMode, entityNamespaces);
  const targetResults = searchEntities(targetSearch, targetMode, entityNamespaces);

  const sourceShort = selectedSource.split(" ")[0];
  const targetShort = selectedTarget.split(" ")[0];
  const edgeId = assembleEdgeId(sourceShort, targetShort, selectedIntent, activeCategory);
  const conceptEdgeId = assembleConceptEdgeId(selectedConcept, activeCategory);
  // Bridge row keys — strictly composite, no source/target tables.
  // Perspective_Intents (perspective, intent) → 3-char intent + counter + perspective
  // Perspective_Concepts (perspective, concept) → same shape, different collection
  const seg3 = (s: string) => s.replace(/[^a-zA-Z]/g, "").slice(0, 3).toUpperCase();
  const persistable = activeCategory !== "ALL";
  const intentBridgeKey = persistable ? `${seg3(selectedIntent)}_001_${activeCategory}` : null;
  const conceptBridgeKey = persistable ? `${seg3(selectedConcept)}_001_${activeCategory}` : null;

  return (
    <div className="flex h-screen w-full bg-[#1e1e2e] text-sm font-['Inter'] overflow-hidden">
      {/* Icon sidebar */}
      <div className="w-12 bg-[#181825] flex flex-col items-center py-3 gap-2 border-r border-slate-700/50">
        <NavItem icon={<span className="text-xs font-bold">≡</span>} />
        <NavItem icon={<Search size={16} />} />
        <NavItem icon={<GitBranch size={16} />} active />
        <NavItem icon={<Database size={16} />} />
        <NavItem icon={<RefreshCw size={12} />} />
        <div className="flex-1" />
        <NavItem icon={<Circle size={14} className="text-slate-400" />} />
      </div>

      {/* Left panel */}
      <div className="w-52 bg-[#1e1e2e] border-r border-slate-700/50 flex flex-col">
        <div className="px-3 pt-3 pb-2">
          <p className="text-[10px] font-bold tracking-widest text-slate-400 uppercase">
            Data Navigator
          </p>
        </div>

        <div className="px-3 py-1.5 flex items-center gap-1.5">
          <Circle size={7} className="fill-emerald-400 text-emerald-400" />
          <span className="text-[10px] font-semibold text-emerald-400 tracking-wide">
            SYNC STATUS: Active
          </span>
        </div>

        <div className="px-3 pt-3 pb-1 flex items-center justify-between">
          <p className="text-[10px] font-bold tracking-widest text-slate-300 uppercase">
            Managed Entities
          </p>
          <Plus size={13} className="text-slate-400 cursor-pointer hover:text-slate-200" />
        </div>

        {/* DATA TYPES tree */}
        <div className="px-2">
          <button
            onClick={() => setDataTypesOpen(!dataTypesOpen)}
            className="w-full flex items-center gap-1 px-1 py-0.5 text-[11px] text-slate-300 hover:text-white"
          >
            {dataTypesOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            <Database size={11} className="text-slate-400" />
            <span className="font-medium">DATA TYPES</span>
          </button>
          {dataTypesOpen && (
            <div className="ml-4 border-l border-slate-700 pl-2 mt-0.5">
              <p className="text-[9px] text-slate-500 mb-1">97 Columns, WORK_ORDER</p>
              {DATA_TYPES.map((t) => (
                <div
                  key={t}
                  className="py-0.5 px-1 text-[10px] text-slate-400 hover:text-slate-200 cursor-pointer rounded hover:bg-slate-700/40"
                >
                  {t}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* GRAPH ENTITIES tree */}
        <div className="px-2 mt-1">
          <button
            onClick={() => setGraphEntitiesOpen(!graphEntitiesOpen)}
            className="w-full flex items-center gap-1 px-1 py-0.5 text-[11px] text-slate-300 hover:text-white"
          >
            {graphEntitiesOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            <GitBranch size={11} className="text-slate-400" />
            <span className="font-medium">GRAPH ENTITIES</span>
          </button>
          {graphEntitiesOpen && (
            <div className="ml-4 border-l border-slate-700 pl-2 mt-0.5">
              {GRAPH_ENTITIES.map((e) => {
                const isExpanded = expandedEntities[e.name];
                const hasChildren = e.children && e.children.length > 0;
                return (
                  <div key={e.name}>
                    <div
                      onClick={() =>
                        hasChildren &&
                        setExpandedEntities({
                          ...expandedEntities,
                          [e.name]: !isExpanded,
                        })
                      }
                      className="flex items-center gap-1 py-0.5 px-1 text-[10px] text-slate-300 hover:text-slate-100 cursor-pointer rounded hover:bg-slate-700/40"
                    >
                      {hasChildren ? (
                        isExpanded ? (
                          <ChevronDown size={10} />
                        ) : (
                          <ChevronRight size={10} />
                        )
                      ) : (
                        <ChevronRight size={10} className="opacity-30" />
                      )}
                      <span className={hasChildren ? "font-semibold" : ""}>
                        {e.name}
                      </span>
                      {hasChildren && (
                        <span className="ml-auto text-[8px] text-slate-500">
                          ({e.children!.length})
                        </span>
                      )}
                    </div>
                    {hasChildren && isExpanded && (
                      <div className="ml-3 border-l border-slate-700/60 pl-2 mt-0.5">
                        {e.children!.map((child) => (
                          <div
                            key={child}
                            className="py-0.5 px-1 text-[9px] text-slate-400 hover:text-slate-200 cursor-pointer rounded hover:bg-slate-700/40 truncate"
                          >
                            {child}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="flex-1" />
        <div className="px-3 py-2 flex items-center gap-1.5 border-t border-slate-700/50">
          <Circle size={7} className="fill-emerald-400 text-emerald-400" />
          <span className="text-[10px] text-emerald-400 font-semibold tracking-wide">
            SYNC STATUS: Active
          </span>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden bg-[#252535]">
        {/* Title bar */}
        <div className="px-5 pt-4 pb-2 border-b border-slate-700/50">
          <h1 className="text-lg font-semibold text-slate-100">
            Define Data Relationship
          </h1>
        </div>

        {/* API warning banner — shown when live schema is unreachable */}
        {apiWarning && (
          <div className="px-5 py-1.5 flex items-center gap-2 bg-amber-900/40 border-b border-amber-700/60">
            <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">⚠ Schema API</span>
            <span className="text-[10px] text-amber-300/80 flex-1">{apiWarning}</span>
            <button
              onClick={() => setApiWarning(null)}
              className="text-amber-500 hover:text-amber-300"
            >
              <X size={12} />
            </button>
          </div>
        )}

        {/* Category pill bar */}
        <div className="px-5 py-2.5 border-b border-slate-700/40 flex items-center gap-2 flex-wrap bg-[#1e1e2e]/60">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold mr-1">
            Category:
          </span>
          {(["ALL", ...categories] as CategoryScope[]).map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold tracking-wide transition-all ${
                activeCategory === cat
                  ? (CATEGORY_COLORS[cat] ?? "bg-slate-600 text-slate-100") + " ring-1 ring-white/20"
                  : "bg-slate-700/50 text-slate-400 hover:bg-slate-600/60 hover:text-slate-200"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {/* Workspace header */}
          <div className="rounded border border-slate-600/60 bg-[#1e1e2e]/80 overflow-hidden">
            <div className="px-4 py-2 bg-slate-700/40 border-b border-slate-600/60">
              <p className="text-[10px] font-bold tracking-widest text-slate-400 uppercase">
                Relationship Definition Workspace
              </p>
            </div>
            <div className="px-4 py-2.5">
              <p className="text-[11px] text-slate-400">
                Link an existing Entity to another Entity via a defined Relation
              </p>
            </div>

            {/* IDENTITY STRIP — three live-assembled keys above the fold.
                Hoisted out of the Edge Property Panel so the demo punchline
                (one edge, two bridge-row composite keys) is visible without scrolling. */}
            <div className="px-4 pb-3 pt-1 border-t border-slate-600/60 bg-slate-900/30">
              <p className="text-[9px] font-bold tracking-widest text-slate-500 uppercase mb-1.5">
                Live Identity Preview
              </p>
              <div className="grid grid-cols-3 gap-2">
                {/* Directional edge — always shown, scoped by intent+perspective */}
                <div className="border border-cyan-500/60 rounded bg-cyan-900/20 px-2 py-1.5">
                  <p className="text-[9px] text-cyan-300/70 uppercase tracking-wide mb-0.5">
                    rel_edge_id
                  </p>
                  <p className="text-[11px] text-cyan-200 font-mono break-all leading-tight">
                    {edgeId}
                  </p>
                  <p className="mt-0.5 text-[9px] text-cyan-300/50 leading-tight">
                    Directional edge (source→target)
                  </p>
                </div>

                {/* Perspective_Intents bridge row key — composite (perspective, intent) */}
                <div className={`border rounded px-2 py-1.5 ${persistable ? "border-violet-500/60 bg-violet-900/20" : "border-slate-600 bg-slate-800/40"}`}>
                  <p className={`text-[9px] uppercase tracking-wide mb-0.5 ${persistable ? "text-violet-300/70" : "text-slate-500"}`}>
                    Perspective_Intents
                  </p>
                  <p className={`text-[11px] font-mono break-all leading-tight ${persistable ? "text-violet-200" : "text-slate-500 italic"}`}>
                    {intentBridgeKey ?? "— pick a category to persist —"}
                  </p>
                  <p className={`mt-0.5 text-[9px] leading-tight ${persistable ? "text-violet-300/50" : "text-slate-600"}`}>
                    Bridge row: (perspective, intent)
                  </p>
                </div>

                {/* Perspective_Concepts bridge row key — composite (perspective, concept) */}
                <div className={`border rounded px-2 py-1.5 ${persistable ? "border-fuchsia-500/60 bg-fuchsia-900/20" : "border-slate-600 bg-slate-800/40"}`}>
                  <p className={`text-[9px] uppercase tracking-wide mb-0.5 ${persistable ? "text-fuchsia-300/70" : "text-slate-500"}`}>
                    Perspective_Concepts
                  </p>
                  <p className={`text-[11px] font-mono break-all leading-tight ${persistable ? "text-fuchsia-200" : "text-slate-500 italic"}`}>
                    {conceptBridgeKey ?? "— pick a category to persist —"}
                  </p>
                  <p className={`mt-0.5 text-[9px] leading-tight ${persistable ? "text-fuchsia-300/50" : "text-slate-600"}`}>
                    Bridge row: (perspective, concept)
                  </p>
                </div>
              </div>
            </div>

            {/* Three-column panel */}
            <div className="grid grid-cols-3 gap-0 border-t border-slate-600/60">
              {/* SELECT SOURCE ENTITY */}
              <div className="border-r border-slate-600/60 p-3">
                <p className="text-[10px] font-bold tracking-widest text-slate-400 uppercase mb-2">
                  Select Source Entity
                </p>

                {/* Search + Match Mode toggle */}
                <div className="flex items-stretch gap-1 mb-1.5">
                  <div className="relative flex-1">
                    <Search size={11} className="absolute left-2 top-1.5 text-slate-500" />
                    <input
                      value={sourceSearch}
                      onChange={(e) => setSourceSearch(e.target.value)}
                      placeholder={
                        sourceMode === "Wildcard"
                          ? "*_orders, quality_*"
                          : sourceMode === "Regex"
                          ? "^quality_.*$"
                          : "Search..."
                      }
                      className="w-full bg-slate-700/50 border border-slate-600 rounded text-[11px] text-slate-300 pl-6 pr-2 py-1 focus:outline-none focus:border-slate-400"
                    />
                  </div>
                  <div className="relative">
                    <button
                      onClick={() => setSourceModeOpen(!sourceModeOpen)}
                      className="h-full bg-slate-700/50 border border-slate-600 rounded text-[10px] text-slate-300 px-2 hover:bg-slate-600/60 flex items-center gap-1"
                    >
                      {sourceMode}
                      <ChevronDown size={10} />
                    </button>
                    {sourceModeOpen && (
                      <div className="absolute right-0 mt-1 z-10 bg-[#1e1e2e] border border-slate-600 rounded shadow-lg min-w-[110px]">
                        {MATCH_MODES.map((m) => (
                          <button
                            key={m}
                            onClick={() => {
                              setSourceMode(m);
                              setSourceModeOpen(false);
                            }}
                            className={`block w-full text-left px-2 py-1 text-[10px] hover:bg-slate-700/60 ${
                              m === sourceMode ? "text-emerald-300" : "text-slate-300"
                            }`}
                          >
                            {m}
                            {m === "Regex" && (
                              <span className="ml-1 text-[8px] text-slate-500">advanced</span>
                            )}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Match count */}
                <p className="text-[9px] text-slate-500 mb-1.5">
                  {sourceResults.matches_found} match{sourceResults.matches_found === 1 ? "" : "es"}
                  {sourceSearch && (
                    <span className="text-slate-600">
                      {" "}· {sourceMode.toLowerCase()} &quot;{sourceSearch}&quot;
                    </span>
                  )}
                </p>

                {/* Grouped results list */}
                <div className="border border-slate-600 rounded bg-slate-800/40 max-h-[140px] overflow-y-auto">
                  {isLoadingEntities ? (
                    <div className="flex items-center gap-1.5 px-2 py-2">
                      <RefreshCw size={11} className="text-slate-500 animate-spin" />
                      <span className="text-[10px] text-slate-500 italic">Loading schema…</span>
                    </div>
                  ) : Object.keys(sourceResults.grouped_results).length === 0 ? (
                    <p className="text-[10px] text-slate-500 italic px-2 py-1.5">
                      No matches
                    </p>
                  ) : (
                    Object.entries(sourceResults.grouped_results).map(([source, records]) => (
                      <div key={source}>
                        <div className="px-2 py-0.5 bg-slate-700/40 border-b border-slate-700 flex items-center justify-between">
                          <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">
                            {source}
                          </span>
                          <span className="text-[9px] text-slate-500">({records.length})</span>
                        </div>
                        {records.map((rec) => {
                          const display = `${rec.table_name} (${source})`;
                          const isSelected = selectedSource === display;
                          return (
                            <button
                              key={rec.qualified_name}
                              onClick={() => setSelectedSource(display)}
                              className={`block w-full text-left px-2 py-0.5 text-[10px] border-l-2 ${
                                isSelected
                                  ? "bg-slate-700/60 text-emerald-300 border-emerald-400"
                                  : "text-slate-300 border-transparent hover:bg-slate-700/40 hover:text-slate-100"
                              }`}
                            >
                              <span className="font-medium">▸ {rec.table_name}</span>
                              <span className="ml-1 text-[8px] text-slate-500">
                                {rec.qualified_name}
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    ))
                  )}
                </div>

                <div className="mt-2">
                  <p className="text-[10px] text-slate-500 uppercase tracking-wide">
                    Context:
                  </p>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Table: {selectedSource.split(" ")[0].toUpperCase()}
                  </p>
                </div>
              </div>

              {/* DEFINE RELATIONSHIP (EDGE) */}
              <div className="border-r border-slate-600/60 p-3">
                <p className="text-[10px] font-bold tracking-widest text-slate-400 uppercase mb-2">
                  Define Relationship (Edge)
                </p>
                <p className="text-[10px] text-slate-500 mb-1">Choose Predicate</p>
                <select
                  value={selectedPredicate}
                  onChange={(e) => setSelectedPredicate(e.target.value)}
                  className="w-full bg-slate-700/50 border border-slate-600 rounded text-[11px] text-slate-300 px-2 py-1 focus:outline-none focus:border-slate-400"
                >
                  {PREDICATES.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>

                <p className="text-[10px] text-slate-500 mb-1 mt-2">Choose Intent</p>
                <select
                  value={selectedIntent}
                  onChange={(e) => setSelectedIntent(e.target.value)}
                  className="w-full bg-slate-700/50 border border-slate-600 rounded text-[11px] text-slate-300 px-2 py-1 focus:outline-none focus:border-slate-400"
                >
                  {intents.map((i) => (
                    <option key={i} value={i}>
                      {i}
                    </option>
                  ))}
                </select>

                <p className="text-[10px] text-slate-500 mb-1 mt-2">
                  Choose Concept <span className="text-slate-600">(elevated by intent)</span>
                </p>
                <select
                  value={selectedConcept}
                  onChange={(e) => setSelectedConcept(e.target.value)}
                  className="w-full bg-slate-700/50 border border-slate-600 rounded text-[11px] text-slate-300 px-2 py-1 focus:outline-none focus:border-slate-400"
                >
                  {concepts.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>

                {/* Relation meaning box */}
                <div className="mt-2 border border-amber-500/60 rounded bg-amber-900/20 p-2">
                  <p className="text-[10px] font-bold text-amber-300 mb-1">
                    Relation Meaning (Table-Scoped):
                  </p>
                  <p className="text-[10px] text-amber-200/80 leading-relaxed">
                    {EDGE_MEANINGS[selectedPredicate] ?? "Select a predicate to see its meaning."}
                  </p>
                </div>
              </div>

              {/* SELECT TARGET ENTITY */}
              <div className="p-3">
                <p className="text-[10px] font-bold tracking-widest text-slate-400 uppercase mb-2">
                  Select Target Entity
                </p>

                {/* Search + Match Mode toggle */}
                <div className="flex items-stretch gap-1 mb-1.5">
                  <div className="relative flex-1">
                    <Search size={11} className="absolute left-2 top-1.5 text-slate-500" />
                    <input
                      value={targetSearch}
                      onChange={(e) => setTargetSearch(e.target.value)}
                      placeholder={
                        targetMode === "Wildcard"
                          ? "*_orders, quality_*"
                          : targetMode === "Regex"
                          ? "^quality_.*$"
                          : "Search..."
                      }
                      className="w-full bg-slate-700/50 border border-slate-600 rounded text-[11px] text-slate-300 pl-6 pr-2 py-1 focus:outline-none focus:border-slate-400"
                    />
                  </div>
                  <div className="relative">
                    <button
                      onClick={() => setTargetModeOpen(!targetModeOpen)}
                      className="h-full bg-slate-700/50 border border-slate-600 rounded text-[10px] text-slate-300 px-2 hover:bg-slate-600/60 flex items-center gap-1"
                    >
                      {targetMode}
                      <ChevronDown size={10} />
                    </button>
                    {targetModeOpen && (
                      <div className="absolute right-0 mt-1 z-10 bg-[#1e1e2e] border border-slate-600 rounded shadow-lg min-w-[110px]">
                        {MATCH_MODES.map((m) => (
                          <button
                            key={m}
                            onClick={() => {
                              setTargetMode(m);
                              setTargetModeOpen(false);
                            }}
                            className={`block w-full text-left px-2 py-1 text-[10px] hover:bg-slate-700/60 ${
                              m === targetMode ? "text-emerald-300" : "text-slate-300"
                            }`}
                          >
                            {m}
                            {m === "Regex" && (
                              <span className="ml-1 text-[8px] text-slate-500">advanced</span>
                            )}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Match count */}
                <p className="text-[9px] text-slate-500 mb-1.5">
                  {targetResults.matches_found} match{targetResults.matches_found === 1 ? "" : "es"}
                  {targetSearch && (
                    <span className="text-slate-600">
                      {" "}· {targetMode.toLowerCase()} &quot;{targetSearch}&quot;
                    </span>
                  )}
                </p>

                {/* Grouped results list */}
                <div className="border border-slate-600 rounded bg-slate-800/40 max-h-[140px] overflow-y-auto">
                  {isLoadingEntities ? (
                    <div className="flex items-center gap-1.5 px-2 py-2">
                      <RefreshCw size={11} className="text-slate-500 animate-spin" />
                      <span className="text-[10px] text-slate-500 italic">Loading schema…</span>
                    </div>
                  ) : Object.keys(targetResults.grouped_results).length === 0 ? (
                    <p className="text-[10px] text-slate-500 italic px-2 py-1.5">
                      No matches
                    </p>
                  ) : (
                    Object.entries(targetResults.grouped_results).map(([source, records]) => (
                      <div key={source}>
                        <div className="px-2 py-0.5 bg-slate-700/40 border-b border-slate-700 flex items-center justify-between">
                          <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">
                            {source}
                          </span>
                          <span className="text-[9px] text-slate-500">({records.length})</span>
                        </div>
                        {records.map((rec) => {
                          const display = `${rec.table_name} (${source})`;
                          const isSelected = selectedTarget === display;
                          return (
                            <button
                              key={rec.qualified_name}
                              onClick={() => setSelectedTarget(display)}
                              className={`block w-full text-left px-2 py-0.5 text-[10px] border-l-2 ${
                                isSelected
                                  ? "bg-slate-700/60 text-emerald-300 border-emerald-400"
                                  : "text-slate-300 border-transparent hover:bg-slate-700/40 hover:text-slate-100"
                              }`}
                            >
                              <span className="font-medium">▸ {rec.table_name}</span>
                              <span className="ml-1 text-[8px] text-slate-500">
                                {rec.qualified_name}
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    ))
                  )}
                </div>

                <div className="mt-2">
                  <p className="text-[10px] text-slate-500 uppercase tracking-wide">
                    Context:
                  </p>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Collection: {selectedTarget.split(" ")[0].toUpperCase()}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* PREVIEW & CONFIRM */}
          <div className="rounded border border-slate-600/60 bg-[#1e1e2e]/80 overflow-hidden">
            <div className="px-4 py-2 bg-slate-700/40 border-b border-slate-600/60">
              <p className="text-[10px] font-bold tracking-widest text-slate-400 uppercase">
                Preview &amp; Confirm Relationship
              </p>
            </div>
            {/* Compact single-row layout: graph preview (left) + horizontal context chip strip (right).
                Identity rows live in the Live Identity Preview strip up top — not duplicated here. */}
            <div className="p-3 flex items-center gap-4">
              {/* Graph preview — shrunk vertically */}
              <div className="flex items-center gap-2 shrink-0">
                <div className="border border-slate-400 rounded px-2.5 py-1 text-[11px] text-slate-200 bg-slate-700/50">
                  {sourceShort}
                </div>
                <div className="flex items-center gap-1 text-slate-400">
                  <div className="w-5 h-px bg-slate-500" />
                  <div className="border border-slate-500 rounded px-1.5 py-0.5 text-[9px] text-slate-400 bg-slate-800">
                    ({selectedPredicate.toLowerCase()})
                  </div>
                  <div className="w-5 h-px bg-slate-500" />
                  <svg width="8" height="10" viewBox="0 0 8 10" className="text-slate-400">
                    <polygon points="0,0 8,5 0,10" fill="currentColor" />
                  </svg>
                </div>
                <div className="border border-slate-400 rounded px-2.5 py-1 text-[11px] text-slate-200 bg-slate-700/50">
                  {targetShort}
                </div>
              </div>

              {/* Horizontal context strip — replaces the old vertical sidebar Edge Property Panel.
                  Just the supporting attributes; identities live in the strip above. */}
              <div className="flex-1 flex items-center gap-1.5 flex-wrap justify-end">
                <span className="text-[9px] uppercase tracking-widest text-slate-500 mr-1">Attrs:</span>
                <span className="border border-slate-600 rounded bg-slate-700/50 px-1.5 py-0.5 text-[10px] text-slate-300">
                  predicate: <span className="text-slate-200">{selectedPredicate}</span>
                </span>
                <span className="border border-slate-600 rounded bg-slate-700/50 px-1.5 py-0.5 text-[10px] text-slate-300">
                  intent: <span className="text-violet-300">{selectedIntent}</span>
                </span>
                <span className="border border-slate-600 rounded bg-slate-700/50 px-1.5 py-0.5 text-[10px] text-slate-300">
                  concept: <span className="text-fuchsia-300">{selectedConcept}</span>
                </span>
                <span className="border border-slate-600 rounded bg-slate-700/50 px-1.5 py-0.5 text-[10px] text-slate-300">
                  category: <span className={activeCategory === "ALL" ? "text-slate-500 italic" : "text-emerald-300"}>{activeCategory}</span>
                </span>
                <span className="border border-slate-600 rounded bg-slate-700/50 px-1.5 py-0.5 text-[10px] text-slate-400">
                  weight: <span className="text-slate-200">{selectedPredicate === "ELEVATES" ? "1" : selectedPredicate === "SUPPRESSES" ? "-1" : "null"}</span>
                </span>
                <Pencil size={11} className="text-slate-500 cursor-pointer hover:text-slate-300 ml-1" />
              </div>
            </div>
          </div>
        </div>

        {/* Bottom action buttons */}
        <div className="border-t border-slate-700/50 px-4 py-3 flex items-center gap-3 bg-[#1e1e2e]">
          <button
            className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-bold tracking-widest uppercase py-2.5 rounded transition-colors"
            onClick={() =>
              commitEdge(selectedPredicate, selectedSource, selectedTarget, selectedIntent, activeCategory)
            }
          >
            Add to Graph
          </button>
          <button className="flex-1 bg-blue-600 hover:bg-blue-500 text-white text-[11px] font-bold tracking-widest uppercase py-2.5 rounded transition-colors">
            Store in Repo Memory (graph_sync.md)
          </button>
          <button className="px-6 bg-rose-700 hover:bg-rose-600 text-white text-[11px] font-bold tracking-widest uppercase py-2.5 rounded transition-colors">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
