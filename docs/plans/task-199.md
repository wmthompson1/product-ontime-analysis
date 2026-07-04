---
title: Live read-only SPARQL endpoint
---
# Live Read-Only SPARQL Endpoint

## What & Why
The POC currently answers SPARQL only through one-shot CLI invocations inside the
parity script. The real interoperability payoff is letting an outside system (an
aerospace/enterprise consumer) issue standard SPARQL over HTTP against the
virtual graph. Run Ontop in its endpoint/server mode over a read-only snapshot,
document how to query it, and add a smoke test that boots the server, runs a
SPARQL query over HTTP, and confirms it returns the same governed number.

## Done looks like
- A single command starts a local SPARQL HTTP endpoint backed by the existing
  ontology + mapping over a read-only snapshot, on a configurable port.
- Documented example requests (e.g. curl) return the on-time rate and the
  supplier optional-delivery results over HTTP.
- An automated smoke test starts the endpoint, issues a SPARQL query over HTTP,
  asserts the on-time rate matches the governed number, and shuts the server down
  cleanly (no orphaned process) — exiting non-zero on failure.
- The endpoint is provably read-only (points at a snapshot, never the live DB)
  and is not wired into the running app.
- README gains a "live SPARQL endpoint" section and drops it from "Out of scope".

## Out of scope
- Authentication, TLS, deployment, or exposing the endpoint publicly.
- A materialized triplestore or OWL reasoning beyond Ontop's SQL-rewriting
  profile.
- Wiring the endpoint into the Flask/HF Space app or Gradio.

## Steps
1. **Endpoint launcher** — Add a script that ensures the toolchain, builds a
   read-only snapshot, and starts Ontop's SPARQL HTTP endpoint over it on a
   configurable port.
2. **Example queries** — Provide ready-to-run HTTP query examples for the on-time
   rate and the supplier optional-delivery view.
3. **HTTP smoke test** — Boot the endpoint, query it over HTTP, assert parity
   with the governed number, and tear it down reliably, exiting non-zero on
   failure.
4. **Docs** — Document startup, example requests, the read-only guarantee, and
   remove the endpoint from "Out of scope".

## Relevant files
- `replit_integrations/ontop_poc_setup.py`
- `replit_integrations/ontop_poc_run_demo.py`
- `poc/ontop-ontology-poc/parity_check.py:46-94`
- `poc/ontop-ontology-poc/mapping/on_time_delivery.properties`
- `poc/ontop-ontology-poc/README.md:139-171,199-210`