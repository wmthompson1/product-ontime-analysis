---
name: SQLGlot Select arg names
description: Non-obvious arg key names in SQLGlot's exp.Select — FROM clause, join side/kind split
---

When parsing SQL with SQLGlot and inspecting a `exp.Select` node's `.args` dict:

**FROM clause key is `"from_"` not `"from"`**
```python
from_clause = select.args.get("from_")  # CORRECT
from_clause = select.args.get("from")   # always returns None — Python reserved word
```

**JOIN type is split across two args: `"side"` and `"kind"`**
- `"side"` → "LEFT", "RIGHT", or None
- `"kind"` → "CROSS", "FULL", or None
- Plain INNER JOIN: both are None

Canonical join type string:
```python
side = (join.args.get("side") or "").upper()
kind = (join.args.get("kind") or "").upper()
join_type = " ".join(filter(None, [side, kind])) or "INNER"
# LEFT JOIN  → "LEFT"
# CROSS JOIN → "CROSS"
# INNER JOIN → "INNER"
# LEFT OUTER → "LEFT OUTER" (if dialect uses it)
```

**Why:** `from` is a Python reserved keyword so SQLGlot can't use it as a Python attribute name; `side` vs `kind` is SQLGlot's internal grammar distinction between join directionality and join modality.

**How to apply:** Any code that walks SQLGlot SELECT nodes for FROM/JOIN extraction must use these keys. `find_all(exp.Join)` still works for locating joins in the AST — the issue is only when reading the args on the Select node directly.
