# SQLMesh VS Code Extension

## Overview
The SQLMesh VS Code extension provides IDE features for SQLMesh projects including column-level lineage visualization, auto-completion, and model rendering.

## Links

| Resource | URL |
|----------|-----|
| **GitHub Repository** | https://github.com/TobikoData/sqlmesh |
| **VS Code Marketplace** | https://marketplace.visualstudio.com/items?itemName=tobikodata.sqlmesh |
| **Official Documentation** | https://sqlmesh.readthedocs.io/en/stable/guides/vscode/ |
| **Issue Tracker** | https://github.com/TobikoData/sqlmesh/issues |

## Installation

### 1. Install LSP Support
```bash
pip install 'sqlmesh[lsp]'
```

### 2. Install VS Code Extension
1. Open VS Code Extensions (Ctrl+Shift+X)
2. Search for "SQLMesh" by TobikoData
3. Click Install

### 3. Configure Python Interpreter
- Open Command Palette (Ctrl+Shift+P)
- Select "Python: Select Interpreter"
- Choose the environment with sqlmesh[lsp] installed

## Key Features

| Feature | Description |
|---------|-------------|
| **Column-Level Lineage** | Interactive graph showing upstream/downstream dependencies |
| **Model Rendering** | Preview macros resolved to final SQL side-by-side |
| **Auto-Completion** | Intelligent suggestions for model names, SQL keywords |
| **Hover Tooltips** | Model descriptions and metadata on hover |
| **Go to Definition** | Jump to model/column definitions with Ctrl+Click |
| **Command Palette** | Quick access to SQLMesh commands |

## Usage

1. Open a SQLMesh project folder in VS Code
2. Open any `.sql` model file
3. Click the "Lineage" tab at the bottom panel
4. Use Command Palette for SQLMesh commands

## Alternative: SQLMesh UI Extension

Community extension that embeds the full web UI in VS Code:
- https://marketplace.visualstudio.com/items?itemName=WesleyBatista.sqlmeshui

## Status
- Open source (Apache 2.0 license)
- Actively maintained by TobikoData
- Community contributions welcome
