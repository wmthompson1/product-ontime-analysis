import { useState, useEffect, useRef } from "react";
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
import { getFirstEntityDisplay } from "./entityDisplay";
import type { EntityRecord, GroupedResults, SearchResult } from "./entityDisplay";
import { undoEdge, fetchGraphStats } from "./graphApi";
import type { GraphStats } from "./graphApi";
import { MOCK_SEARCH_DATA } from "./fixtures";
import { useColumnsByTable } from "./useColumnsByTable";
import type { ColumnMeta } from "./useColumnsByTable";

// Pill bar now scopes the workspace by Perspective/Category (was: edge predicate filter).
// Picking a Category here means "I'm building relationships within this domain scope" — and the
// active Category becomes an edge property on every relationship you create (architectural roadmap:
// categories migrate FROM nodes TO edge properties).
type CategoryScope = string;

// Varied accent palette for the 12 perspectives + neutral for ALL.
const CATEGORY_COLORS: Record<string, string> = {
  ALL: "bg-slate-600 text-slate-100",
  CRM: "bg-sky-700 text-sky-100",
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
  CONTAINS: "Defined as: Structural containment — a table node owns its column nodes. Physical layer only, no business meaning. edge_type stored on the contains edge collection.",
  FOREIGN_KEY: "Defined as: structural referential integrity link between ERP tables. Table-Scoped. NOT GLOBAL MEANING.",
  ELEVATES: "Defined as: Intent promotes this Concept when routing a question. Semantic weight = 1. NOT GLOBAL MEANING.",
  SUPPRESSES: "Defined as: Intent demotes this Concept when routing a question. Semantic weight = -1. NOT GLOBAL MEANING.",
  MAPS_TO_CONCEPT: "Defined as: ERP table is bridged to a semantic Concept node. MAPS_TO_CONCEPT bridge. NOT GLOBAL MEANING.",
  OPERATES_WITHIN: "Defined as: Intent is scoped to a Perspective domain (e.g. quality, finance). NOT GLOBAL MEANING.",
  HAS_COLUMN: "Defined as: Structural edge linking table node to its atomic column node. NOT GLOBAL MEANING.",
  BOUND_TO: "Defined as: Binding resolves to an APPROVED SME SQL snippet for this Concept. NOT GLOBAL MEANING.",
};

// SOURCE_ENTITIES static list retired — selectedSource now derives from MOCK_SEARCH_DATA
// so the initial highlight always matches the live grouped-results list.
// MOCK_SEARCH_DATA is defined in ./fixtures — import above.

type MatchMode = "Contains" | "Starts with" | "Wildcard" | "Regex";

const MATCH_MODES: MatchMode[] = ["Contains", "Starts with", "Wildcard", "Regex"];

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

const STRUCTURAL_PREDICATES = ["CONTAINS", "FOREIGN_KEY"];

const SEMANTIC_PREDICATES = [
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
  "CRM",
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
  { name: "Types", children: CATEGORIES },
  { name: "Intents" },
  { name: "Concepts" },
  { name: "Bindings" },
];

// Mock intent set — representative intents covering manufacturing + CRM walkthrough.
// Real list comes from the intents collection in v2.
const INTENTS = [
  // CRM intent walkthrough — joins customer → customer_address
  "CRM_Join",
  // Manufacturing intents
  "Avoid_Cost",
  "Quality_Defect",
  "Throughput_Boost",
];

// Mock concept set — base concept names (perspective suffix emerges from the composite).
// Real list comes from `schema_concepts` / reviewer_manifest.json.
const CONCEPTS = [
  // CRM concept elevated by CRM_Join intent
  "CustomerProfile",
  // Manufacturing concepts
  "DefectSeverity",
  "DeliveryPerformance",
  "OEE",
];

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

// M4 — Load entity category list (pill bar)
// Live: GET /mcp/tools/get_entity_categories → {categories: string[], source: "sqlite"}
// Falls back to the CATEGORIES constant if the endpoint is unavailable.
async function fetchCategories(): Promise<string[]> {
  const res = await fetch("/mcp/tools/get_entity_categories");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  if (!Array.isArray(data.categories) || data.categories.length === 0) {
    return ["ALL", ...CATEGORIES];
  }
  return ["ALL", ...data.categories];
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
// perspective and category are stored as direct properties on every edge document.
async function commitEdge(
  predicate: string,
  sourceId: string,
  targetId: string,
  intent: string,
  category: string,
  conceptAnchor?: string,
): Promise<{ ok: boolean; message: string; edge_id?: string }> {
  const cat = category === "ALL" ? null : category;
  const res = await fetch("/mcp/tools/commit_edge", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      predicate,
      source_id: sourceId,
      target_id: targetId,
      intent: intent || null,
      category: cat,
      perspective: cat,
      concept_anchor: conceptAnchor || null,
    }),
  });
  const data = await res.json();
  if (!res.ok) return { ok: false, message: data.detail ?? data.error ?? `HTTP ${res.status}` };
  return { ok: true, message: data.message ?? `Edge committed: ${data.edge_id ?? "ok"}`, edge_id: data.edge_id };
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

