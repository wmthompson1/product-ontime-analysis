# Quick Start: Using the Repo with our Copilot-style Agent

Link to agent docs / installer
- Company agent hub: [https://github.com/copilot]  <!-- Replace this with your company equivalent of https://github.com/copilot -->

One‑line summary
- Use Ask/Chat for quick explanations and examples. Use Agents for multi‑step repo tasks (scans, edits, tests, PRs). Start read‑only and escalate permissions only after reviewing the plan and diffs.

Before you start
- Have a GitHub account (or company SSO) and access to this repo (or fork).
- Install VS Code and the company Copilot/Agent extension and sign in.
- Open this repo in VS Code.

3-step starter checklist (safe)
1. Ask/Chat: Open a file with SQL, highlight a query, and ask:  
   "Explain this SQL and point out any unsafe string concatenation or SELECT * usage."
2. Read‑only agent: Run an agent with goal:  
   "Find SQL usage across the repo and list files/lines with SELECT * or string concatenation."  
   - Grant read-only permissions first.
   - Review the CSV/log it produces.
3. Scoped change (feature branch): If you want fixes applied, run an agent with a goal like:  
   "Create a feature branch that replaces string-concatenated SQL with parameterized queries in /src, add unit tests, run tests, and open a draft PR."  
   - Require the agent to show a plan and diffs before granting write/PR permissions.

Example prompts (copy/paste)
- Ask mode: "In file src/db/query.sql, explain each SELECT and propose a parameterized version."
- Agent (read-only): "Scan repo and output CSV: filename, line, snippet, and mark SELECT * or concatenated SQL."
- Agent (write-enabled): "Create a branch that replaces concatenated SQL in /src/db with parameterized queries, add tests, run them, and open a draft PR. Show plan and diffs before making commits."

Permissions & safety notes
- Start agents read-only. Only grant file-write, run-tests, or push/PR permissions after reviewing the agent’s plan.
- Require feature branches and enforce branch protections for main.
- Never store secrets in the repo; limit agent scopes and audit run logs periodically.

Who to contact
- Repo owner / maintainer: [REPO_OWNER_NAME] ([email or Slack])
- Security/DevOps: [SEC_TEAM_CONTACT]

Replace placeholders
- Replace [COMPANY_COPILOT_URL], [REPO_OWNER_NAME], and [SEC_TEAM_CONTACT] with your company links/contacts before sharing.

Quick copyable email snippet
- "Hi — to try our Copilot agent with this repo: install the company agent from [COMPANY_COPILOT_URL], open the repo in VS Code, and run the read-only agent 'Scan repo for SQL patterns'. Ping [REPO_OWNER_NAME] if you need access."
