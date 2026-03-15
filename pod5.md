The move from `.github/agents/` to a dedicated `agents/` directory at the project root represents a shift from **documentation-based instructions** to **protocol-aware execution**. In an MCP (Model Context Protocol) framework, this isn't just a folder change; it’s a change in how the AI "handshakes" with your local environment.

---

### 1. Functional Role: Documentation vs. Execution

* **.github/agents/**: In your current setup, these act as high-level "System Prompts" or instruction sets for the GitHub Copilot SDK to understand the role of a specific agent (e.g., the Writer or the Orchestrator).
* **agents/** (Project Root): In the new setup, these files serve as **MCP Entity Definitions**. They are part of a modular system where the agent is explicitly tied to "Skills" (like your `masking_engine`) through the `copilot-config.yaml`.

### 2. The Skill Contract Solder

The primary difference is the **proximity to the Skill Contract** (`skill.json`):

* **Current Setup**: The agent reads an `.md` file and "knows" what to do, but it has to "guess" or be told the exact file paths and Python arguments for scripts like `mask_pii.py`.
* **MCP Setup**: The `intent-mapping-agent.md` in the root `agents/` folder is designed to call the `masking_engine_001` skill. Because they share the same root environment, the "contract" defines exactly which parameters (like `gemin_salt`) the agent is **required** to provide before the script can run.

### 3. Comparison Table: Solder vs. Instructions

| Feature | `.github/agents/` (Current) | `agents/` + `skills/` (MCP) |
| --- | --- | --- |
| **Primary Goal** | Define "Persona" and general intent. | Execute "Skills" via strict interface contracts. |
| **Logic Binding** | Loose; depends on the LLM finding the right script. | Tight; bound by the `skill.json` entry point. |
| **Env Awareness** | Remote; may struggle with relative paths in `.venv`. | Local; anchored to the project root and `.venv`. |
| **Validation** | Narrative-based; hard to verify before execution. | Schema-based; `skill.json` validates inputs automatically. |

---

### 4. Why this matters for Plan-001

By moving the agents to the project root, you are creating a **Unified Runtime Solder**. When the **Intent Mapping Agent** needs to apply the "Manufacturing Perspective," it doesn't just read about it; it invokes the `hierarchy_crawler` skill to fetch the **BFS path** and then passes that directly to the `masking_engine` skill.

**Would you like me to draft the "Handshake Logic" for the Orchestrator to show how it calls an agent from the new root folder instead of the .github folder?**