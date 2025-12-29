#!/usr/bin/env python3
"""
Normalize NetworkX node metadata using schema/ folder.

- Loads schema/collections.yml to get known table names (optional).
- Loads optional schema/candidate_keys.yaml for hints.
- For each node:
    * If node['table'] exists, keep it.
    * Else try to infer table from node attributes (table/table_name/schema/type) or
      from node id/label tokens by matching known table names.
    * Set node['_key'] to a deterministic sanitized string: "<table>:<sanitized-node-id>"
- Writes an output graph pickle (or prints dry-run summary).

Usage:
  python normalize_nodes_with_schema.py --in graph.pkl --out graph_normalized.pkl --schema-dir schema --dry-run
  python normalize_nodes_with_schema.py --in graph.pkl --out graph_normalized.pkl --schema-dir schema

Notes:
- Back up your original graph before running for real.
- This script does NOT persist to Arango. Use your persist_networkx_to_arango.py afterwards.
"""
import argparse
import os
import pickle
import re
import hashlib
import yaml

def load_collections(schema_dir):
    cfg_path = os.path.join(schema_dir, "collections.yml")
    if not os.path.exists(cfg_path):
        return {}
    with open(cfg_path, "r", encoding="utf-8") as fh:
        try:
            cfg = yaml.safe_load(fh) or {}
            return cfg.get("vertices", {})  # mapping logical_table -> collection_name
        except Exception:
            return {}

def load_candidate_keys(schema_dir):
    path = os.path.join(schema_dir, "candidate_keys.yaml")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as fh:
        try:
            return yaml.safe_load(fh) or []
        except Exception:
            return []

_key_re = re.compile(r'[^A-Za-z0-9_\-\.]')

def sanitize_key_component(s: str) -> str:
    if s is None:
        s = ""
    s = str(s)
    s = _key_re.sub('_', s)
    if len(s) > 120:
        h = hashlib.sha1(s.encode('utf-8')).hexdigest()
        s = s[:60] + '_' + h[:40]
    return s

def normalized_node_key(table: str, node_id: str, prefix=True):
    comp = sanitize_key_component(node_id)
    if prefix and table:
        t = sanitize_key_component(table)
        return f"{t}:{comp}"
    return comp

def infer_table_from_node(node_id, attrs, known_tables=None):
    # 1) direct attrs
    for k in ("table","schema","table_name","type"):
        v = attrs.get(k)
        if v:
            return v

    # 2) field_refs or similar attributes might reference "table.column"
    for k, v in attrs.items():
        if isinstance(v, str) and "." in v:
            cand_table = v.split(".", 1)[0]
            if known_tables:
                for t in known_tables:
                    if cand_table.lower() == t.lower():
                        return t
            else:
                return cand_table

    # 3) parse node id/label tokens for candidate table names
    s = str(node_id)
    s2 = re.sub(r'^\s*\d+\s*[-:]\s*', '', s)  # remove leading numeric prefix like "2 - "
    tokens = re.split(r'[\s_\-:]+', s2)
    # check tokens against known tables if provided
    if known_tables:
        for t in known_tables:
            for tok in tokens:
                if tok and (tok.lower() in t.lower() or t.lower() in tok.lower()):
                    return t
    # fallback: return last non-empty token (best-effort)
    for tkn in reversed(tokens):
        if tkn:
            # strip common suffixes like 'node'
            t = tkn
            if t.endswith("node"):
                t = t.replace("_node", "").replace("node", "")
            return t
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", required=True, help="Input pickled NetworkX graph")
    ap.add_argument("--out", dest="outfile", required=True, help="Output pickled graph")
    ap.add_argument("--schema-dir", default="schema", help="Schema folder (collections.yml, candidate_keys.yaml)")
    ap.add_argument("--columns-to-ref", default="", help="Comma-separated column names to set field_refs for (optional)")
    ap.add_argument("--prefix-key", action="store_true", help="Prefix node keys with table (default: False)")
    ap.add_argument("--dry-run", action="store_true", help="Do not write output; show summary only")
    ap.add_argument("--preview", type=int, default=20, help="Number of changed nodes to preview")
    args = ap.parse_args()

    infile = args.infile
    outfile = args.outfile
    schema_dir = args.schema_dir
    columns_to_ref = [c.strip() for c in args.columns_to_ref.split(",")] if args.columns_to_ref else []
    prefix = args.prefix_key

    if not os.path.exists(infile):
        raise SystemExit(f"Input file not found: {infile}")

    # load graph
    with open(infile, "rb") as fh:
        G = pickle.load(fh)

    # load schema hints
    known_vertices = load_collections(schema_dir)
    known_tables = list(known_vertices.keys()) if known_vertices else []
    candidate_keys = load_candidate_keys(schema_dir)

    changed = []
    missing_table_nodes = []
    total = 0
    for n, attrs in list(G.nodes(data=True)):
        total += 1
        old_table = attrs.get("table")
        inferred = None
        if not old_table:
            inferred = infer_table_from_node(n, attrs, known_tables=known_tables)
            if inferred:
                G.nodes[n]['table'] = inferred
            else:
                missing_table_nodes.append(n)
        # set deterministic _key
        table_for_key = G.nodes[n].get('table') or 'default'
        new_key = normalized_node_key(table_for_key, n, prefix=prefix)
        prev_key = attrs.get("_key") or attrs.get("key") or None
        if prev_key != new_key:
            G.nodes[n]['_key'] = new_key
            changed.append((n, prev_key, new_key, G.nodes[n].get('table')))
        # optional field_refs
        if columns_to_ref:
            refs = {}
            for col in columns_to_ref:
                if col in attrs:
                    refs[col] = f"{G.nodes[n].get('table','default')}.{col}"
            if refs:
                prev_refs = G.nodes[n].get('field_refs', {})
                prev_refs.update(refs)
                G.nodes[n]['field_refs'] = prev_refs

    # report
    print(f"Total nodes processed: {total}")
    print(f"Nodes updated with new _key: {len(changed)}")
    print(f"Nodes still missing 'table' attribute: {len(missing_table_nodes)}")
    if changed and args.preview > 0:
        print("\nPreview of changed nodes (first {0}):".format(min(len(changed), args.preview)))
        for idx, (n, prev, new, tbl) in enumerate(changed[:args.preview], 1):
            print(f"{idx}. node={n} table={tbl} prev_key={prev} new_key={new}")

    if missing_table_nodes:
        print("\nExamples of nodes missing table (first 10):")
        for n in missing_table_nodes[:10]:
            print(f" - {n} attrs: {dict(G.nodes[n])}")

    if args.dry_run:
        print("\nDry-run enabled: no file will be written.")
        return

    # write out modified graph
    out_dir = os.path.dirname(outfile)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    with open(outfile, "wb") as fh:
        pickle.dump(G, fh)
    print(f"\nWrote normalized graph to: {outfile}")

if __name__ == "__main__":
    main()