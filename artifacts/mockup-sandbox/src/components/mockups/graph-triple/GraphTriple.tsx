import { useState, useRef } from "react";
import { ArrowRight, Check, X, RotateCcw, Search, Zap } from "lucide-react";

type Predicate =
  | "RESOLVES_TO"
  | "HAS_COLUMN"
  | "references"
  | "MAPS_TO_CONCEPT"
  | "BOUND_TO"
  | "OPERATES_WITHIN";

type EntityType = "intent" | "concept" | "table" | "column" | "binding";

interface Entity {
  id: string;
  label: string;
  type: EntityType;
  namespace?: string;
}

interface Triple {
  subject: Entity;
  predicate: Predicate;
  object: Entity;
  committedAt: string;
}

const PREDICATE_META: Record<Predicate, { color: string; bg: string; desc: string; allowedSubject: EntityType[]; allowedObject: EntityType[] }> = {
  RESOLVES_TO:     { color: "text-amber-700",   bg: "bg-amber-50 border-amber-300",     desc: "Binary gate: weight=1 activates, weight=0 deactivates. Table or column → Concept. AI selects among weight=1 ground truths.", allowedSubject: ["table", "column"], allowedObject: ["concept"] },
  HAS_COLUMN:      { color: "text-cyan-700",     bg: "bg-cyan-50 border-cyan-300",       desc: "Table owns this column node. Column name is the semantic claim.",                                                              allowedSubject: ["table"],           allowedObject: ["column"] },
  references:      { color: "text-indigo-700",   bg: "bg-indigo-50 border-indigo-300",   desc: "Structural references edge: child column → parent column (carries references_table/references_column). The FK flag itself is the foreign_key boolean on the column node.", allowedSubject: ["column"],          allowedObject: ["column"] },
  MAPS_TO_CONCEPT: { color: "text-emerald-700",  bg: "bg-emerald-50 border-emerald-300", desc: "ERP table bridges to a semantic concept.",                                                                                     allowedSubject: ["table"],           allowedObject: ["concept"] },
  BOUND_TO:        { color: "text-violet-700",   bg: "bg-violet-50 border-violet-300",   desc: "Binding resolves to approved SME SQL snippet.",                                                                                allowedSubject: ["binding"],         allowedObject: ["concept"] },
  OPERATES_WITHIN: { color: "text-fuchsia-700",  bg: "bg-fuchsia-50 border-fuchsia-300", desc: "Intent scoped to a perspective/domain. Perspective is an edge property, not a node.",                                        allowedSubject: ["intent"],          allowedObject: ["concept"] },
};

const TYPE_BADGE: Record<EntityType, string> = {
  intent:  "bg-blue-100 text-blue-700",
  concept: "bg-emerald-100 text-emerald-700",
  table:   "bg-slate-100 text-slate-700",
  column:  "bg-cyan-100 text-cyan-700",
  binding: "bg-violet-100 text-violet-700",
};

const SAMPLE_ENTITIES: Entity[] = [
  { id: "i1",  label: "defect_cost_analysis",   type: "intent",  namespace: "Quality" },
  { id: "i2",  label: "supplier_otd",            type: "intent",  namespace: "Procurement" },
  { id: "i3",  label: "wip_valuation",           type: "intent",  namespace: "Manufacturing" },
  { id: "c1",  label: "DEFECTSEVERITYCOST",      type: "concept", namespace: "Quality" },
  { id: "c2",  label: "SUPPLIERPERFOTD",         type: "concept", namespace: "Procurement" },
  { id: "c3",  label: "WIPVALUATION",            type: "concept", namespace: "Manufacturing" },
  { id: "t1",  label: "quality_events",          type: "table",   namespace: "ERP_Instance_1" },
  { id: "t2",  label: "purchase_orders",         type: "table",   namespace: "ERP_Instance_1" },
  { id: "t3",  label: "work_order_operations",   type: "table",   namespace: "ERP_Instance_1" },
  { id: "col1",label: "defect_cost",             type: "column",  namespace: "quality_events" },
  { id: "col2",label: "promised_ship_date",      type: "column",  namespace: "purchase_orders" },
  { id: "b1",  label: "binding::defect_cost",    type: "binding", namespace: "Quality" },
];

