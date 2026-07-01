Here’s the crisp, *correct* explanation of the line you asked about:

```
?op a :Operation ;
```

This single line does **two** things at once in SPARQL, and understanding it is foundational for OBDA, Ontop, and the routing showcase.

---

# 🧩 1. `?op` is a **SPARQL variable**
It means:

> “Bind `?op` to every RDF subject in the graph that matches the following triple patterns.”

In your OBDA mapping, those subjects are the IRIs minted from the `operation` table:

```
:operation/{rowid_pk}
```

(from your `.obda` file)

So `?op` iterates over **each operation row**.

---

# 🧩 2. `a` is shorthand for `rdf:type`
SPARQL uses `a` as syntactic sugar:

```
?op a :Operation
```

is exactly the same as:

```
?op rdf:type :Operation
```

It means:

> “Return only those subjects that are typed as `:Operation`.”

Your OBDA mapping explicitly asserts this type:

```
target :operation/{rowid_pk} a :Operation ;
```

So Ontop generates triples like:

```
:operation/17 rdf:type :Operation .
:operation/18 rdf:type :Operation .
...
```

---

# 🧩 3. The semicolon (`;`) means “same subject, more predicates”
This is SPARQL’s compact syntax.

```
?op a :Operation ;
    :partOfWorkOrder ?wo ;
    :runHours ?hrs .
```

is equivalent to writing three separate triples:

```
?op a :Operation .
?op :partOfWorkOrder ?wo .
?op :runHours ?hrs .
```

The semicolon simply says:

> “Continue describing `?op` with additional predicates.”

---

# 🧩 4. Why this line is essential in Ontop OBDA

### It forces Ontop to:
- bind `?op` only to individuals created by the **operation mapping**
- avoid accidental inference from other mappings
- avoid domain‑based inference (your TTL warns against this)

TTL citation:

> “It is given a range only and NO rdfs:domain… an rdfs:domain on a link property makes Ontop infer the subject class… and emit invalid UNION/LEFT-JOIN SQL.”

By explicitly typing `?op a :Operation`, you ensure Ontop uses **only** the mapping:

```
mappingId map-routing-operation
target :operation/{rowid_pk} a :Operation ;
```

This keeps the SQL rewrite clean and predictable.

---

# 🧩 5. What SQL Ontop generates from this line

The triple pattern:

```
?op a :Operation
```

rewrites to:

```sql
SELECT o.rowid_pk AS op
FROM operation o
```

because your mapping says:

```
:operation/{rowid_pk} a :Operation
```

This is why the SPARQL query:

```sparql
SELECT ?wo (SUM(?hrs) AS ?totalRunHours)
WHERE {
  ?op a :Operation ;
      :partOfWorkOrder ?wo ;
      :runHours ?hrs .
}
GROUP BY ?wo
```

rewrites to the clean SQL:

```sql
SELECT o.wo_id, SUM(o.run_hrs)
FROM operation o
GROUP BY o.wo_id;
```

Exactly matching your grounding SQL.

---

# 🧩 Summary (the one‑liner)

**`?op a :Operation ;` means:  
“Bind `?op` to each operation row published as an RDF individual of class `:Operation`, and continue describing that same subject with additional predicates.”**

---

If you want, I can also show:

- how this line behaves under **Ontop’s SQL rewrite logs**,  
- how it interacts with **SPARQL optimizers**,  
- or how to teach LLMs to generate this pattern reliably (OBO Academy style).

Just tell me what direction you want to go.