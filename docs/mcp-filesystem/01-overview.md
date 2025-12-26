# MCP File System Server - Overview

A Model Context Protocol (MCP) server providing secure file system operations for AI assistants. This server enables tools like GitHub Copilot, Claude, and Cursor to interact with your local files safely.

## What is MCP?

The **Model Context Protocol (MCP)** is an open standard introduced by Anthropic that provides a universal way to connect AI assistants to external data sources and tools. Think of it as "USB-C for AI" - instead of building custom integrations for every AI tool, MCP offers one protocol that everything can speak.

## Why Use This Server?

This MCP server enables AI assistants to:

- **Read** your existing code and project files
- **Write** new files with generated content
- **Update** existing files with precision using exact string matching
- **Make selective edits** to code without rewriting entire files
- **Delete** files when needed
- **Review** repositories to provide analysis and recommendations
- **Debug** and fix issues in your codebase
- **Generate** complete implementations based on your specifications

All operations are securely contained within your specified project directory, giving you control while enabling powerful AI collaboration on your local files.

## Key Features

| Feature | Description |
|---------|-------------|
| `list_directory` | List all files and directories in the project |
| `read_file` | Read the contents of a file |
| `save_file` | Write content to a file atomically |
| `append_file` | Append content to the end of a file |
| `delete_this_file` | Delete a specified file from the filesystem |
| `edit_file` | Make selective edits using exact string matching |
| `move_file` | Move or rename files and directories |
| `get_reference_projects` | Discover available read-only reference projects |
| `list_reference_directory` | List files in reference projects |
| `read_reference_file` | Read files from reference projects |

## Security Features

- **Path Validation**: All file operations are restricted to the specified project directory
- **Directory Traversal Prevention**: Attempts to access files outside the project directory result in errors
- **Reference Projects**: Read-only access to additional directories for context
- **Gitignore Filtering**: Automatically hides files matching .gitignore patterns

## Supported AI Tools

This MCP server works with:

- **GitHub Copilot** (VS Code)
- **Claude Desktop**
- **Cursor**
- **Windsurf**
- **Zed**
- **Any MCP-compatible AI assistant**

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      AI Assistant                            │
│              (GitHub Copilot, Claude, Cursor)               │
└─────────────────────────┬───────────────────────────────────┘
                          │ MCP Protocol
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 MCP File System Server                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐│
│  │   File Tools    │  │  Reference      │  │   Logging    ││
│  │  (read, write,  │  │  Projects       │  │   System     ││
│  │   edit, move)   │  │  (read-only)    │  │              ││
│  └─────────────────┘  └─────────────────┘  └──────────────┘│
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Your Project Files                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   src/      │  │   docs/     │  │   sample_data/      │ │
│  │  (r/w)      │  │  (r/w)      │  │  (reference, r/o)   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Install from GitHub
pip install git+https://github.com/MarcusJellinghaus/mcp_server_filesystem.git

# Run the server
mcp-server-filesystem --project-dir /path/to/your/project --console-only
```

## Next Steps

- [Installation Guide](02-installation.md) - Detailed installation instructions
- [Tools Reference](03-tools-reference.md) - Complete tool documentation
- [Integration Guide](04-integration.md) - Setting up with AI tools
