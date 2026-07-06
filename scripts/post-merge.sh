#!/bin/bash
set -e

if [ -f requirements.txt ]; then
  uv pip install --quiet --python .pythonlibs/bin/python -r requirements.txt || true
fi

if [ -f hf-space-inventory-sqlgen/requirements.txt ]; then
  uv pip install --quiet --python .pythonlibs/bin/python -r hf-space-inventory-sqlgen/requirements.txt || true
fi

# Self-heal stale SQL graph source tables (sql_graph_nodes / sql_graph_edges).
# main's app DB (manufacturing.db) is gitignored, so when a task re-exports the
# graph it bumps the committed graph_metadata.json, but main's persistent
# sql_graph_* tables (materialized in the task's own gitignored DB) lag behind and
# the parity gate below then fails. Re-materialize the tables from the schema to
# heal that staleness — but ONLY when they are already out of parity with the
# committed JSON. If they already match, do nothing: re-exporting unconditionally
# would pull in ERP columns that were added to the schema but not yet curated into
# the graph and wrongly fail the build (additive ERP schema changes are
# graph-invisible by design). The committed JSON is preserved across the export so
# the downstream parity check still compares the *committed* JSON against the
# freshly-materialized tables — real drift (or a hand-edited / stale JSON) still
# fails, while mere DB staleness self-heals. Guarded on the DB existing so a
# no-DB environment falls through to the existing skip/error handling.
_app_db="hf-space-inventory-sqlgen/app_schema/manufacturing.db"
if [ -f "$_app_db" ] \
  && [ -f replit_integrations/seed_elevations.py ] \
  && [ -f replit_integrations/export_graph_metadata.py ] \
  && [ -f replit_integrations/sql_graph_parity_check.py ]; then
  if ! python replit_integrations/sql_graph_parity_check.py >/dev/null 2>&1; then
    # Two distinct failure shapes:
    #   1. EMPTY tables (fresh-bootstrap DB): the bridge feeds the exporter
    #      materializes from are not part of the bootstrap chain, so the DB
    #      cannot re-derive the frozen graph — the committed JSON is the only
    #      surviving copy. Restore the tables FROM it (import_graph_metadata.py,
    #      which refuses to overwrite populated tables). seed_elevations still
    #      runs first so the semantic bridge vocabulary (concepts/elevations the
    #      app + Query Palette read) is repopulated too.
    #   2. POPULATED-but-stale tables: re-materialize from the schema as before.
    _sg_nodes=$(sqlite3 "$_app_db" "SELECT COUNT(*) FROM sql_graph_nodes" 2>/dev/null || echo 0)
    if [ "${_sg_nodes:-0}" -eq 0 ] && [ -f replit_integrations/import_graph_metadata.py ]; then
      echo "post-merge: sql_graph_* tables are empty (fresh DB) — restoring from committed graph_metadata.json"
      python replit_integrations/seed_elevations.py || {
        echo "post-merge: seed_elevations regeneration failed"
        exit 1
      }
      # Re-apply the schema seed AFTER seed_elevations: its intent->concept link
      # inserts are name-based INSERT..SELECTs that silently insert zero rows on
      # a fresh bootstrap (the concepts do not exist yet at that point in the
      # chain). Same INSERT OR IGNORE transform the app applies on boot.
      python - <<'PYEOF' || { echo "post-merge: schema seed re-apply failed"; exit 1; }
