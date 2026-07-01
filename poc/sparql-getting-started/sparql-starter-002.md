Now it's clear. You're looking at a markdown note, not code — so "empty" is expected.

poc/sparql-getting-started/sparql-starter-001.md is a plain doc. Its contents are actually a saved copy of my previous chat answer (lines 1–17), followed by an empty ## Resources heading at the bottom. It mentions run_sparql() in prose but contains no function — there's nothing to be empty, because there's no code there in the first place.

The real run_sparql() lives in poc/ontop-ontology-poc/parity_check.py (line 81), with five sibling copies in the other *_parity_check.py files. It is not empty — here's the actual body:

def run_sparql(props, query_file, out_csv):
    cmd = [
        ONTOP, "query",
        "-m", MAPPING,       # the OWL ontology's .obda mapping
        "-t", ONTOLOGY,      # the .ttl ontology
        "-p", props,         # JDBC props pointing at the read-only snapshot
        "-q", query_file,    # the .rq SPARQL query
        "-o", out_csv,       # where Ontop writes the CSV result
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=POC_DIR)
    if res.returncode != 0:
        sys.stderr.write(res.stdout + "\n" + res.stderr + "\n")
        raise SystemExit(f"ontop query failed for {os.path.basename(query_file)}")
    return out_csv

So it assembles an ontop query … command, runs it as a subprocess, fails loudly on a non-zero exit, and returns the path to the CSV Ontop produced. The companion read_first_column() (line 97) then parses the scalar answer out of that CSV (stripping any ^^<datatype> suffix) so it can be compared to the direct-SQL number.

Quick orientation:

Learning notes → poc/sparql-getting-started/ (currently just the one .md).
Runnable code → poc/ontop-ontology-poc/ (parity_check.py + the six *_parity_check.py, plus sparql_endpoint.py for the HTTP-endpoint variant).
Would you like me to flesh out that starter doc into a proper hands-on guide — e.g. a minimal, runnable "your first SPARQL query" walkthrough pointing at the real run_sparql() and one .rq file — or leave your notes as they are?