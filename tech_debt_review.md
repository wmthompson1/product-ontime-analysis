tech debt review  
docs/tech\_debt\_review

FKs  
replit prompt  
*we had table relationships in the updated contextual hints demo. Could you review in 2-3 pages and recommend which files to highlight in the repo for Copilot? I need this for tech debt review.*

Here's your **Tech Debt Review Summary** for Copilot:

---

Files to Highlight for Tech Debt Review  
Priority 1: Core Schema Metadata

| File | Purpose | Tech Debt Issue |
| ----- | ----- | ----- |
| app/database\_hints\_loader.py | Loads FK relationships from schema\_edges | Uses psycopg2 (PostgreSQL) but HF Space uses SQLite |
| app/contextual\_hints.py | Hint engine with hardcoded acronyms | 7 acronyms hardcoded \- should migrate to manufacturing\_acronyms table |

Priority 2: Schema DDL

| File | Purpose | Tech Debt Issue |
| ----- | ----- | ----- |
| schema/schema\_sqlite.sql | SQLite schema (20 tables) | 4 tables missing from PostgreSQL migration |
| schema/schema.sql | Original PostgreSQL (24 tables) | Source of truth |

Priority 3: Database Tables Needing Work

| Table | Current State | Needed |
| ----- | ----- | ----- |
| schema\_edges | 7 relationships | More FKs for 20 tables |
| schema\_nodes | Empty | Table descriptions |
| manufacturing\_acronyms | Empty | Populate with NCM, OTD, OEE, etc. |

---

Current FK Relationships (7 total)

equipment → product (part\_id)

product → supplier (supplier\_id)

equipment → production\_line (line\_id)

equipment → maintenance\_log (equipment\_id)

production\_line → quality\_control (line\_id)

product → quality\_control (product\_id)

equipment → quality\_control (equipment\_id)

---

Action Items

1. **Add candidate keys** \- Document PKs beyond id columns  
2. **Expand FK coverage** \- More relationships for 20 tables  
3. **Populate schema\_nodes** \- Add table descriptions  
4. **Migrate acronyms** \- Move hardcoded to database  
5. **Unify database layer** \- SQLite support for hints loader

Want me to continue with any specific item, or shall I clear context now?

^^\*\*  
