# CI workflow for the Ontop POC

## What & Why
The Ontop interoperability checks — the parity checks, the supplier-rating proof,
and the live SPARQL HTTP endpoint smoke test — are all standalone today, deliberately
left out of `scripts/post-merge.sh` because they need a JVM + the Ontop toolchain.
That means interoperability guarantees can silently regress. Add a dedicated CI
workflow that provisions the toolchain and runs these checks automatically, with
failure alerting consistent with the project's existing pattern, so the virtual
graph stays trustworthy.

## Done looks like
- A GitHub Actions workflow installs Java + the pinned Ontop toolchain and runs
  the POC parity checks and the SPARQL HTTP endpoint smoke test end-to-end,
  failing the run on any mismatch or orphaned process.
- The workflow runs on changes under the POC directory and on a schedule (nightly),
  consistent with the existing smoke/drift workflows.
- On failure it posts a Slack alert reusing the established alert pattern, gated on
  the existing alert webhook secret (skipped silently when the secret is absent).
- The offline mapping drift guard stays in `post-merge.sh`; only the JVM-dependent
  checks move into this workflow.
- README notes that the POC is now covered by CI.

## Out of scope
- Moving the JVM-dependent checks into `scripts/post-merge.sh` (they stay separate).
- New parity logic — this only schedules and runs the existing checks.
- Exposing the endpoint publicly, auth, or TLS.

## Steps
1. **Workflow** — Add a CI workflow that sets up Java + the Ontop toolchain and
   runs the parity checks and the endpoint HTTP smoke test, on POC-path changes and
   nightly.
2. **Alerting** — Post a Slack alert on failure using the existing webhook secret
   and Block Kit pattern, skipping silently when unset.
3. **Docs** — Document the new CI coverage in the POC README.

## Relevant files
- `poc/ontop-ontology-poc/parity_check.py`
- `poc/ontop-ontology-poc/rating_parity_check.py`
- `poc/ontop-ontology-poc/endpoint_smoke_test.py`
- `replit_integrations/ontop_poc_setup.py`
- `.github/workflows/graph-sync-on-change.yml`
- `.github/workflows/arango-legacy-smoke.yml`
- `.github/workflows/drift-alert.yml`
- `poc/ontop-ontology-poc/README.md:296-310`
