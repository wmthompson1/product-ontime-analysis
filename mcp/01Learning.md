```list type="issue"
data:
- url: "https://github.com/wmthompson1/product-ontime-analysis/issues/3"
  state: "closed"
  draft: false
  title: "✨ Set up Copilot instructions"
  number: 3
  created_at: "23 minutes"
  closed_at: "21 minutes"
  merged_at: ""
  labels: []
  author: "wmthompson1"
  comments: 0
  assignees_avatar_urls:
  - "https://avatars.githubusercontent.com/in/1143301?v=4"
```

I listed the repository’s closed issues for wmthompson1/product-ontime-analysis and found one closed issue (shown above): a short onboarding/CoPilot setup item you created and then completed.

Next, I sketched a learning outline you can use to prepare as a data analyst who needs to present SQL results to management (hypothetical). This is focused on practical SQL skills, data storytelling, reproducibility, and artifacts that management cares about.

Learning plan: SQL for a data analyst preparing deliverables for management
- Goal
  - Be able to extract, transform, analyze, and present data-driven recommendations using SQL and lightweight reporting tools; produce clear dashboards and an executive summary for non-technical stakeholders.

- Target audience & duration
  - Audience: early-to-mid level data analysts familiar with spreadsheets; want hands-on SQL and reporting practice.
  - Suggested duration: 4–8 weeks (4-week intensive or 8-week part-time).

- Weekly/modules (example 6-module, 6-week schedule)
  1. Foundations & data literacy (Week 1)
     - Objectives: Understand relational data, keys, normalization, simple SELECTs.
     - Topics/exercises: SELECT, WHERE, ORDER BY, basic filtering; practice on a sample orders table.
     - Deliverable: Short query set answering 5 business questions (counts, top N).
  2. Aggregation & grouping (Week 2)
     - Objectives: GROUP BY, HAVING, aggregates, date bucketing.
     - Topics/exercises: Monthly revenue, growth %, cohort counts.
     - Deliverable: Table and one chart (CSV) showing trend of key metric.
  3. Joining data & data modeling (Week 3)
     - Objectives: INNER/LEFT/RIGHT joins, deduping, basic schema thinking.
     - Topics/exercises: Join orders, customers, products to compute CLTV or defect rates.
     - Deliverable: Reproducible multi-table query with explanations.
  4. Advanced SQL (Week 4)
     - Objectives: Window functions, CTEs, subqueries, conditional logic.
     - Topics/exercises: Rolling averages, rank/top-N per group, running totals.
     - Deliverable: Query suite producing business insights (with comments).
  5. Performance, ETL basics & production thinking (Week 5)
     - Objectives: Index basics, explain plan, avoid anti-patterns, introduce ETL pipelines.
     - Topics/exercises: Optimize a slow query, create a simple ETL SQL script (staging -> marts).
     - Deliverable: Optimized query and short write-up of changes and trade-offs.
  6. Reporting, storytelling & delivery (Week 6)
     - Objectives: Build executive summary, visualizations, interpret results for management.
     - Topics/exercises: Dashboard in a BI tool (or CSV->Google Sheets), concise one-page memo, recommended actions.
     - Deliverable: Executive summary (1 page), 2 visuals, SQL scripts that generated numbers.

- Capstone project (end of course)
  - Project: From raw sample dataset (orders, shipments, returns), produce:
    - A set of reproducible SQL scripts (staging and final queries).
    - A short executive summary with 3 key insights and recommended actions.
    - A simple dashboard or set of charts (CSV + screenshots or link).
  - Grading criteria: correctness, reproducibility (can run queries in order), clarity of explanation, business relevance.

- Exercises & practice sources
  - Interactive: Mode SQL Tutorial, SQLBolt, SQLZoo.
  - Problem sets: LeetCode Database, HackerRank SQL.
  - Reference: PostgreSQL docs, BigQuery docs (if using cloud).
  - Visualization: Looker Studio / Tableau / Metabase / simple Excel/Sheets.

- Reproducibility & repo practices (ties to GitHub)
  - Organize repo:
    - /sql/01-staging.sql, /sql/02-marts.sql, /notebooks/ (if any), /reports/executive-summary.md
    - Add README with run-order and sample data instructions.
  - Use issue tracker to break modules into tasks (I can create those if you want).
  - Use small PRs for each module/exercise; keep queries commented and include expected output samples.
  - Add an ISSUE_TEMPLATE for exercise submissions and a CONTRIBUTING.md explaining how to submit solutions.

- Suggested artifacts for management
  - One-page executive summary: headline, 3 findings, recommended actions, impact estimate.
  - Top-line dashboard: 3–5 KPIs + trend sparkline.
  - SQL scripts + data dictionary (table/column descriptions).
  - Short README with “how to run” and data assumptions.

What I can do next for you (pick one or more)
- Flesh out any module into a lesson plan with specific exercises and sample datasets.
- Create repository issues for each module (so you can track learning progress).
- Generate starter files: README, folder structure, and a sample SQL query or capstone template in this repo.
- Build the executive-summary template and a sample query that produces metrics from a toy dataset.
- Or simply refine the 4–8 week timeline to match how much time you want to spend.

Tell me which action you want next and I’ll proceed (for example: “Create issues for the 6-week modules in the repo” or “Expand Week 4 with 5 concrete exercises and solutions”).
