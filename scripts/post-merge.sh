#!/bin/bash
set -e

if [ -f requirements.txt ]; then
  pip install --quiet --disable-pip-version-check -r requirements.txt || true
fi

if [ -f hf-space-inventory-sqlgen/requirements.txt ]; then
  pip install --quiet --disable-pip-version-check -r hf-space-inventory-sqlgen/requirements.txt || true
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

if [ -f replit_integrations/sql_graph_parity_check.py ]; then
  python replit_integrations/sql_graph_parity_check.py || {
    echo "post-merge: SQLite <-> graph_metadata.json parity check failed"
    exit 1
  }
fi

echo "post-merge: OK"