function EntityPill({ entity, onClear }: { entity: Entity; onClear?: () => void }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${TYPE_BADGE[entity.type]}`}>
      <span className="opacity-60 uppercase tracking-wider text-[10px]">{entity.type}</span>
      <span className="font-semibold">{entity.label}</span>
      {entity.namespace && <span className="opacity-50">· {entity.namespace}</span>}
      {onClear && (
        <button onClick={onClear} className="ml-1 rounded-full hover:bg-black/10 p-0.5 transition-colors">
          <X size={10} />
        </button>
      )}
    </span>
  );
}

function EntitySearch({
  placeholder,
  value,
  onChange,
  allowed,
}: {
  placeholder: string;
  value: Entity | null;
  onChange: (e: Entity | null) => void;
  allowed: EntityType[];
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const filtered = SAMPLE_ENTITIES.filter(
    (e) =>
      allowed.includes(e.type) &&
      (query === "" || e.label.toLowerCase().includes(query.toLowerCase()))
  );

  if (value) {
    return (
      <div className="flex items-center gap-2">
        <EntityPill entity={value} onClear={() => onChange(null)} />
      </div>
    );
  }

  return (
    <div className="relative" ref={ref}>
      <div className="flex items-center gap-1.5 border border-slate-300 rounded-lg px-3 py-2 bg-white focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-400 transition-all">
        <Search size={13} className="text-slate-400 flex-shrink-0" />
        <input
          className="flex-1 text-sm outline-none placeholder-slate-400 min-w-0 bg-transparent"
          placeholder={placeholder}
          value={query}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
        />
        {allowed.length > 0 && (
          <span className="text-[10px] text-slate-400 flex-shrink-0">
            {allowed.join(" · ")}
          </span>
        )}
      </div>
      {open && filtered.length > 0 && (
        <ul className="absolute z-50 top-full left-0 mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg max-h-48 overflow-auto">
          {filtered.map((e) => (
            <li
              key={e.id}
              className="flex items-center gap-2 px-3 py-2 hover:bg-slate-50 cursor-pointer text-sm transition-colors"
              onMouseDown={() => { onChange(e); setQuery(""); setOpen(false); }}
            >
              <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${TYPE_BADGE[e.type]}`}>
                {e.type}
              </span>
              <span className="font-medium text-slate-800">{e.label}</span>
              {e.namespace && <span className="text-slate-400 text-xs ml-auto">{e.namespace}</span>}
            </li>
          ))}
        </ul>
      )}
      {open && filtered.length === 0 && query && (
        <div className="absolute z-50 top-full left-0 mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg px-3 py-2 text-sm text-slate-500">
          No {allowed.join(" or ")} matching "{query}"
        </div>
      )}
    </div>
  );
}

