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
  python replit_integrations/sql_graph_parity_check.py || {
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
  # SQL (SQLite tables) vs AQL (live ArangoDB graph). Offline-tolerant: an
  # unreachable/unconfigured graph is a skip, a real field drift is a failure.
  python replit_integrations/sql_aql_parity_check.py --skip-on-missing || {
    echo "post-merge: SQLite <-> live ArangoDB (SQL vs AQL) parity check failed"
    exit 1
  }
fi

echo "post-merge: OK"
