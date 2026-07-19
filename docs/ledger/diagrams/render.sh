#!/usr/bin/env bash
# Deterministically re-render the committed ledger diagrams from their
# Graphviz sources. Run from anywhere; requires graphviz (dot).
set -euo pipefail
cd "$(dirname "$0")"
for f in ledger_ontology job_costing_flow; do
    dot -Tsvg "${f}.dot" -o "${f}.svg"
    echo "rendered ${f}.svg"
done