export default function GraphTriple() {
  const [subject, setSubject] = useState<Entity | null>(null);
  const [predicate, setPredicate] = useState<Predicate | null>(null);
  const [object, setObject] = useState<Entity | null>(null);
  const [committed, setCommitted] = useState<Triple[]>([]);
  const [flash, setFlash] = useState(false);

  const meta = predicate ? PREDICATE_META[predicate] : null;
  const allowedSubject: EntityType[] = predicate ? meta!.allowedSubject : ["intent", "concept", "table", "column", "binding"];
  const allowedObject: EntityType[] = predicate ? meta!.allowedObject : ["intent", "concept", "table", "column", "binding"];

  const canCommit = subject && predicate && object;

  const subjectTypeOk = !subject || !predicate || meta!.allowedSubject.includes(subject.type);
  const objectTypeOk  = !object  || !predicate || meta!.allowedObject.includes(object.type);
  const typeWarning = (!subjectTypeOk || !objectTypeOk);

  function handleCommit() {
    if (!canCommit) return;
    const triple: Triple = {
      subject: subject!,
      predicate: predicate!,
      object: object!,
      committedAt: new Date().toLocaleTimeString(),
    };
    setCommitted((prev) => [triple, ...prev].slice(0, 10));
    setSubject(null);
    setPredicate(null);
    setObject(null);
    setFlash(true);
    setTimeout(() => setFlash(false), 800);
  }

  function handleUndo(idx: number) {
    setCommitted((prev) => prev.filter((_, i) => i !== idx));
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-start justify-center p-8">
      <div className="w-full max-w-2xl space-y-5">

        {/* Header */}
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-7 h-7 rounded-md bg-slate-800 flex items-center justify-center">
              <Zap size={14} className="text-amber-400" />
            </div>
            <h1 className="text-lg font-semibold text-slate-800">Graph Triple</h1>
          </div>
          <p className="text-sm text-slate-500">
            Commit a Subject → Predicate → Object relationship to the manufacturing graph.
          </p>
        </div>

        {/* Triple Builder Card */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">

          {/* Predicate selector strip */}
          <div className="border-b border-slate-100 px-5 py-3 bg-slate-50">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Predicate</p>
            <div className="flex flex-wrap gap-1.5">
              {(Object.keys(PREDICATE_META) as Predicate[]).map((p) => (
                <button
                  key={p}
                  onClick={() => { setPredicate(p); setSubject(null); setObject(null); }}
                  className={`px-2.5 py-1 rounded-full text-xs font-semibold border transition-all
                    ${predicate === p
                      ? `${PREDICATE_META[p].bg} ${PREDICATE_META[p].color} border-current shadow-sm`
                      : "bg-white text-slate-500 border-slate-200 hover:border-slate-300 hover:text-slate-700"
                    }`}
                >
                  {p}
                </button>
              ))}
            </div>
            {meta && (
              <p className={`mt-2 text-xs ${meta.color} font-medium`}>{meta.desc}</p>
            )}
          </div>

          {/* Subject · Arrow · Object */}
          <div className="px-5 py-5 space-y-4">
            <div className="grid grid-cols-[1fr_auto_1fr] gap-3 items-center">
              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Subject</label>
                <EntitySearch
                  placeholder={`Search ${allowedSubject.join(", ")}…`}
                  value={subject}
                  onChange={setSubject}
                  allowed={allowedSubject}
                />
                {subject && !subjectTypeOk && (
                  <p className="text-rose-500 text-xs mt-1">
                    {predicate} expects a {meta!.allowedSubject.join("/")} — got {subject.type}
                  </p>
                )}
              </div>

              <div className="flex flex-col items-center gap-0.5 pt-5">
                <ArrowRight
                  size={22}
                  className={predicate ? `${PREDICATE_META[predicate].color}` : "text-slate-300"}
                  strokeWidth={2.5}
                />
                {predicate && (
                  <span className={`text-[10px] font-bold uppercase tracking-widest ${PREDICATE_META[predicate].color} whitespace-nowrap`}>
                    {predicate}
                  </span>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Object</label>
                <EntitySearch
                  placeholder={`Search ${allowedObject.join(", ")}…`}
                  value={object}
                  onChange={setObject}
                  allowed={allowedObject}
                />
                {object && !objectTypeOk && (
                  <p className="text-rose-500 text-xs mt-1">
                    {predicate} expects a {meta!.allowedObject.join("/")} — got {object.type}
                  </p>
                )}
              </div>
            </div>

            {/* Live preview */}
            {(subject || predicate || object) && (
              <div className={`rounded-lg border px-4 py-3 text-sm font-mono transition-all ${
                typeWarning
                  ? "bg-rose-50 border-rose-200 text-rose-700"
                  : canCommit
                    ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                    : "bg-slate-50 border-slate-200 text-slate-600"
              }`}>
                <span className="text-slate-400 text-xs font-sans font-medium mr-2">TRIPLE</span>
                <span className="font-semibold">{subject?.label ?? "…"}</span>
                <span className="mx-2 opacity-50">—[</span>
                <span className={predicate ? (meta?.color ?? "") : "opacity-40"}>{predicate ?? "?"}</span>
                <span className="opacity-50">]→</span>
                <span className="font-semibold ml-2">{object?.label ?? "…"}</span>
              </div>
            )}

            {/* Commit button */}
            <button
              onClick={handleCommit}
              disabled={!canCommit || typeWarning}
              className={`w-full py-2.5 rounded-lg text-sm font-semibold transition-all flex items-center justify-center gap-2
                ${canCommit && !typeWarning
                  ? flash
                    ? "bg-emerald-600 text-white scale-[0.98]"
                    : "bg-slate-800 text-white hover:bg-slate-700 active:scale-[0.98]"
                  : "bg-slate-100 text-slate-400 cursor-not-allowed"
                }`}
            >
              {flash ? <><Check size={15} /> Committed</> : <><Zap size={15} /> Commit Triple</>}
            </button>
          </div>
        </div>

        {/* Committed triples log */}
        {committed.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Committed — {committed.length}
              </span>
              <button
                onClick={() => setCommitted([])}
                className="text-xs text-slate-400 hover:text-slate-600 flex items-center gap-1 transition-colors"
              >
                <X size={11} /> Clear all
              </button>
            </div>
            <ul className="divide-y divide-slate-50">
              {committed.map((t, i) => (
                <li key={i} className="px-5 py-3 flex items-center gap-3 group hover:bg-slate-50 transition-colors">
                  <div className="flex-1 flex items-center gap-2 text-sm font-mono min-w-0 flex-wrap">
                    <EntityPill entity={t.subject} />
                    <span className={`text-[11px] font-bold uppercase ${PREDICATE_META[t.predicate].color} flex-shrink-0`}>
                      —[{t.predicate}]→
                    </span>
                    <EntityPill entity={t.object} />
                  </div>
                  <span className="text-xs text-slate-400 flex-shrink-0">{t.committedAt}</span>
                  <button
                    onClick={() => handleUndo(i)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-400 hover:text-rose-500 flex items-center gap-1 text-xs"
                  >
                    <RotateCcw size={11} /> undo
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
