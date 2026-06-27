#!/usr/bin/env python3
"""
Ontop POC one-command demo (Python port of poc/ontop-ontology-poc/run_demo.sh).
=============================================================================

Proves the virtual SPARQL graph matches the SQL semantic layer:

  1. Ensures the toolchain is present (idempotent download via
     :func:`ontop_poc_setup.ensure_toolchain`).
  2. Runs ``poc/ontop-ontology-poc/parity_check.py`` and propagates its exit
     code (0 on parity, non-zero on mismatch/error).

Lives in ``replit_integrations/`` so it can be shared with the other integration
tools, but it points back into the POC folder. Run it directly
(``python3 replit_integrations/ontop_poc_run_demo.py``) or via
``python3 -m replit_integrations.ontop_poc_run_demo``.
"""
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import ontop_poc_setup  # noqa: E402

PARITY_CHECK = os.path.join(ontop_poc_setup.POC_DIR, "parity_check.py")


def main():
    ontop_poc_setup.ensure_toolchain()
    res = subprocess.run([sys.executable, PARITY_CHECK])
    return res.returncode


if __name__ == "__main__":
    sys.exit(main())
