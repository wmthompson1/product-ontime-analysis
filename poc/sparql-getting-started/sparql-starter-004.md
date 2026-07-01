Done. I rewrote poc/sparql-getting-started/sparql-starter-001.md into a proper hands-on guide, and every command and number in it is empirically verified (not just described):

The live query runs: the exact ontop query … command pointed at routing_total_run_hours.rq returns totalRunHours,operations = 669.55,502 (read-only, ~13s including JVM boot).
The parity claim holds: the governed SQL (sqlite3 -readonly … and a Python mode=ro equivalent) both return the identical 669.55, 502.
The sibling exercise is correct: WO-240003 = 6 routing steps, as the guide states.
What the guide covers, in teaching order:

The one big idea (Ontop rewrites SPARQL → SQL over SQLite; no data copied).
The four ingredients (.ttl ontology, .obda mapping, .properties, .rq query) with the real routing files.
A line-by-line read of the actual query (triple pattern, variables, SUM/COUNT).
One-time toolchain setup + the exact runnable command (flags mapped to ingredients), the real output, and an explanation that the OWL-2-QL / foreign-key / primary-key warnings are benign.
A "prove it" step showing SPARQL == governed SQL.
How run_sparql() and the automated parity check wrap the same command (with the CLI-not-HTTP clarification from our earlier discussion).
**Three try-it-yourself exercises**, including the /-in-IRI angle-bracket gotcha.
A read-only safety note so they can experiment freely.
I skipped a formal code review since this is a documentation file with no code logic, and instead verified correctness by actually running every command. The guide is self-contained and copy-pasteable from the repo root.

(Unrelated: the mockup-sandbox preview workflow is still showing as failed — same separate issue as before, untouched by this work. Say the word if you'd like me to look at it.)