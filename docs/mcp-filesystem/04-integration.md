# MCP File System Server - Integration Guide

This guide covers how to integrate the MCP File System Server with various AI tools and development environments.

## VS Code with GitHub Copilot

### Configuration

Add to your VS Code MCP settings (`.vscode/mcp.json` or workspace settings):

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "mcp-server-filesystem",
      "args": [
        "--project-dir", "${workspaceFolder}",
        "--reference-project", "schemas=./sample_data",
        "--console-only"
      ]
    }
  }
}
```

### Usage

Once configured, you can ask GitHub Copilot questions like:

- "List all files in the src directory"
- "Read the contents of package.json"
- "Create a new utility file with helper functions"
- "Fix the typo in config.js"

---

## Claude Desktop

### Configuration

1. Locate the Claude Desktop configuration file:
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

2. Add the MCP server configuration:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "mcp-server-filesystem",
      "args": [
        "--project-dir",
        "C:\\path\\to\\your\\project",
        "--reference-project",
        "docs=C:\\path\\to\\documentation",
        "--log-level",
        "INFO"
      ]
    }
  }
}
```

3. Restart Claude Desktop to apply changes.

### Troubleshooting

- Check logs at: `%APPDATA%\Claude\logs` (Windows) or `~/Library/Application Support/Claude/logs` (macOS)
- Verify `mcp-server-filesystem` is in your PATH
- Ensure the project directory exists

---

## Cursor

### Configuration

Add to your Cursor MCP configuration:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "mcp-server-filesystem",
      "args": [
        "--project-dir", ".",
        "--console-only"
      ]
    }
  }
}
```

---

## Windsurf

Windsurf requires a local proxy for MCP servers:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y", 
        "mcp-remote", 
        "mcp-server-filesystem --project-dir /path/to/project"
      ]
    }
  }
}
```

---

## npm Scripts Integration

For projects using npm, add these scripts to `package.json`:

```json
{
  "scripts": {
    "mcp-fs": "mcp-server-filesystem --project-dir . --console-only",
    "mcp-fs:schemas": "mcp-server-filesystem --project-dir . --reference-project schemas=./sample_data --console-only",
    "mcp-fs:debug": "mcp-server-filesystem --project-dir . --log-level DEBUG"
  }
}
```

Run with:

```bash
npm run mcp-fs
```

---

## Running Alongside Other Services

Use `concurrently` to run the MCP server with your development servers:

```json
{
  "scripts": {
    "dev:all": "concurrently -n flask,astro,mcp -c blue,magenta,green \"npm run flask\" \"npm run astro\" \"npm run mcp-fs\""
  }
}
```

---

## Reference Projects Configuration

Reference projects provide read-only access to additional codebases for context.

### Use Cases

| Use Case | Configuration |
|----------|--------------|
| Documentation | `--reference-project docs=./documentation` |
| Code examples | `--reference-project examples=/path/to/examples` |
| Shared libraries | `--reference-project libs=../shared-libraries` |
| Schema files | `--reference-project schemas=./sample_data` |
| HF Space code | `--reference-project hf-space=./hf-space-inventory-sqlgen` |

### Multiple Reference Projects

```bash
mcp-server-filesystem \
  --project-dir ./my-project \
  --reference-project docs=./documentation \
  --reference-project examples=/home/user/examples \
  --reference-project libs=../shared-libraries \
  --reference-project schemas=./sample_data
```

### Auto-Rename Behavior

Duplicate names are automatically renamed with numeric suffixes:

```bash
# Input:
--reference-project docs=./docs1 \
--reference-project docs=./docs2 \
--reference-project docs=./docs3

# Results in:
# - docs (points to ./docs1)
# - docs_2 (points to ./docs2)
# - docs_3 (points to ./docs3)
```

---

## MCP Inspector (Testing & Development)

Use MCP Inspector for debugging and testing:

```bash
npx @modelcontextprotocol/inspector \
  mcp-server-filesystem \
  --project-dir /path/to/your/project \
  --log-level DEBUG
```

In the MCP Inspector web UI, you can:

- Test individual tools
- View request/response payloads
- Debug file operations
- Verify reference project access

---

## Logging Configuration

### Console Only (Development)

```bash
mcp-server-filesystem --project-dir . --console-only --log-level DEBUG
```

### File Logging (Production)

```bash
mcp-server-filesystem \
  --project-dir . \
  --log-file ./logs/mcp-server.log \
  --log-level INFO
```

### Log Levels

| Level | Description |
|-------|-------------|
| DEBUG | Detailed debugging information |
| INFO | General operational messages |
| WARNING | Potential issues |
| ERROR | Error conditions |
| CRITICAL | Serious problems |

---

## Complete Example Configuration

For a manufacturing analytics project with multiple MCP servers:

### package.json

```json
{
  "scripts": {
    "dev": "concurrently -n flask,astro -c blue,magenta \"npm run flask\" \"npm run astro\"",
    "flask": "python main.py",
    "astro": "cd astro-sample && npm run dev",
    "hf-space": "cd hf-space-inventory-sqlgen && python app.py",
    "mcp-fs": "mcp-server-filesystem --project-dir . --reference-project schemas=./sample_data --reference-project hf-space=./hf-space-inventory-sqlgen --console-only"
  }
}
```

### VS Code MCP Configuration

```json
{
  "mcpServers": {
    "Astro docs": {
      "url": "https://mcp.docs.astro.build/mcp"
    },
    "Astro project": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:4321/__mcp/sse"]
    },
    "filesystem": {
      "command": "mcp-server-filesystem",
      "args": [
        "--project-dir", "${workspaceFolder}",
        "--reference-project", "schemas=./sample_data",
        "--reference-project", "hf-space=./hf-space-inventory-sqlgen",
        "--console-only"
      ]
    }
  }
}
```

---

## Security Best Practices

1. **Limit project directory scope** - Only expose directories AI needs access to
2. **Use reference projects for read-only access** - Prevent accidental modifications to important files
3. **Review gitignore patterns** - Ensure sensitive files are excluded
4. **Monitor logs** - Watch for unexpected file access patterns
5. **Use console-only in development** - Avoid filling disk with log files

---

## Troubleshooting

### Server Not Starting

1. Verify installation: `mcp-server-filesystem --version`
2. Check Python version: `python --version` (requires 3.10+)
3. Ensure virtual environment is activated

### Tool Not Available

1. Restart the AI assistant after configuration changes
2. Check MCP server logs for errors
3. Verify project directory exists and is accessible

### Reference Project Not Found

1. Check path is correct (relative or absolute)
2. Verify directory exists
3. Check for typos in reference project name

### Permission Errors

1. Ensure the user running the MCP server has read/write access
2. Check file permissions on the project directory
3. On Windows, run as Administrator if needed