import sqlite3
sql = open("hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql").read()
sql = sql.replace("INSERT INTO", "INSERT OR IGNORE INTO")
conn = sqlite3.connect("hf-space-inventory-sqlgen/app_schema/manufacturing.db")
conn.executescript(sql)
conn.commit()
conn.close()
PYEOF
      python replit_integrations/import_graph_metadata.py || {
        echo "post-merge: graph restore from committed JSON failed"
        exit 1
      }
    else
    echo "post-merge: sql_graph_* tables are stale vs committed graph_metadata.json — re-materializing"
    _gm_json="replit_integrations/graph_metadata.json"
    _gm_bak=""
    if [ -f "$_gm_json" ]; then
      _gm_bak="$(mktemp)"
      cp "$_gm_json" "$_gm_bak"
      # If the exporter fails mid-run after rewriting the JSON, restore the
      # committed copy on exit so the tracked file is never left modified.
      trap 'if [ -n "$_gm_bak" ] && [ -f "$_gm_bak" ]; then cp "$_gm_bak" "$_gm_json"; rm -f "$_gm_bak"; fi' EXIT
    fi
    python replit_integrations/seed_elevations.py || {
      echo "post-merge: seed_elevations regeneration failed"
      exit 1
    }
    python replit_integrations/export_graph_metadata.py || {
      echo "post-merge: export_graph_metadata regeneration failed"
      exit 1
    }
    # Restore the committed graph_metadata.json now (before the parity gates) so the
    # gate compares the *committed* JSON against the freshly-materialized tables and
    # still catches a stale/hand-edited committed JSON instead of becoming a tautology.
    if [ -n "$_gm_bak" ] && [ -f "$_gm_bak" ]; then
      cp "$_gm_bak" "$_gm_json"
      rm -f "$_gm_bak"
      _gm_bak=""
    fi
    trap - EXIT
    fi
  fi
fi

