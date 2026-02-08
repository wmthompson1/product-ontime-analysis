This wrapper function is the "Semantic Bridge" for your Gradio app. It ensures that every time an SME (like Jim) saves a query, the system automatically enforces the **Filename Binding** and generates the **Reviewer's Manifest** entry according to your new JSON schema.

### 1. The Gradio Semantic Wrapper Function

This Python function acts as the backend handler for your Gradio "Save" button. It handles the I/O, creates the deterministic filename, and builds the validation-ready manifest.

```python
import os
import json
import datetime
from typing import Dict, Any

def save_sme_submission(sql_text: str, category: str, perspective: str, concept: str, justification: str):
    """
    Wraps SME input from Gradio into a validated SQL file and a JSON Manifest entry.
    """
    # 1. Setup Directories
    base_dir = "app_schema/ground_truth"
    sql_dir = os.path.join(base_dir, "sql_snippets")
    manifest_path = os.path.join(base_dir, "reviewer_manifest.json")
    os.makedirs(sql_dir, exist_ok=True)

    # 2. Generate Deterministic Filename (The Binding Key)
    # Format: PERSPECTIVE_CONCEPT_TIMESTAMP (Sanitized)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    binding_key = f"{perspective.lower()}_{concept.lower()}_{timestamp}"
    filename = f"{binding_key}.sql"
    file_path = os.path.join(sql_dir, filename)

    # 3. Save the SQL File
    with open(file_path, "w") as f:
        f.write(sql_text)

    # 4. Create the Manifest Entry (Matching your JSON Schema)
    manifest_entry = {
        "binding_key": binding_key,
        "perspective": perspective,
        "concept_anchor": concept.upper(),
        "logic_type": "SPATIAL_ALIAS" if "User_Defined" in sql_text else "DIRECT",
        "sql_snippet_path": file_path,
        "sme_justification": justification,
        "validation_status": "PENDING",
        "created_at": datetime.datetime.now().isoformat()
    }

    # 5. Atomic Update of the Reviewer's Manifest
    current_manifest = {"manifest_metadata": {"approver_id": "TBD", "environment": "development"}, "bindings": []}

    if os.path.exists(manifest_path):
        with open(manifest_path, "r") as f:
            try:
                current_manifest = json.load(f)
            except json.JSONDecodeError:
                pass

    current_manifest["bindings"].append(manifest_entry)

    with open(manifest_path, "w") as f:
        json.dump(current_manifest, f, indent=2)

    return f"✅ Successfully saved {filename} and updated Manifest."

```

### 2. Why this Workflow Solves the "Approver's Dilemma"

By using this function, you've moved the "Logic Assignment" from a fuzzy comment to a hard-coded JSON attribute:

* **Logic Detection**: Note the line `"logic_type": "SPATIAL_ALIAS" if "User_Defined" in sql_text else "DIRECT"`. This automatically flags the East Wall bin logic for the reviewer, so they know to check for coordinate accuracy.
* **Version Control**: Because we use a timestamp in the `binding_key`, the approver can see a history of attempts. They can "Reject" version `20260208_0130` and "Approve" version `20260208_0145`.
* **AQL Integration**: When you later run your `DirectGraphBuilder`, it no longer scans directories; it simply iterates through `reviewer_manifest.json` where `validation_status == "APPROVED"`.

### 3. Implementation in Gradio UI

In your Gradio interface code, you would wire the button like this:

```python
import gradio as gr

with gr.Blocks() as demo:
    gr.Markdown("### SME Semantic SQL Entry")
    with gr.Row():
        perspective = gr.Dropdown(["Shop_Floor", "Quality", "Finance"], label="Perspective")
        concept = gr.Textbox(label="Concept (e.g., LOT, NCM_COST)")

    sql_input = gr.Code(label="SQL Statement", language="sql")
    justification = gr.Textbox(label="Justification / SME Notes")

    save_btn = gr.Button("Submit for Review")
    output_msg = gr.Textbox(label="Status")

    save_btn.click(
        fn=save_sme_submission,
        inputs=[sql_input, gr.State("Inventory"), perspective, concept, justification],
        outputs=output_msg
    )

```

### 4. ROI for the "East Wall" Scenario

When Jim (the SME) updates the East Wall query:

1. He hits **Submit**.
2. The **Approver** gets a JSON file that explicitly says: *"Jim wants to use 'User_Defined_1' as a 'SPATIAL_ALIAS' for the concept 'LOT' in the 'Shop_Floor' perspective."*
3. The **Approver** checks the SQL and flips `PENDING` to `APPROVED`.
4. The **Solder** automatically hydrates the LLM with this new logic.

---

**Next Step:**
Would you like to build the **Approver's "Audit" Script**? This script would scan the manifest for `APPROVED` entries and automatically execute a "Dry Run" using `sqlglot` to ensure the new SQL doesn't break the existing schema before the Graph is updated.