Partly — but let me correct the specific mechanism, because there are two different paths in the POC and they work differently.

The parity checks (the actual proofs for all 6 showcases, including the 3 I just built): no HTTP endpoint.
Python drives the Ontop command-line tool via subprocess, not an HTTP SPARQL endpoint and not a Python SPARQL client library (no SPARQLWrapper/rdflib-remote). The flow in run_sparql() is:

```
ontop query --properties <snapshot.properties> -q <query.rq>   ← run as a subprocess
```

Ontop reads the .rq file, rewrites the SPARQL into SQL against the read-only SQLite snapshot, and returns CSV on stdout. Python parses that CSV and compares it to the same number computed by direct governed SQL (sqlite3 on the identical snapshot). So Python is orchestrating Ontop's CLI query mode and diffing CSVs — there's no server/endpoint involved in this path. All three new checks (capacity_planning_, shop_floor_routing_, inventory_transactions_parity_check.py) reuse that same run_sparql CLI helper.

There is a separate, standalone piece where your description is exactly right.
sparql_endpoint.py boots Ontop in endpoint (server) mode — a real HTTP SPARQL endpoint at http://127.0.0.1:<port>/sparql — and endpoint_smoke_test.py then POSTs SPARQL queries over HTTP (via Python's urllib, form param query, Accept: text/csv) and checks the answers. That's the "an outside system could consume this over standard SPARQL/HTTP" proof.

But that endpoint path is not what the merged showcase parity checks use — it's a separate, manual/CI-only demonstration. The 6 governed-domain parity proofs all go through the CLI subprocess route.

So: yes, Python programmatically issues SPARQL to Ontop in both cases — but the headline parity proofs use the Ontop CLI (subprocess → CSV), and only the optional smoke test actually hits an HTTP SPARQL endpoint. Want me to point you at the exact lines, or walk through either path in more detail?

## Resources