if [ -f hf-space-inventory-sqlgen/tests/test_perspective_deprecation.py ]; then
  python hf-space-inventory-sqlgen/tests/test_perspective_deprecation.py || {
    echo "post-merge: perspective deprecation regression failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/scripts/check_legacy_perspective_refs.py ]; then
  python hf-space-inventory-sqlgen/scripts/check_legacy_perspective_refs.py || {
    echo "post-merge: legacy perspective grep gate failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/scripts/check_legacy_elevates_refs.py ]; then
  python hf-space-inventory-sqlgen/scripts/check_legacy_elevates_refs.py || {
    echo "post-merge: legacy elevates (v16 resolves_to rename) grep gate failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_sync_db_to_dab_config.py ]; then
  python hf-space-inventory-sqlgen/tests/test_sync_db_to_dab_config.py || {
    echo "post-merge: DAB sync tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_field_description_pipeline.py ]; then
  python hf-space-inventory-sqlgen/tests/test_field_description_pipeline.py || {
    echo "post-merge: field description pipeline tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_metric_assembly.py ]; then
  python hf-space-inventory-sqlgen/tests/test_metric_assembly.py || {
    echo "post-merge: metric assembly tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_get_resolves_to.py ]; then
  python hf-space-inventory-sqlgen/tests/test_get_resolves_to.py || {
    echo "post-merge: get_resolves_to endpoint tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_mrp_schedule.py ]; then
  python hf-space-inventory-sqlgen/tests/test_mrp_schedule.py || {
    echo "post-merge: MRP schedule grid tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_demand_linkage.py ]; then
  python hf-space-inventory-sqlgen/tests/test_demand_linkage.py || {
    echo "post-merge: demand linkage + forecast tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_three_way_match_data.py ]; then
  python hf-space-inventory-sqlgen/tests/test_three_way_match_data.py || {
    echo "post-merge: three-way match data tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_demand_expansion.py ]; then
  python hf-space-inventory-sqlgen/tests/test_demand_expansion.py || {
    echo "post-merge: demand expansion tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_procurement_views.py ]; then
  python hf-space-inventory-sqlgen/tests/test_procurement_views.py || {
    echo "post-merge: procurement view tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_structural_fingerprint.py ]; then
  python hf-space-inventory-sqlgen/tests/test_structural_fingerprint.py || {
    echo "post-merge: structural fingerprint tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_register_snippet_v2.py ]; then
  python hf-space-inventory-sqlgen/tests/test_register_snippet_v2.py || {
    echo "post-merge: register_snippet v2 fingerprint tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_mrp_query_palette.py ]; then
  python hf-space-inventory-sqlgen/tests/test_mrp_query_palette.py || {
    echo "post-merge: MRP query palette tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_mrp_keyword_routing.py ]; then
  python hf-space-inventory-sqlgen/tests/test_mrp_keyword_routing.py || {
    echo "post-merge: MRP keyword routing tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_db_init_self_heal.py ]; then
  python hf-space-inventory-sqlgen/tests/test_db_init_self_heal.py || {
    echo "post-merge: DB init self-heal tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_operation_schedule_cost_accrual.py ]; then
  python hf-space-inventory-sqlgen/tests/test_operation_schedule_cost_accrual.py || {
    echo "post-merge: operation schedule + cost-accrual tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_ontology_mosaic.py ]; then
  python hf-space-inventory-sqlgen/tests/test_ontology_mosaic.py || {
    echo "post-merge: ontology mosaic cascade + semantic ontology tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_labor_chain_reconciliation.py ]; then
  python hf-space-inventory-sqlgen/tests/test_labor_chain_reconciliation.py || {
    echo "post-merge: labor chain reconciliation tests failed"
    exit 1
  }
fi

if [ -f replit_integrations/field_description_coverage_check.py ]; then
  python replit_integrations/field_description_coverage_check.py || {
    echo "post-merge: field description graph coverage check failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_temporal_contract_validation.py ]; then
  # SolderEngine temporal-parameter contract validation + the fail-closed
  # zero-weight enforcement gate: reads the owl:complementOf-flagged (zero-weight)
  # contexts from the inventory-transactions ontology and asserts none has a
  # resolves_to edge in the governed graph (committed graph_metadata.json AND the
  # SQLite sql_graph_edges source of truth), so a future graph change can never
  # silently elevate a field the ontology declares to carry zero semantic weight.
  python hf-space-inventory-sqlgen/tests/test_temporal_contract_validation.py || {
    echo "post-merge: temporal contract + zero-weight enforcement tests failed"
    exit 1
  }
fi

if [ -f poc/ontop-ontology-poc/mapping_drift_check.py ]; then
  # Offline drift guard for the Ontop POC: proves the hand-authored .obda mapping
  # and .ttl ontology stay aligned with the governed graph_metadata.json (file vs
  # file, no DB/network). --skip-on-missing degrades gracefully if the POC files
  # are absent from a stripped checkout.
  python poc/ontop-ontology-poc/mapping_drift_check.py --skip-on-missing || {
    echo "post-merge: Ontop ontology/mapping drift check failed"
    exit 1
  }
fi

if [ -f poc/ontop-ontology-poc/mapping_generation_check.py ]; then
  # Offline equivalence gate for the Ontop POC mapping GENERATOR: proves the
  # generated .obda is byte-identical to the committed hand-authored mapping (so
  # the switch to generation is provably lossless), the committed generated
  # vocabulary is fresh, and every generated term is declared in the runtime
  # ontology — all file vs file, no DB/network. --skip-on-missing degrades
  # gracefully if the POC files are absent from a stripped checkout.
  python poc/ontop-ontology-poc/mapping_generation_check.py --skip-on-missing || {
    echo "post-merge: Ontop mapping generation equivalence check failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_masking_policy_pipeline.py ]; then
  python hf-space-inventory-sqlgen/tests/test_masking_policy_pipeline.py || {
    echo "post-merge: masking policy pipeline tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_sync_masking_to_dab_config.py ]; then
  python hf-space-inventory-sqlgen/tests/test_sync_masking_to_dab_config.py || {
    echo "post-merge: masking DAB sync tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_masking_matrix.py ]; then
  python hf-space-inventory-sqlgen/tests/test_masking_matrix.py || {
    echo "post-merge: masking matrix tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_masking_type.py ]; then
  python hf-space-inventory-sqlgen/tests/test_masking_type.py || {
    echo "post-merge: masking type tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_reconstruct_containment_graph.py ]; then
  python hf-space-inventory-sqlgen/tests/test_reconstruct_containment_graph.py || {
    echo "post-merge: graph reconstructor tests failed"
    exit 1
  }
fi

if [ -f scripts/verify_metadata_meaning.py ]; then
  python scripts/verify_metadata_meaning.py --skip-on-no-arango --allow-sweep1-gaps || {
    echo "post-merge: metadata meaning verification failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_sweep1_coverage_gaps.py ]; then
  python hf-space-inventory-sqlgen/tests/test_sweep1_coverage_gaps.py || {
    echo "post-merge: sweep1 coverage gap tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_approved_snippets_execute.py ]; then
  python hf-space-inventory-sqlgen/tests/test_approved_snippets_execute.py || {
    echo "post-merge: approved snippet execution tests failed"
    exit 1
  }
fi

if [ -f tests/test_semantic_scaffolding.py ]; then
  python tests/test_semantic_scaffolding.py || {
    echo "post-merge: semantic scaffolding format-lock tests failed"
    exit 1
  }
fi

if [ -f tests/test_sql_graph_tables.py ]; then
  python tests/test_sql_graph_tables.py || {
    echo "post-merge: SQL graph source table tests failed"
    exit 1
  }
fi

if [ -f tests/test_authored_edges_merge.py ]; then
  python tests/test_authored_edges_merge.py || {
    echo "post-merge: SME-authored edge merge tests failed"
    exit 1
  }
fi

if [ -f hf-space-inventory-sqlgen/tests/test_commit_edge_sqlite_first.py ]; then
  python hf-space-inventory-sqlgen/tests/test_commit_edge_sqlite_first.py || {
    echo "post-merge: SQLite-first canonical edge authoring tests failed"
    exit 1
  }
fi

if [ -f replit_integrations/sql_graph_parity_check.py ]; then
  python replit_integrations/sql_graph_parity_check.py \
    --report-file replit_integrations/sql_graph_parity_report.txt \
    --csv-dir replit_integrations || {
    echo "post-merge: SQLite <-> graph_metadata.json parity check failed"
    exit 1
  }
fi

if [ -f tests/test_sql_aql_parity.py ]; then
  python tests/test_sql_aql_parity.py || {
    echo "post-merge: SQL vs AQL parity tests failed"
    exit 1
  }
fi

if [ -f replit_integrations/sql_aql_parity_check.py ]; then
  # SQL (SQLite tables) vs AQL (live ArangoDB graph). WARN-ONLY (non-fatal):
  # the shared live graph is on the legacy concept_-prefixed key model and is
  # raced by external main-version loads, so this check is non-deterministic and
  # fails independently (documented out-of-scope in replit.md). The authoritative
  # acceptance gate is sql_graph_parity_check.py (SQLite <-> graph_metadata.json),
  # which runs fatally elsewhere. We still run this to emit the report/CSVs.
  python replit_integrations/sql_aql_parity_check.py --skip-on-missing \
    --report-file replit_integrations/sql_aql_parity_report.txt \
    --csv-dir replit_integrations || {
    echo "post-merge: WARNING — SQLite <-> live ArangoDB (SQL vs AQL) parity check"
    echo "post-merge:   reported drift; non-fatal (live graph is out-of-scope/legacy"
    echo "post-merge:   key model, raced by external loads). See report above."
  }
fi

if [ -f tests/test_mrp_approval_committer.py ]; then
  python tests/test_mrp_approval_committer.py || {
    echo "post-merge: MRP approval committer tests failed"
    exit 1
  }
fi

if [ -f tests/test_mrp_term_promoter.py ]; then
  python tests/test_mrp_term_promoter.py || {
    echo "post-merge: MRP term promoter tests failed"
    exit 1
  }
fi

echo "post-merge: OK"
