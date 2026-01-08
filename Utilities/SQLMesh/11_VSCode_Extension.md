# 11 - SQLMesh VS Code Extension

## Overview

The SQLMesh VS Code extension provides IDE features for SQLMesh projects:
- Column-level lineage visualization
- Auto-completion and IntelliSense
- Go to definition
- Model rendering and preview
- Integrated command palette

## Links

| Resource | URL |
|----------|-----|
| **GitHub Repository** | https://github.com/TobikoData/sqlmesh |
| **VS Code Marketplace** | https://marketplace.visualstudio.com/items?itemName=tobikodata.sqlmesh |
| **Official Documentation** | https://sqlmesh.readthedocs.io/en/stable/guides/vscode/ |
| **Issue Tracker** | https://github.com/TobikoData/sqlmesh/issues |

## Installation

### Step 1: Install LSP Support

```bash
pip install 'sqlmesh[lsp]'
```

### Step 2: Install VS Code Extension

1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X)
3. Search for "SQLMesh" by TobikoData
4. Click Install

### Step 3: Configure Python Interpreter

1. Open Command Palette (Ctrl+Shift+P)
2. Select "Python: Select Interpreter"
3. Choose the environment with `sqlmesh[lsp]` installed

## Key Features

### Column-Level Lineage

Interactive graph showing data flow:

1. Open any model file
2. Click "Lineage" tab at bottom panel
3. Hover over columns to see upstream/downstream
4. Click columns to expand lineage

### Model Rendering

Preview resolved SQL:

1. Open a model file
2. Click "Rendered Query" tab
3. See macros and Jinja resolved

### Auto-Completion

IntelliSense for:
- Model names (with descriptions)
- Column names (from upstream models)
- SQL keywords
- Macro functions

### Go to Definition

- Ctrl+Click on model name → Jump to model file
- Ctrl+Click on column → Jump to definition

### Hover Tooltips

Hover over:
- Model names → See description, owner, tags
- Columns → See column documentation
- Macros → See function signature

### Command Palette

Ctrl+Shift+P → "SQLMesh:" commands:
- SQLMesh: Plan
- SQLMesh: Run
- SQLMesh: Test
- SQLMesh: Audit
- SQLMesh: Render Model

## Configuration

### settings.json

```json
{
  "sqlmesh.pythonPath": "${workspaceFolder}/.venv/bin/python",
  "sqlmesh.projectPath": "${workspaceFolder}",
  "sqlmesh.defaultDialect": "duckdb"
}
```

### Multi-Root Workspaces

For monorepos with multiple SQLMesh projects:

```json
{
  "folders": [
    {"path": "project-a"},
    {"path": "project-b"}
  ],
  "settings": {
    "sqlmesh.projectPath": "${workspaceFolder}"
  }
}
```

## Usage Workflow

### 1. Open Project

```bash
code Utilities/SQLMesh
```

### 2. Explore Models

- Navigate to `models/` directory
- Open any `.sql` file
- Extension activates automatically

### 3. View Lineage

- Click "Lineage" tab at bottom
- Interactive column-level graph
- Click nodes to expand

### 4. Edit with IntelliSense

- Type model names → Auto-complete
- Type column names → Suggestions from upstream
- Hover for documentation

### 5. Run Commands

- Ctrl+Shift+P → "SQLMesh: Plan"
- Or use integrated terminal

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Go to Definition | Ctrl+Click / F12 |
| Find References | Shift+F12 |
| Peek Definition | Alt+F12 |
| Command Palette | Ctrl+Shift+P |
| Quick Fix | Ctrl+. |

## Troubleshooting

### Extension Not Activating

1. Check Python interpreter is set correctly
2. Verify `sqlmesh[lsp]` is installed
3. Restart VS Code

### Lineage Not Showing

1. Run `sqlmesh plan` once to build state
2. Check for syntax errors in models
3. Verify config.yaml is valid

### Slow Performance

1. Large projects may take time to index
2. Check Python interpreter path
3. Restart language server

### Language Server Errors

```bash
# Reinstall LSP support
pip uninstall sqlmesh
pip install 'sqlmesh[lsp]'
```

## Alternative: SQLMesh UI Extension

Community extension embedding full web UI:

- **Marketplace**: https://marketplace.visualstudio.com/items?itemName=WesleyBatista.sqlmeshui
- Embeds the web UI directly in VS Code
- Useful for those who prefer the web interface

## Best Practices

1. **Install LSP first**: Extension needs language server
2. **Keep sqlmesh updated**: `pip install --upgrade sqlmesh[lsp]`
3. **Use virtual environments**: Isolate project dependencies
4. **Configure settings**: Set Python path explicitly
5. **Report issues**: Help improve the extension on GitHub

## Status

- **License**: Apache 2.0 (open source)
- **Maintainer**: TobikoData
- **Status**: Actively maintained
- **Contributions**: Welcome via GitHub PRs

## Resources

| Resource | Description |
|----------|-------------|
| [GitHub Issues](https://github.com/TobikoData/sqlmesh/issues) | Report bugs, request features |
| [Slack Community](https://tobikodata.com/slack) | Get help from community |
| [Documentation](https://sqlmesh.readthedocs.io/) | Official docs |
| [Blog](https://tobikodata.com/blog) | Tutorials and updates |
