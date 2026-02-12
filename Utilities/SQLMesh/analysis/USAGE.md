# SQL Lineage Analysis - Usage Guide

Detailed guide for daily operations and advanced usage patterns.

## 📖 Table of Contents

1. [Daily Operations](#daily-operations)
2. [Advanced Usage](#advanced-usage)
3. [Dashboard Features](#dashboard-features)
4. [Command-Line Tools](#command-line-tools)
5. [Integration Examples](#integration-examples)
6. [Troubleshooting](#troubleshooting)

## 📅 Daily Operations

### Morning Routine: Check Recent Changes

```bash
cd Utilities/SQLMesh/analysis

# Extract latest lineage
python lineage/extract_tables.py

# Check for new high-impact tables
python graph/networkx_builder.py

# Launch dashboard to explore
python dashboard/app.py
```

### Before Schema Changes

```bash
# Analyze impact before dropping/modifying a table
python impact/impact_analyzer.py --table CUSTOMER_ORDER

# Find all affected files
python impact/find_dependencies.py --table CUSTOMER_ORDER
```

### After Adding New Reports

```bash
# Re-extract lineage
python lineage/extract_tables.py

# Rebuild graph
python graph/networkx_builder.py

# Refresh dashboard (click "Refresh Data" button)
```

## 🚀 Advanced Usage

### Batch Analysis of Multiple Tables

Create a script `check_tables.sh`:
```bash
#!/bin/bash
TABLES=("WORK_ORDER" "PART" "CUSTOMER_ORDER" "SHIPPER")

for table in "${TABLES[@]}"; do
    echo "Analyzing: $table"
    python impact/find_dependencies.py --table "$table"
    echo "---"
done
```

### Export Lineage for Documentation

```python
import json
from pathlib import Path

# Load lineage data
lineage_file = Path("reports/lineage/table_lineage.json")
with open(lineage_file) as f:
    data = json.load(f)

# Export top 20 tables to markdown
most_used = data['most_used_tables'][:20]
with open('top_tables.md', 'w') as f:
    f.write("# Most Used Tables\n\n")
    for i, table in enumerate(most_used, 1):
        f.write(f"{i}. **{table['table']}** - used {table['count']} times\n")
```

### Custom Query Analysis

```python
from utils.sql_parser import SQLParser

parser = SQLParser(dialect="tsql")

# Your custom query
sql = """
SELECT *
FROM LIVE.dbo.WORK_ORDER wo
JOIN LIVE.dbo.PART p ON wo.PART_ID = p.ID
WHERE wo.STATUS = 'OPEN'
"""

# Extract tables
tables = parser.extract_tables_from_query(sql)
print("Tables:", [t['full_name'] for t in tables])

# Analyze complexity
complexity = parser.analyze_query_complexity(sql)
print(f"Complexity Score: {complexity['complexity_score']}/100")
```

### Filter by Schema/Database

```python
# Find tables from specific database
lineage_data = json.load(open('reports/lineage/table_lineage.json'))

live_tables = set()
for file_info in lineage_data['files']:
    for table in file_info['tables']:
        if table.get('database') == 'LIVE':
            live_tables.add(table['full_name'])

print(f"Found {len(live_tables)} tables from LIVE database")
```

## 🎛️ Dashboard Features

### Overview Tab
- **Purpose**: Quick summary of entire codebase
- **Key Metrics**: 
  - Total files analyzed
  - Unique tables referenced
  - Top 20 most-used tables
- **Actions**: Refresh data to reload after running extraction

### Search Tables Tab
- **Purpose**: Find which files use a specific table
- **Usage**:
  1. Enter table name (partial or full)
  2. Click "Search"
  3. View list of files using that table
- **Tips**:
  - Can use partial names: "WORK" matches "WORK_ORDER"
  - Case-insensitive search
  - Searches both full and short table names

### File Details Tab
- **Purpose**: See all tables used by a specific file
- **Usage**:
  1. Enter file path (relative to SQL_Reports)
  2. Click "Get Details"
  3. View complete table list
- **Example Paths**:
  - `AMLA/AMLA_Hours.sql`
  - `CMP Reports/CMP Shipments.sql`
  - `Part Reports/Parts Catalog.sql`

### All Tables Tab
- **Purpose**: Browse complete table catalog
- **Features**:
  - Sortable columns
  - Click column headers to sort
  - Shows usage count for each table
- **Use Cases**:
  - Find rarely-used tables
  - Identify most critical tables
  - Export table list

### Ambiguous Columns Tab
- **Purpose**: Find queries with potential issues
- **What are ambiguous columns?**
  - Columns without explicit table qualifiers
  - Example: `SELECT Name` instead of `SELECT p.Name`
- **Why it matters**:
  - Can cause issues when tables change
  - Makes queries harder to understand
  - May cause performance issues
- **Actions**:
  - Review top offenders
  - Add table qualifiers to improve queries

### Query Analyzer Tab
- **Purpose**: Analyze any SQL query in real-time
- **Usage**:
  1. Paste SQL query into text box
  2. Click "Analyze Query"
  3. View:
     - All tables referenced
     - Complexity metrics
     - Query structure
- **Use Cases**:
  - Before adding new query to codebase
  - Optimize complex queries
  - Understand dependencies of proposed changes
  - Training: understand query structure

## 🖥️ Command-Line Tools

### extract_tables.py

**Purpose**: Extract table lineage from all SQL files

```bash
# Basic usage
python lineage/extract_tables.py

# Output location
# reports/lineage/table_lineage.json
```

**When to run**:
- After adding/modifying SQL files
- Daily as part of CI/CD
- Before major refactoring

### column_lineage.py

**Purpose**: Identify ambiguous columns

```bash
python lineage/column_lineage.py

# Output location
# reports/lineage/column_lineage.json
```

**When to run**:
- During code quality reviews
- Before major schema changes
- When investigating query issues

### find_dependencies.py

**Purpose**: Quick lookup of table usage

```bash
# Find files using specific table
python impact/find_dependencies.py --table WORK_ORDER

# Exact match only
python impact/find_dependencies.py --table WORK_ORDER --exact

# Exit codes:
# 0 = files found
# 1 = no files found
```

**Use Cases**:
- Quick checks during development
- Script automation
- CI/CD validation

### impact_analyzer.py

**Purpose**: Assess impact of schema changes

```bash
python impact/impact_analyzer.py --table PART

# Exit codes:
# 0 = no impact
# 1 = low impact
# 2 = medium impact
# 3 = high impact
```

**Output Includes**:
- Impact level (none/low/medium/high)
- Number of affected files
- List of affected files
- Specific recommendations

**Use Cases**:
- Before dropping tables
- Before schema migrations
- Risk assessment

### networkx_builder.py

**Purpose**: Build graph representation

```bash
python graph/networkx_builder.py

# Outputs:
# reports/graphs/lineage_graph.graphml  (for Gephi, yEd)
# reports/graphs/lineage_graph.json     (for D3.js)
# reports/graphs/lineage_graph.gpickle  (for Python)
```

**When to run**:
- After lineage extraction
- When exporting for visualization
- Before using graph-based queries

## 🔄 Integration Examples

### Pre-commit Hook

Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Check if SQL files changed
if git diff --cached --name-only | grep -q "\.sql$"; then
    echo "SQL files changed - updating lineage..."
    cd Utilities/SQLMesh/analysis
    python lineage/extract_tables.py
    git add reports/lineage/table_lineage.json
fi
```

### CI/CD Pipeline

See `.github/workflows/sql-lineage.yml` for complete example.

Key steps:
1. Checkout code
2. Install Python dependencies
3. Run lineage extraction
4. Upload reports as artifacts
5. Commit reports back to repo

### VSCode Task

Create `.vscode/tasks.json`:
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Extract SQL Lineage",
      "type": "shell",
      "command": "cd Utilities/SQLMesh/analysis && python lineage/extract_tables.py",
      "problemMatcher": []
    },
    {
      "label": "Launch Lineage Dashboard",
      "type": "shell",
      "command": "cd Utilities/SQLMesh/analysis && python dashboard/app.py",
      "problemMatcher": []
    }
  ]
}
```

### Python Script Integration

```python
from pathlib import Path
import sys

# Add to path
sys.path.insert(0, str(Path(__file__).parent / "Utilities/SQLMesh/analysis"))

from utils.sql_parser import SQLParser
from graph.networkx_builder import LineageGraphBuilder

# Parse custom query
parser = SQLParser()
tables = parser.extract_tables_from_query("SELECT * FROM WORK_ORDER")

# Query graph
builder = LineageGraphBuilder(Path("Utilities/SQLMesh/analysis/reports/lineage/table_lineage.json"))
builder.build_graph()
files = builder.find_table_dependencies("WORK_ORDER")
```

## 🐛 Troubleshooting

### Issue: "Lineage file not found"

**Cause**: Haven't run extraction yet

**Solution**:
```bash
cd Utilities/SQLMesh/analysis
python lineage/extract_tables.py
```

### Issue: Dashboard shows no data

**Causes**:
1. Reports not generated
2. Path issues

**Solutions**:
```bash
# Generate reports
python lineage/extract_tables.py
python lineage/column_lineage.py

# Rebuild graph
python graph/networkx_builder.py

# Restart dashboard
python dashboard/app.py
```

### Issue: Parse errors on specific files

**Cause**: Complex SQL syntax not fully supported

**Solution**:
- Check error logs in console output
- Most parse errors are non-fatal
- Parser uses fallback method for problematic queries
- File is still analyzed, just with reduced accuracy

### Issue: Port 5000 already in use

**Solution**:
```bash
# Check what's using port
lsof -i :5000

# Kill process
kill -9 <PID>

# Or edit dashboard/app.py to use different port
# Change: dashboard.launch(port=5001)
```

### Issue: Slow performance

**Optimization tips**:
```bash
# Extract lineage less frequently
# Use incremental processing (future feature)

# For dashboard:
# - Only load data when needed
# - Use filters to reduce dataset size
# - Consider sampling for very large codebases
```

### Issue: Table not found in search

**Possible causes**:
1. Table name typo
2. Table not used in any SQL files
3. Table reference in unsupported syntax

**Debug steps**:
```bash
# Check raw lineage data
cat reports/lineage/table_lineage.json | grep -i "table_name"

# Try partial match (default behavior)
python impact/find_dependencies.py --table PART  # not --exact
```

## 📊 Best Practices

### Regular Maintenance

1. **Daily**: Run extraction after SQL changes
2. **Weekly**: Review ambiguous columns report
3. **Monthly**: Analyze graph statistics for trends
4. **Before releases**: Run impact analysis on changed tables

### Code Quality

- Use dashboard's Query Analyzer before adding new SQL
- Address ambiguous columns in high-priority files
- Document complex table dependencies
- Keep lineage reports in version control

### Team Collaboration

- Share dashboard URL with team (port 5000)
- Include lineage reports in code reviews
- Use impact analysis in change requests
- Train new team members using Query Analyzer

### Performance

- Extract lineage during off-hours for large codebases
- Use CI/CD to automate extraction
- Cache graph data for faster queries
- Consider incremental extraction (future)

## 🎯 Tips and Tricks

### Quick Table Lookup
```bash
# Create alias in .bashrc/.zshrc
alias sqlfind='cd /path/to/repo/Utilities/SQLMesh/analysis && python impact/find_dependencies.py --table'

# Usage
sqlfind WORK_ORDER
```

### Export for Confluence
```python
# Convert reports to Confluence-friendly format
import json
import pandas as pd

data = json.load(open('reports/lineage/table_lineage.json'))
df = pd.DataFrame(data['most_used_tables'][:20])
df.to_html('top_tables.html')
```

### Jupyter Notebook Analysis
```python
import json
import pandas as pd
import matplotlib.pyplot as plt

# Load data
data = json.load(open('reports/lineage/table_lineage.json'))

# Create DataFrame
tables = pd.DataFrame(data['most_used_tables'])

# Plot
tables.head(10).plot(x='table', y='count', kind='barh')
plt.title('Top 10 Most Used Tables')
plt.show()
```

## 📚 Additional Resources

- [README.md](README.md) - Overview and quick start
- [config.yaml](config.yaml) - Configuration options
- SQL Parser documentation: `utils/sql_parser.py`
- Graph builder documentation: `graph/networkx_builder.py`

---

**Need help?** Create an issue in the repository or consult the main README.
