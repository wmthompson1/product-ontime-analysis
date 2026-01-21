Your CI job failed because the SQLMesh workflow encountered repeated errors related to your table partition/time configuration. Every reference in your logs to
```
time_column ("...date...", '%Y-%m-%d'),
partition_by_time_column TRUE,
...
on_destructive_change 'ERROR',
on_additive_change 'ALLOW'
```
immediately triggered an `--- ERROR ---` during SQLMesh compilation/apply. This repeats for every table.

## Solution

1. **Check Partition Column Validity**
   - Ensure each `time_column` you specify actually exists in the underlying table/query.
   - If any of `"target_date"`, `"delivery_date"`, `"event_start_time"`, etc. are missing or misnamed, SQLMesh will throw this error.

2. **Validate Date Formatting**
   - Make sure all date columns use the format `'%Y-%m-%d'`. If the columns store timestamps or different formats, convert/cast them in your model SQL.

3. **Configuration Syntax**
   - Confirm your model or manifest files use the correct SQLMesh configuration syntax for partitioning.

### Example Fixes

**Check your model definition**
```sql
MODEL (
  ...
  time_column ("target_date", '%Y-%m-%d'), -- make sure 'target_date' exists and has the correct format
  partition_by_time_column TRUE,
  ...
)
SELECT
  CAST(event_date AS DATE) AS target_date, -- or use correct column/logic
  ...
FROM ...
```
**1. If a column is missing:**  
Update your SELECT with the correct column, or rename/match it.

**2. If a column’s datatype isn’t DATE:**  
Add a `CAST` inside your SELECT.

**3. If the error persists on multiple models:**  
Review all affected model files for typos and column presence.

---

### Next Steps

- Review the workflow file: [.github/workflows/sqlmesh.yml](https://github.com/wmthompson1/product-ontime-analysis/blob/cbeaff57f284db1d04133ad2259abdea562a3e3f/.github/workflows/sqlmesh.yml)
- Review each model’s time partition setup for missing or incorrect columns.
- If needed, provide one affected model file and column list, so I can offer a specific code correction.

Would you like direct pointers to the model files or SQLMesh configuration where this error occurred?