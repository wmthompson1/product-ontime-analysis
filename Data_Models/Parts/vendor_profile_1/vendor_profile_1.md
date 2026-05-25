I’m comparing the slow query to the fast part profile and checking the join and aggregation shape first, so I can point to the likely cost drivers before suggesting a rewrite.

Read memory

Read [](file:///c%3A/Users/williamt/source/skillsinc/skills-inc-org/SQL-Projects/Documentation/Schema/Data_Models/Parts/Part_Profile_2.sql)

Read skill [sql-optimization](file:///c%3A/Users/williamt/source/skillsinc/skills-inc-org/SQL-Projects/.agents/skills/sql-optimization/SKILL.md?vscodeLinkType%3Dskill#1-1), lines 1 to 260

Starting: *Read candidate SQL files for pivot query* (4/5)

I’ve got the main shape difference. I’m pulling exact anchor lines for the expensive parts so I can give you a precise review and a concrete rewrite direction.

Searched for regex `CTE_PO AS|CTE_VENDOR AS|CTE_USER_DEF_FIELDS_VMPRTMNT AS|CTE_USER_DEF_FIELDS AS|STRING_SPLIT|row_number\(|x\.\*|FROM Live\.dbo\.USER_DEF_FIELDS|FROM USER_DEF_FIELDS|LEFT OUTER JOIN CTE_USER_DEF_FIELDS|LEFT JOIN CTE_USER_DEF_FIELDS_VMPRTMNT` (`**/Documentation/Schema/Data_Models/Parts/vendor_profile_1.sql`), 11 results

Searched for regex `CTE_PART AS|CTE_USER_DEF_FIELDS AS|STRING_SPLIT|FROM USER_DEF_FIELDS|LEFT OUTER JOIN CTE_USER_DEF_FIELDS` (`**/Documentation/Schema/Data_Models/Parts/Part_Profile_2.sql`), no results

I’ve got the slow-query anchors. I’m adding exact anchors from the fast query now so the comparison is clean and not hand-wavy.

Searched for regex `WITH CTE_PART AS|CTE_USER_DEF_FIELDS AS|STRING_SPLIT\(@cc_in, ','\)|FROM USER_DEF_FIELDS|LEFT OUTER JOIN CTE_USER_DEF_FIELDS UDF` (`SQL-Projects` · `Documentation/Schema/Data_Models/Parts/Part_Profile_2.sql`), 6 results

Read [](file:///c%3A/Users/williamt/source/skillsinc/skills-inc-org/SQL-Projects/Documentation/Schema/Data_Models/Parts/vendor_profile_1.sql#30-30), lines 30 to 150

I’ve isolated the structural difference. I’m checking whether the schema has supporting indexes for the exact filters and joins, because that determines whether a temp-table rewrite is actually necessary.

Searched for regex `CREATE TABLE \[dbo\]\.\[USER_DEF_FIELDS\]|CREATE NONCLUSTERED INDEX|PROGRAM_ID|DOCUMENT_ID|ID\]` (`**/Utilities/SQLMesh/ddl/dbo.USER_DEF_FIELDS.sql`), no results

Searched for files matching `**/Utilities/SQLMesh/ddl/dbo.PURC_ORDER_LINE.sql`, no matches

Searched for files matching `**/Utilities/SQLMesh/ddl/dbo.PURCHASE_ORDER.sql`, no matches

Searched for files matching `**/Utilities/SQLMesh/ddl/dbo.PART.sql`, no matches

The first DDL lookup hit workspace filters, so I’m locating the actual DDL files directly before I make any indexing 

Starting: *Review vendor_profile_1.sql for performance issues* (5/6)

claims.

Read [](file:///c%3A/Users/williamt/source/skillsinc/skills-inc-org/SQL-Projects/Utilities/SQLMesh/ddl)

Read [](file:///c%3A/Users/williamt/source/skillsinc/skills-inc-org/SQL-Projects/Utilities/SQLMesh)

I found the DDL files. I’m reading the relevant table definitions now so I can tie the slowdown to specific join/index pressure instead of just the SQL shape.

Read [](file:///c%3A/Users/williamt/source/skillsinc/skills-inc-org/SQL-Projects/Utilities/SQLMesh/ddl/dbo.USER_DEF_FIELDS.sql)

Read [](file:///c%3A/Users/williamt/source/skillsinc/skills-inc-org/SQL-Projects/Utilities/SQLMesh/ddl/dbo.PURCHASE_ORDER.sql)

Read [](file:///c%3A/Users/williamt/source/skillsinc/skills-inc-org/SQL-Projects/Utilities/SQLMesh/ddl/dbo.PURC_ORDER_LINE.sql)

Read [](file:///c%3A/Users/williamt/source/skillsinc/skills-inc-org/SQL-Projects/Utilities/SQLMesh/ddl/dbo.PART.sql)

**Findings**

1. High: the query aggregates the entire USER_DEF_FIELDS table twice before it knows which parts or vendors are relevant. In vendor_profile_1.sql, `CTE_USER_DEF_FIELDS_VMPRTMNT` groups all `VMPRTMNT` rows by `DOCUMENT_ID`, and in vendor_profile_1.sql, `CTE_USER_DEF_FIELDS` does a second full aggregation for `VMVNDMNT`. That is the main reason this is slower than Part_Profile_2.sql, which only performs one UDF aggregation and stays on the part domain.

2. High: the working set is much larger than it looks because the query starts from purchase orders and lines, not from a small scoped part set. The expansion begins in vendor_profile_1.sql, where `PURCHASE_ORDER`, `PURC_ORDER_LINE`, and `PART` are joined before any vendor or UDF reduction happens. If `@PART_ID` and `@PURC_ORD_ID` are `NULL`, this becomes “all PO lines for selected commodity codes,” which is a much broader slice than the fast part-profile query.

3. Medium: `CTE_VENDOR` is redundant and causes another pass over the PO-derived set. In vendor_profile_1.sql, `CTE_VENDOR` just derives vendor IDs from `CTE_PO`, and then the final query rejoins that to `VENDOR` in vendor_profile_1.sql. That extra hop does not add selectivity; it only adds work.

4. Medium: the nullable filter pattern weakens plan quality. In vendor_profile_1.sql and vendor_profile_1.sql, predicates like `column = @param OR @param IS NULL` are convenient but not optimizer-friendly. They are especially expensive here because the query already spans large purchasing tables.

5. Low: the final projection and windowing add avoidable cost after the rowset is already large. `ROW_NUMBER()` in vendor_profile_1.sql forces a partitioned sort, and `x.*` in vendor_profile_1.sql widens the row unnecessarily. These are not the root cause, but they compound the slowdown.

**Why Part_Profile_2 is fast**

Part_Profile_2.sql scopes the problem to parts first, then performs one UDF pivot in Part_Profile_2.sql, and finally joins that result once in Part_Profile_2.sql. The slow query is doing both part-UDF and vendor-UDF pivots over broader purchasing data, so its cardinality and aggregation cost are fundamentally higher.

**Recommendation**

A temp-table approach is justified here. The right shape is:

1. Materialize the filtered PO/line/part scope first into `#po_scope`.
2. Add indexes on `#po_scope` for `PART_ID`, `VENDOR_ID`, and optionally `(PURC_ORD_ID, PO_LINE_NO)`.
3. Build `#part_scope` and `#vendor_scope` as distinct IDs from `#po_scope`.
4. Aggregate `USER_DEF_FIELDS` only for those scoped IDs:
   - join `USER_DEF_FIELDS` to `#part_scope` for `PROGRAM_ID = 'VMPRTMNT'`
   - join `USER_DEF_FIELDS` to `#vendor_scope` for `PROGRAM_ID = 'VMVNDMNT'`
5. Join those smaller aggregated results back to `#po_scope`.
6. Remove `CTE_VENDOR` and join `VENDOR` directly from `#po_scope`.

That changes the cost from “scan and group all matching UDF rows in the database” to “scan and group only UDF rows for the parts and vendors already proven relevant.”

I did not run an execution plan against SQL Server, so this is based on query shape plus the extracted DDL. In the DDL I checked, dbo.USER_DEF_FIELDS.sql shows the table structure but no visible supporting secondary indexes in the extract, which makes the two broad aggregations even more suspicious.

If you want, I can rewrite vendor_profile_1.sql into the temp-table version now.

Completed: *Review vendor_profile_1.sql for performance issues* (5/6)