# MCP File System Server - Installation Guide

This guide covers multiple installation methods for the MCP File System Server.

## Prerequisites

- Python 3.10 or higher
- pip or uv package manager
- Git (for cloning or pip install from GitHub)

## Installation Methods

### Method 1: Install from GitHub (Recommended)

The simplest way to install for production use:

```bash
pip install git+https://github.com/MarcusJellinghaus/mcp_server_filesystem.git
```

Verify installation:

```bash
mcp-server-filesystem --help
```

### Method 2: Install with uv

For faster installation using the uv package manager:

```bash
# Create python environment
uv venv

# Activate environment
# On Windows:
.venv\Scripts\activate
# On Unix/MacOS:
source .venv/bin/activate

# Install from GitHub
uv pip install git+https://github.com/MarcusJellinghaus/mcp_server_filesystem.git
```

### Method 3: Clone and Install (Development)

For development or customization:

```bash
# Clone the repository
git clone https://github.com/MarcusJellinghaus/mcp_server_filesystem.git
cd mcp_server_filesystem

# Create and activate a virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install in development mode
pip install -e .

# To include development dependencies:
pip install -e ".[dev]"
```

## Command Line Arguments

Once installed, the `mcp-server-filesystem` command accepts these arguments:

| Argument | Required | Description |
|----------|----------|-------------|
| `--project-dir` | Yes | Base directory for all file operations |
| `--reference-project` | No | Reference project in format `name=/path/to/dir` (repeatable) |
| `--log-level` | No | Set logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `--log-file` | No | Path for structured JSON logs |
| `--console-only` | No | Log only to console, ignore --log-file |

## Basic Usage Examples

### Single Project

```bash
mcp-server-filesystem --project-dir /path/to/your/project
```

### With Reference Projects

```bash
mcp-server-filesystem \
  --project-dir ./my-project \
  --reference-project docs=./documentation \
  --reference-project examples=/home/user/examples
```

### With Custom Logging

```bash
mcp-server-filesystem \
  --project-dir ./my-project \
  --log-level DEBUG \
  --log-file ./logs/mcp-server.log
```

### Console-Only Mode

```bash
mcp-server-filesystem \
  --project-dir ./my-project \
  --console-only \
  --log-level INFO
```

## Adding to requirements.txt

Add this line to your `requirements.txt`:

```
git+https://github.com/MarcusJellinghaus/mcp_server_filesystem.git
```

Then install with:

```bash
pip install -r requirements.txt
```

## Adding to package.json (npm scripts)

Add a script to run the MCP server alongside your other services:

```json
{
  "scripts": {
    "mcp-fs": "mcp-server-filesystem --project-dir . --reference-project schemas=./sample_data --console-only"
  }
}
```

Run with:

```bash
npm run mcp-fs
```

## Verification

After installation, verify everything works:

```bash
# Check version
mcp-server-filesystem --version

# Check help
mcp-server-filesystem --help

# Test with a project directory
mcp-server-filesystem --project-dir /tmp --console-only
```

Expected output:

```
2024-XX-XX XX:XX:XX - mcp_server_filesystem - INFO - Starting MCP server with project directory: /tmp
2024-XX-XX XX:XX:XX - mcp_server_filesystem - INFO - Project directory set to: /tmp
2024-XX-XX XX:XX:XX - mcp_server_filesystem - INFO - Starting MCP server
```

## Troubleshooting

### Command Not Found

If `mcp-server-filesystem` is not found after installation:

1. Ensure your virtual environment is activated
2. Check if the package installed correctly: `pip show mcp-server-filesystem`
3. Verify the script is in your PATH: `which mcp-server-filesystem`

### Import Errors

If you see import errors when running:

1. Ensure all dependencies installed: `pip install -e ".[dev]"`
2. Check Python version: `python --version` (requires 3.10+)

### Permission Issues

If you encounter permission errors:

1. Ensure the project directory exists and is accessible
2. Check file permissions on the target directory
3. On Windows, run as Administrator if needed

## Next Steps

- [Tools Reference](03-tools-reference.md) - Learn about available file operations
- [Integration Guide](04-integration.md) - Connect to AI assistants