type FormMode = "structural" | "semantic";

export function DefineRelationship() {
  const [formMode, setFormMode] = useState<FormMode>("structural");
  const [activeCategory, setActiveCategory] = useState<CategoryScope>("ALL");
  const [selectedSource, setSelectedSource] = useState(
    getFirstEntityDisplay(MOCK_SEARCH_DATA)
  );
  const [selectedPredicate, setSelectedPredicate] = useState("CONTAINS");
  const [selectedIntent, setSelectedIntent] = useState(INTENTS[0]);
  const [selectedConcept, setSelectedConcept] = useState(CONCEPTS[0]);
  const [selectedTarget, setSelectedTarget] = useState(
    getFirstEntityDisplay(MOCK_SEARCH_DATA)
  );
  const [dataTypesOpen, setDataTypesOpen] = useState(true);
  const [graphEntitiesOpen, setGraphEntitiesOpen] = useState(true);
  const [expandedEntities, setExpandedEntities] = useState<Record<string, boolean>>({
    Types: true,
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

  // Commit-edge feedback state.
  const [isCommitting, setIsCommitting] = useState(false);

  // Multi-entry undo history — last MAX_HISTORY successful additions shown as a list.
  // Each entry has its own Undo button and is removed once undone or after historyTtlMs.
  const DEFAULT_HISTORY_TTL_MS = 30_000;
  const [historyTtlMs, setHistoryTtlMs] = useState(DEFAULT_HISTORY_TTL_MS); // adjustable from UI (#94)
  const MAX_HISTORY = 5;
  const HISTORY_SESSION_KEY = "dr_recent_additions_v1";
  type HistoryEntry = {
    id: string;
    ok: boolean;
    message: string;
    edge_id?: string;
    predicate: string;
    source: string;
    target: string;
    addedAt: number;
  };
  // Restore history from sessionStorage on mount, dropping entries older than DEFAULT_HISTORY_TTL_MS.
  const [recentAdditions, setRecentAdditions] = useState<HistoryEntry[]>(() => {
    try {
      const raw = sessionStorage.getItem(HISTORY_SESSION_KEY);
      if (raw) {
        const parsed: HistoryEntry[] = JSON.parse(raw);
        const now = Date.now();
        return parsed.filter((e) => now - e.addedAt < DEFAULT_HISTORY_TTL_MS);
      }
    } catch {}
    return [];
  });
  const [undoingEdgeId, setUndoingEdgeId] = useState<string | null>(null);
  const historyTimersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const removeHistoryEntry = (id: string) => {
    setRecentAdditions((prev) => prev.filter((e) => e.id !== id));
    const t = historyTimersRef.current.get(id);
    if (t) { clearTimeout(t); historyTimersRef.current.delete(id); }
  };

  const scheduleExpiry = (id: string, delay: number) => {
    const t = setTimeout(() => removeHistoryEntry(id), delay);
    historyTimersRef.current.set(id, t);
  };

  // Transient undo confirmation — shown for 3 s then auto-cleared.
  const [undoConfirm, setUndoConfirm] = useState<{ predicate: string; source: string; target: string } | null>(null);
  const undoConfirmTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Live edge-count badge — null means not yet loaded.
  const [graphEdgeCount, setGraphEdgeCount] = useState<number | null>(null);
  const [graphStats, setGraphStats] = useState<GraphStats | null>(null);
  const [badgeHovered, setBadgeHovered] = useState(false);
  const [edgeDelta, setEdgeDelta] = useState<number | null>(null); // shows +/- since last change (#97)
  const prevEdgeCountRef = useRef<number | null>(null);

  const refreshGraphStats = () => {
    fetchGraphStats().then((stats) => {
      if (stats !== null) {
        const prev = prevEdgeCountRef.current;
        const next = stats.total_edges;
        if (prev !== null && prev !== next) {
          setEdgeDelta(next - prev);
          // Clear the delta indicator after 4 s
          setTimeout(() => setEdgeDelta(null), 4000);
        }
        prevEdgeCountRef.current = next;
        setGraphEdgeCount(next);
        setGraphStats(stats);
      }
    });
  };

  // Persist history to sessionStorage whenever it changes (#92).
  useEffect(() => {
    try {
      sessionStorage.setItem(HISTORY_SESSION_KEY, JSON.stringify(recentAdditions));
    } catch {}
  }, [recentAdditions]);

  // Pre-fill source/target from URL parameters on mount (#102).
  // Example: ?source=production_orders&target=work_orders
  useEffect(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const s = params.get("source");
      const t = params.get("target");
      if (s) setSelectedSource(s);
      if (t) setSelectedTarget(t);
    } catch {}
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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
    refreshGraphStats();
  }, []);

  const isStructural = formMode === "structural";

  const handleModeSwitch = (newMode: FormMode) => {
    if (newMode === formMode) return;
    const firstEntity = getFirstEntityDisplay(entityNamespaces);
    setFormMode(newMode);
    setSelectedSource(firstEntity);
    setSelectedTarget(firstEntity);
    setSelectedPredicate(newMode === "structural" ? "CONTAINS" : "ELEVATES");
    setSelectedIntent(intents[0] ?? "");
    setSelectedConcept(concepts[0] ?? "");
    setActiveCategory("ALL");
    setSourceSearch("");
    setTargetSearch("");
    setSourceMode("Contains");
    setTargetMode("Contains");
  };

  const sourceResults = searchEntities(sourceSearch, sourceMode, entityNamespaces);
  const targetResults = searchEntities(targetSearch, targetMode, entityNamespaces);

  const sourceShort = selectedSource.split(" ")[0];
  const targetShort = selectedTarget.split(" ")[0];
  const edgeId = assembleEdgeId(sourceShort, targetShort, selectedIntent, activeCategory);
  const hasCategory = activeCategory !== "ALL";

  // When CONTAINS is the active edge type, fetch columns for the selected source table.
  // The hook caches results per-table and returns IDLE when edge type is not CONTAINS.
  const isContains = selectedPredicate === "CONTAINS";
  const {
    columns: targetColumns,
    isLoading: isLoadingColumns,
    error: columnError,
  } = useColumnsByTable(sourceShort, selectedPredicate);

  // Keep selectedTarget in sync when switching into CONTAINS mode —
  // reset to the first available column so the preview strip is never stale.
  useEffect(() => {
    if (isContains && targetColumns.length > 0) {
      setSelectedTarget(targetColumns[0].qualified_name);
    }
    if (!isContains) {
      // Restore a table-style selection when leaving CONTAINS mode.
      setSelectedTarget(getFirstEntityDisplay(entityNamespaces));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isContains, targetColumns.length]);

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
        <div className="px-5 pt-4 pb-2 border-b border-slate-700/50 flex items-center gap-3">
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

        {/* Category pill bar — semantic mode only; greyed out in structural */}
        <div className={`px-5 py-2.5 border-b border-slate-700/40 flex items-center gap-2 flex-wrap bg-[#1e1e2e]/60 transition-opacity ${isStructural ? "opacity-30 pointer-events-none select-none" : ""}`}>
          <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold mr-1">
            Category:
          </span>
          {isStructural && (
            <span className="text-[10px] text-slate-600 italic">
              Not applicable to structural edges
            </span>
          )}
          {!isStructural && (categories as CategoryScope[]).map((cat) => (
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
            <div className="px-4 py-2.5 flex items-center justify-between">
              <p className="text-[11px] text-slate-400">
                Link an existing Entity to another Entity via a defined Relation
              </p>
              {/* Hard-toggle: switching clears all form state */}
              <div className="flex rounded overflow-hidden border border-slate-600 shrink-0 ml-4">
                <button
                  onClick={() => handleModeSwitch("structural")}
                  className={`px-3 py-1 text-[10px] font-semibold tracking-wide transition-colors ${
                    isStructural
                      ? "bg-cyan-700 text-cyan-100"
                      : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200"
                  }`}
                >
                  Structural
                </button>
                <button
                  onClick={() => handleModeSwitch("semantic")}
                  className={`px-3 py-1 text-[10px] font-semibold tracking-wide transition-colors border-l border-slate-600 ${
                    !isStructural
                      ? "bg-violet-700 text-violet-100"
                      : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200"
                  }`}
                >
                  Semantic
                </button>
              </div>
            </div>

            {/* IDENTITY STRIP — structural vs semantic layouts */}
            <div className="px-4 pb-3 pt-1 border-t border-slate-600/60 bg-slate-900/30">
              <p className="text-[9px] font-bold tracking-widest text-slate-500 uppercase mb-1.5">
                Live Identity Preview
              </p>

              {isStructural ? (
                <div className="grid grid-cols-2 gap-2">
                  {/* Structural edge key — EDGE_TYPE:src->tgt */}
                  <div className="border border-cyan-500/60 rounded bg-cyan-900/20 px-2 py-1.5">
                    <p className="text-[9px] text-cyan-300/70 uppercase tracking-wide mb-0.5">
                      edge_key
                    </p>
                    <p className="text-[11px] text-cyan-200 font-mono break-all leading-tight">
                      {selectedPredicate}:{sourceShort.toUpperCase()}→{targetShort.toUpperCase()}
                    </p>
                    <p className="mt-0.5 text-[9px] text-cyan-300/50 leading-tight">
                      Physical containment / FK — no intent scope
                    </p>
                  </div>
                  {/* edge_type */}
                  <div className="border border-slate-600 rounded bg-slate-800/40 px-2 py-1.5">
                    <p className="text-[9px] text-slate-500 uppercase tracking-wide mb-0.5">
                      edge_type
                    </p>
                    <p className="text-[11px] text-slate-200 font-mono leading-tight">
                      {selectedPredicate}
                    </p>
                    <p className="mt-0.5 text-[9px] text-slate-600 leading-tight">
                      Structural — no category / perspective
                    </p>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-3 gap-2">
                  {/* Directional semantic edge ID */}
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
                  {/* edge.category */}
                  <div className={`border rounded px-2 py-1.5 ${hasCategory ? "border-violet-500/60 bg-violet-900/20" : "border-slate-600 bg-slate-800/40"}`}>
                    <p className={`text-[9px] uppercase tracking-wide mb-0.5 ${hasCategory ? "text-violet-300/70" : "text-slate-500"}`}>
                      edge.category
                    </p>
                    <p className={`text-[11px] font-mono break-all leading-tight ${hasCategory ? "text-violet-200" : "text-slate-500 italic"}`}>
                      {hasCategory ? activeCategory : "— pick a category —"}
                    </p>
                    <p className={`mt-0.5 text-[9px] leading-tight ${hasCategory ? "text-violet-300/50" : "text-slate-600"}`}>
                      Edge property (domain scope)
                    </p>
                  </div>
                  {/* edge.perspective */}
                  <div className={`border rounded px-2 py-1.5 ${hasCategory ? "border-fuchsia-500/60 bg-fuchsia-900/20" : "border-slate-600 bg-slate-800/40"}`}>
                    <p className={`text-[9px] uppercase tracking-wide mb-0.5 ${hasCategory ? "text-fuchsia-300/70" : "text-slate-500"}`}>
                      edge.perspective
                    </p>
                    <p className={`text-[11px] font-mono break-all leading-tight ${hasCategory ? "text-fuchsia-200" : "text-slate-500 italic"}`}>
                      {hasCategory ? activeCategory : "— pick a category —"}
                    </p>
                    <p className={`mt-0.5 text-[9px] leading-tight ${hasCategory ? "text-fuchsia-300/50" : "text-slate-600"}`}>
                      Edge property (analytical scope)
                    </p>
                  </div>
                </div>
              )}
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
                  {isLoadingEntities ? (
                    <span className="animate-pulse text-slate-600">—</span>
                  ) : (
                    <>
                      {sourceResults.matches_found} match{sourceResults.matches_found === 1 ? "" : "es"}
                      {apiWarning !== null && (
                        <span className="ml-1 text-amber-400 font-semibold">mock</span>
                      )}
                      {sourceSearch && (
                        <span className="text-slate-600">
                          {" "}· {sourceMode.toLowerCase()} &quot;{sourceSearch}&quot;
                        </span>
                      )}
                    </>
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
                            Tables
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
                              <span className="font-medium">{rec.table_name}</span>
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
                <p className="text-[10px] text-slate-500 mb-1">
                  {isStructural ? "Choose Edge Type" : "Edge Type"}
                  {!isStructural && (
                    <span className="ml-1 text-slate-600 normal-case tracking-normal font-normal">
                      — type freehand or pick a suggestion
                    </span>
                  )}
                </p>

                {isStructural ? (
                  <select
                    value={selectedPredicate}
                    onChange={(e) => setSelectedPredicate(e.target.value)}
                    className="w-full bg-slate-700/50 border border-slate-600 rounded text-[11px] text-slate-300 px-2 py-1 focus:outline-none focus:border-slate-400"
                  >
                    {STRUCTURAL_PREDICATES.map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                ) : (
                  <>
                    <input
                      type="text"
                      list="semantic-predicates-datalist"
                      value={selectedPredicate}
                      onChange={(e) => setSelectedPredicate(e.target.value.toUpperCase())}
                      placeholder="e.g. ELEVATES"
                      className="w-full bg-slate-700/50 border border-slate-600 rounded text-[11px] text-slate-300 px-2 py-1 focus:outline-none focus:border-violet-500 placeholder-slate-600"
                    />
                    <datalist id="semantic-predicates-datalist">
                      {SEMANTIC_PREDICATES.map((p) => (
                        <option key={p} value={p} />
                      ))}
                    </datalist>
                  </>
                )}

                {!isStructural && (
                  <>
                    <p className="text-[10px] text-slate-500 mb-1 mt-2">Choose Intent</p>
                    <select
                      value={selectedIntent}
                      onChange={(e) => setSelectedIntent(e.target.value)}
                      className="w-full bg-slate-700/50 border border-slate-600 rounded text-[11px] text-slate-300 px-2 py-1 focus:outline-none focus:border-slate-400"
                    >
                      {intents.map((i) => (
                        <option key={i} value={i}>{i}</option>
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
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </>
                )}

                {/* Relation meaning box */}
                <div className={`mt-2 border rounded p-2 ${isStructural ? "border-cyan-500/40 bg-cyan-900/10" : "border-amber-500/60 bg-amber-900/20"}`}>
                  <p className={`text-[10px] font-bold mb-1 ${isStructural ? "text-cyan-300" : "text-amber-300"}`}>
                    {isStructural ? "Structural Meaning:" : "Relation Meaning (Table-Scoped):"}
                  </p>
                  <p className={`text-[10px] leading-relaxed ${isStructural ? "text-cyan-200/80" : "text-amber-200/80"}`}>
                    {EDGE_MEANINGS[selectedPredicate] ?? (
                      selectedPredicate.trim()
                        ? `Custom predicate "${selectedPredicate}" — no standard meaning defined. This edge type will be stored as-is on the graph edge.`
                        : "Type a predicate name above, or pick one from the suggestions."
                    )}
                  </p>
                </div>
              </div>

              {/* SELECT TARGET ENTITY — switches to column list when CONTAINS is active */}
              <div className="p-3">
                <p className="text-[10px] font-bold tracking-widest text-slate-400 uppercase mb-2">
                  {isContains ? "Select Target Column" : "Select Target Entity"}
                </p>

                {isContains ? null : (
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
                )}

                {/* Match count — columns mode shows a simple count; table mode shows search results */}
                <p className="text-[9px] text-slate-500 mb-1.5">
                  {isContains ? (
                    isLoadingColumns ? (
                      <span className="animate-pulse text-slate-600">Loading columns…</span>
                    ) : columnError ? (
                      <span className="text-slate-500 italic">
                        Column list not loaded — pick a table above
                      </span>
                    ) : (
                      <span>
                        {targetColumns.length} column{targetColumns.length === 1 ? "" : "s"} in{" "}
                        <span className="text-slate-300 font-semibold">{sourceShort.toUpperCase()}</span>
                      </span>
                    )
                  ) : isLoadingEntities ? (
                    <span className="animate-pulse text-slate-600">—</span>
                  ) : (
                    <>
                      {targetResults.matches_found} match{targetResults.matches_found === 1 ? "" : "es"}
                      {apiWarning !== null && (
                        <span className="ml-1 text-amber-400 font-semibold">mock</span>
                      )}
                      {targetSearch && (
                        <span className="text-slate-600">
                          {" "}· {targetMode.toLowerCase()} &quot;{targetSearch}&quot;
                        </span>
                      )}
                    </>
                  )}
                </p>

                {/* Results list — column list when CONTAINS, grouped table list otherwise */}
                <div className="border border-slate-600 rounded bg-slate-800/40 max-h-[140px] overflow-y-auto">
                  {isContains ? (
                    isLoadingColumns ? (
                      <div className="flex items-center gap-1.5 px-2 py-2">
                        <RefreshCw size={11} className="text-slate-500 animate-spin" />
                        <span className="text-[10px] text-slate-500 italic">Loading columns…</span>
                      </div>
                    ) : targetColumns.length === 0 ? (
                      <p className="text-[10px] text-slate-500 italic px-2 py-1.5">No columns found</p>
                    ) : (
                      <>
                        <div className="px-2 py-0.5 bg-slate-700/40 border-b border-slate-700 flex items-center justify-between">
                          <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">
                            Columns — {sourceShort.toUpperCase()}
                          </span>
                          <span className="text-[9px] text-slate-500">({targetColumns.length})</span>
                        </div>
                        {targetColumns.map((col: ColumnMeta) => {
                          const isSelected = selectedTarget === col.qualified_name;
                          return (
                            <button
                              key={col.qualified_name}
                              onClick={() => setSelectedTarget(col.qualified_name)}
                              className={`block w-full text-left px-2 py-0.5 text-[10px] border-l-2 ${
                                isSelected
                                  ? "bg-slate-700/60 text-emerald-300 border-emerald-400"
                                  : "text-slate-300 border-transparent hover:bg-slate-700/40 hover:text-slate-100"
                              }`}
                            >
                              <span className="font-medium">{col.column_name}</span>
                              <span className="ml-1 text-[8px] text-slate-500">
                                {col.data_type}
                                {col.primary_key && (
                                  <span className="ml-1 text-amber-400 font-semibold">PK</span>
                                )}
                                {col.not_null && !col.primary_key && (
                                  <span className="ml-1 text-slate-600">NN</span>
                                )}
                              </span>
                            </button>
                          );
                        })}
                      </>
                    )
                  ) : isLoadingEntities ? (
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
                            Tables
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
                              <span className="font-medium">{rec.table_name}</span>
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
                  {isContains ? (
                    <p className="text-[11px] text-slate-400 mt-0.5 font-mono">
                      {selectedTarget}
                    </p>
                  ) : (
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Collection: {selectedTarget.split(" ")[0].toUpperCase()}
                    </p>
                  )}
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
                    {selectedPredicate.toLowerCase()}
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

              {/* Horizontal context strip — attrs differ by form mode */}
              <div className="flex-1 flex items-center gap-1.5 flex-wrap justify-end">
                <span className="text-[9px] uppercase tracking-widest text-slate-500 mr-1">Attrs:</span>
                <span className="border border-slate-600 rounded bg-slate-700/50 px-1.5 py-0.5 text-[10px] text-slate-300">
                  edge_type: <span className="text-slate-200">{selectedPredicate}</span>
                </span>
                {isStructural ? (
                  <>
                    <span className="border border-slate-600 rounded bg-slate-700/50 px-1.5 py-0.5 text-[10px] text-slate-300">
                      from: <span className="text-cyan-300">{sourceShort.toUpperCase()}</span>
                    </span>
                    <span className="border border-slate-600 rounded bg-slate-700/50 px-1.5 py-0.5 text-[10px] text-slate-300">
                      to: <span className="text-cyan-300">{targetShort.toUpperCase()}</span>
                    </span>
                  </>
                ) : (
                  <>
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
                  </>
                )}
                <Pencil size={11} className="text-slate-500 cursor-pointer hover:text-slate-300 ml-1" />
              </div>
            </div>
          </div>
        </div>

        {/* Bottom action buttons */}
        <div className="border-t border-slate-700/50 px-4 pt-3 pb-3 flex flex-col gap-2 bg-[#1e1e2e]">
          {/* Live edge-count badge with per-collection tooltip */}
          <div className="flex items-center gap-1.5 self-end relative">
            <span className="text-[9px] uppercase tracking-widest text-slate-500">Graph:</span>
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border cursor-default transition-colors ${
                graphEdgeCount === null
                  ? "bg-slate-800 border-slate-600 text-slate-500 animate-pulse"
                  : "bg-violet-900/50 border-violet-600/60 text-violet-300"
              }`}
              onMouseEnter={() => setBadgeHovered(true)}
              onMouseLeave={() => setBadgeHovered(false)}
            >
              {graphEdgeCount === null
                ? "Loading…"
                : `${graphEdgeCount} edges`}
              {edgeDelta !== null && (
                <span className={`text-[9px] font-bold ${edgeDelta > 0 ? "text-emerald-400" : "text-rose-400"}`}>
                  {edgeDelta > 0 ? `+${edgeDelta}` : `${edgeDelta}`}
                </span>
              )}
            </span>

            {/* Popover — shown while hovering badge and stats are loaded */}
            {badgeHovered && graphStats !== null && (
              <div
                className="absolute bottom-full right-0 mb-2 z-50 min-w-[200px] rounded-md border border-slate-600 bg-slate-900 shadow-xl text-[10px] text-slate-300 py-2"
                onMouseEnter={() => setBadgeHovered(true)}
                onMouseLeave={() => setBadgeHovered(false)}
              >
                {/* ArangoDB section */}
                <p className="px-3 pb-1 text-[9px] uppercase tracking-widest text-slate-500 border-b border-slate-700/60 mb-1">
                  {graphStats.arango_available ? "ArangoDB collections" : "ArangoDB offline — showing SQLite counts only"}
                </p>
                {Object.entries(graphStats.collections).map(([col, count]) => (
                  <div key={col} className="flex items-center justify-between px-3 py-0.5">
                    <span className={graphStats.arango_available ? "text-violet-300" : "text-slate-500 italic"}>
                      {col}
                    </span>
                    <span className={`font-semibold tabular-nums ${graphStats.arango_available ? "text-slate-100" : "text-slate-600"}`}>
                      {count}
                    </span>
                  </div>
                ))}

                {/* SQLite bridge rows section */}
                <p className="px-3 pt-2 pb-1 text-[9px] uppercase tracking-widest text-slate-500 border-t border-slate-700/60 mt-1">
                  SQLite bridge rows
                </p>
                <div className="flex items-center justify-between px-3 py-0.5">
                  <span className="text-emerald-400">schema_intent_perspectives + schema_perspective_concepts</span>
                  <span className="font-semibold tabular-nums text-slate-100 ml-3 shrink-0">{graphStats.sqlite_bridge_rows}</span>
                </div>

                {/* Total */}
                <div className="flex items-center justify-between px-3 pt-1.5 mt-1 border-t border-slate-700/60">
                  <span className="text-slate-400 font-semibold">Total</span>
                  <span className="font-semibold tabular-nums text-violet-300">{graphStats.total_edges}</span>
                </div>
              </div>
            )}
          </div>
          {undoConfirm && (
            <div className="text-[10px] font-medium px-3 py-1.5 rounded flex items-center gap-2 bg-slate-700/70 border border-slate-500/60 text-slate-300 dr-fade-in">
              <span>↩</span>
              <span className="flex-1">
                Removed: <span className="text-slate-100 font-semibold">{undoConfirm.predicate}</span> edge (
                <span className="text-slate-100">{undoConfirm.source}</span> → <span className="text-slate-100">{undoConfirm.target}</span>)
              </span>
              <button
                className="ml-1 shrink-0 text-slate-500 hover:text-slate-200 cursor-pointer bg-transparent border-0 p-0"
                title="Dismiss"
                onClick={() => {
                  if (undoConfirmTimerRef.current) clearTimeout(undoConfirmTimerRef.current);
                  setUndoConfirm(null);
                }}
              >
                <X size={10} />
              </button>
            </div>
          )}
          {recentAdditions.length > 0 && (
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between px-0.5">
                <p className="text-[9px] uppercase tracking-widest text-slate-500">
                  Recent additions ({recentAdditions.length}/{MAX_HISTORY})
                </p>
                {/* TTL slider — adjusts how long entries stay visible (#94) */}
                <label className="flex items-center gap-1.5 text-[9px] text-slate-600 cursor-pointer select-none">
                  <span>Keep</span>
                  <input
                    type="range"
                    min={5}
                    max={120}
                    step={5}
                    value={historyTtlMs / 1000}
                    onChange={(e) => setHistoryTtlMs(parseInt(e.target.value) * 1000)}
                    className="w-16 accent-violet-500"
                    title={`History visible for ${historyTtlMs / 1000}s`}
                  />
                  <span className="min-w-[26px]">{historyTtlMs / 1000}s</span>
                </label>
              </div>
              {recentAdditions.map((entry) => (
                <div
                  key={entry.id}
                  className={`text-[10px] font-medium px-3 py-1.5 rounded flex items-center gap-2 ${
                    entry.ok
                      ? "bg-emerald-900/60 border border-emerald-600/50 text-emerald-300"
                      : "bg-rose-900/60 border border-rose-600/50 text-rose-300"
                  }`}
                >
                  <span>{entry.ok ? "✓" : "✗"}</span>
                  <span className="flex-1 min-w-0 truncate">
                    {entry.ok
                      ? <>
                          <span className="font-semibold text-emerald-200">{entry.predicate}</span>
                          {" "}
                          <span className="text-slate-300">{entry.source.split(" ")[0]}</span>
                          <span className="text-slate-500 mx-1">→</span>
                          <span className="text-slate-300">{entry.target.split(" ")[0]}</span>
                        </>
                      : entry.message
                    }
                  </span>
                  {entry.ok && entry.edge_id && (
                    <button
                      className="ml-auto shrink-0 underline text-emerald-400 hover:text-emerald-200 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer bg-transparent border-0 p-0 text-[10px] font-semibold"
                      disabled={undoingEdgeId !== null}
                      onClick={async () => {
                        setUndoingEdgeId(entry.id);
                        try {
                          const result = await undoEdge(entry.edge_id!);
                          if (result.ok) {
                            removeHistoryEntry(entry.id);
                            refreshGraphStats();
                            if (undoConfirmTimerRef.current) clearTimeout(undoConfirmTimerRef.current);
                            setUndoConfirm({ predicate: entry.predicate, source: entry.source, target: entry.target });
                            undoConfirmTimerRef.current = setTimeout(() => setUndoConfirm(null), 3000);
                          } else {
                            setRecentAdditions((prev) =>
                              prev.map((e) =>
                                e.id === entry.id
                                  ? { ...e, ok: false, message: `Undo failed: ${result.message}`, edge_id: undefined }
                                  : e
                              )
                            );
                            scheduleExpiry(entry.id, 5000);
                          }
                        } catch (err: unknown) {
                          const msg = err instanceof Error ? err.message : String(err);
                          setRecentAdditions((prev) =>
                            prev.map((e) =>
                              e.id === entry.id
                                ? { ...e, ok: false, message: `Undo failed: ${msg}`, edge_id: undefined }
                                : e
                            )
                          );
                          scheduleExpiry(entry.id, 5000);
                        } finally {
                          setUndoingEdgeId(null);
                        }
                      }}
                    >
                      {undoingEdgeId === entry.id ? "Undoing…" : "Undo"}
                    </button>
                  )}
                  {(!entry.edge_id) && (
                    <button
                      className="ml-auto shrink-0 text-slate-500 hover:text-slate-300 cursor-pointer bg-transparent border-0 p-0"
                      onClick={() => removeHistoryEntry(entry.id)}
                      title="Dismiss"
                    >
                      <X size={10} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
          <div className="flex items-center gap-3">
          <button
            className="flex-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-[11px] font-bold tracking-widest uppercase py-2.5 rounded transition-colors"
            disabled={isCommitting}
            onClick={async () => {
              setIsCommitting(true);
              const snapshotPredicate = selectedPredicate;
              const snapshotSource = selectedSource;
              const snapshotTarget = selectedTarget;
              try {
                const result = await commitEdge(
                  snapshotPredicate,
                  snapshotSource,
                  snapshotTarget,
                  selectedIntent,
                  activeCategory,
                  selectedConcept,
                );
                const entryId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
                const entry: HistoryEntry = {
                  id: entryId,
                  ok: result.ok,
                  message: result.message,
                  edge_id: result.edge_id,
                  predicate: snapshotPredicate,
                  source: snapshotSource,
                  target: snapshotTarget,
                  addedAt: Date.now(),
                };
                setRecentAdditions((prev) => [entry, ...prev].slice(0, MAX_HISTORY));
                if (result.ok) {
                  refreshGraphStats();
                  if (result.edge_id) {
                    scheduleExpiry(entryId, historyTtlMs);
                  } else {
                    scheduleExpiry(entryId, 4000);
                  }
                } else {
                  scheduleExpiry(entryId, 6000);
                }
              } catch (err: unknown) {
                const msg = err instanceof Error ? err.message : String(err);
                const entryId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
                const entry: HistoryEntry = {
                  id: entryId,
                  ok: false,
                  message: msg,
                  predicate: snapshotPredicate,
                  source: snapshotSource,
                  target: snapshotTarget,
                  addedAt: Date.now(),
                };
                setRecentAdditions((prev) => [entry, ...prev].slice(0, MAX_HISTORY));
                scheduleExpiry(entryId, 6000);
              } finally {
                setIsCommitting(false);
              }
            }}
          >
            {isCommitting ? "Saving…" : "Add to Graph"}
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
    </div>
  );
}
