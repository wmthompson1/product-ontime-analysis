# MCP File System Server - Tools Reference

Complete documentation for all available MCP tools exposed by the server.

## Tool Summary

| Tool | Operation | Access Level |
|------|-----------|--------------|
| `list_directory` | List files and directories | Read |
| `read_file` | Read file contents | Read |
| `save_file` | Create or overwrite files | Write |
| `append_file` | Add content to existing files | Write |
| `edit_file` | Make selective edits | Write |
| `move_file` | Move or rename files | Write |
| `delete_this_file` | Remove files | Write |
| `get_reference_projects` | List reference projects | Read |
| `list_reference_directory` | List reference project files | Read |
| `read_reference_file` | Read reference project files | Read |

---

## list_directory

Lists all files and directories in the project directory.

**Parameters:** None (lists from project root)

**Returns:** List of file and directory names

**Behavior:**
- Results are filtered based on `.gitignore` patterns
- `.git` folders are excluded by default
- Returns both files and directories

**Example Prompt:**
> "List all files in the src directory"

---

## read_file

Reads the contents of a file.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `file_path` | string | Path to the file (relative to project directory) |

**Returns:** File content as a string

**Example Prompt:**
> "Show me the contents of main.js"

---

## save_file

Creates or overwrites a file atomically.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `file_path` | string | Path to the file to write |
| `content` | string | Content to write to the file |

**Returns:** Boolean indicating success

**Notes:**
- Creates parent directories if they don't exist
- Atomic write prevents partial file corruption
- Overwrites existing files without warning

**Example Prompt:**
> "Create a new file called app.js with a basic Express server"

---

## append_file

Appends content to the end of an existing file.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `file_path` | string | Path to the file to append to |
| `content` | string | Content to append |

**Returns:** Boolean indicating success

**Notes:**
- The file must already exist
- Use `save_file` to create new files

**Example Prompt:**
> "Add a new function to the end of utils.js"

---

## edit_file

Makes precise edits to files using exact string matching. This is the most powerful tool for code modifications.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `file_path` | string | File to edit (relative to project directory) |
| `edits` | array | List of edit operations |
| `dry_run` | boolean | Preview changes without applying (default: false) |
| `options` | object | Formatting settings |

**Edit Object Structure:**
```json
{
  "old_text": "exact text to find",
  "new_text": "replacement text"
}
```

**Options:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `preserve_indentation` | boolean | false | Apply indentation from old_text to new_text |

**Key Characteristics:**
- **Exact string matching only** - `old_text` must match exactly (case-sensitive, whitespace-sensitive)
- **No fuzzy matching** - For maximum reliability and predictability
- **First occurrence only** - Replaces only the first match of each pattern
- **Sequential processing** - Edits applied in order, each seeing results of previous edits
- **Already-applied detection** - Automatically detects when edits are already applied
- **Git-style diff output** - Shows exactly what changed

**Examples:**

Basic text replacement:
```python
edit_file("config.py", [
    {"old_text": "DEBUG = False", "new_text": "DEBUG = True"}
])
```

Multiple edits in one operation:
```python
edit_file("app.py", [
    {"old_text": "def old_function():", "new_text": "def new_function():"},
    {"old_text": "old_function()", "new_text": "new_function()"}
])
```

Preview changes without applying:
```python
edit_file("code.py", edits, dry_run=True)
```

With indentation preservation:
```python
edit_file("indented.py", [
    {"old_text": "    old_code()", "new_text": "new_code()"}
], options={"preserve_indentation": True})
```

**Example Prompt:**
> "Fix the bug in the fetch function by changing the timeout from 5000 to 10000"

---

## move_file

Moves or renames files and directories within the project.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `source_path` | string | Source file/directory path |
| `destination_path` | string | Destination path |

**Returns:** Boolean indicating success

**Features:**
- Automatically creates parent directories if needed
- Preserves git history when moving tracked files
- Falls back to filesystem operations if git is unavailable
- Works for both files and directories

**Examples:**

Rename a file:
```python
move_file("old_name.py", "new_name.py")
```

Move to a different directory:
```python
move_file("src/temp.py", "archive/temp.py")
```

Rename a directory:
```python
move_file("old_folder", "new_folder")
```

**Error Messages:**
| Error | Meaning |
|-------|---------|
| "File not found" | Source doesn't exist |
| "Destination already exists" | Target path is occupied |
| "Permission denied" | Access issues |
| "Invalid path" | Security violation |

**Example Prompt:**
> "Rename config.js to settings.js"

---

## delete_this_file

Deletes a specified file from the filesystem.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `file_path` | string | Path to the file to delete |

**Returns:** Boolean indicating success

**Warning:** This operation is irreversible and will permanently remove the file.

**Example Prompt:**
> "Delete the temporary.txt file"

---

## Reference Project Tools

These tools provide read-only access to additional codebases.

### get_reference_projects

Discovers available reference projects.

**Parameters:** None

**Returns:** Dictionary of available reference projects with their paths

**Example Prompt:**
> "What reference projects are available?"

### list_reference_directory

Lists files in a reference project directory.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `project_name` | string | Name of the reference project |
| `path` | string | Path within the reference project (optional) |

**Returns:** List of files and directories

**Example Prompt:**
> "List files in the docs reference project"

### read_reference_file

Reads a file from a reference project.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `project_name` | string | Name of the reference project |
| `file_path` | string | Path to the file within the reference project |

**Returns:** File content as a string

**Example Prompt:**
> "Show me the README from the examples project"

---

## Error Handling

All tools return clear error messages when operations fail:

| Error Type | Description |
|------------|-------------|
| Path validation error | Attempted access outside project directory |
| File not found | Requested file doesn't exist |
| Permission denied | Insufficient permissions |
| Invalid operation | Operation not allowed (e.g., writing to reference project) |

## Next Steps

- [Integration Guide](04-integration.md) - Connect to AI assistants
