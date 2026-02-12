# SQL Lineage Analysis System

A comprehensive SQL lineage analysis system for exploring dependencies, impact analysis, and query complexity in SQL Server T-SQL files.

## 🎯 Features

### Core Capabilities
- **Table Lineage Extraction**: Automatically scan and extract table dependencies from all SQL files
- **Column-Level Analysis**: Identify columns and detect ambiguous references
- **Impact Analysis**: Assess the impact of schema changes before making them
- **Interactive Dashboard**: Web-based Gradio interface for exploring lineage data
- **Graph Visualization**: NetworkX-based graph representation of dependencies
- **Real-time Query Analysis**: Paste any SQL query to analyze its dependencies

### Key Characteristics
- ✅ **Read-Only**: NO SQL execution - only static analysis using sqlglot
- ✅ **Safe**: Works with production SQL files without any database connections
- ✅ **Fast**: Parallel processing for large codebases
- ✅ **Comprehensive**: Supports SQL Server T-SQL dialect
- ✅ **Interactive**: Web dashboard on port 5000

## 🚀 Quick Start

### 1. Installation

```bash
cd Utilities/SQLMesh/analysis
pip install -r requirements.txt
```

### 2. Extract Lineage

```bash
python lineage/extract_tables.py
```

This will:
- Scan all SQL files in `SQL_Reports/`
- Extract table dependencies
- Generate report: `reports/lineage/table_lineage.json`

### 3. Launch Dashboard

```bash
python dashboard/app.py
```

Access at: **http://localhost:5000**

## 📁 Project Structure

```
analysis/
├── __init__.py
├── config.yaml                 # Configuration file
├── README.md                   # This file
├── USAGE.md                    # Detailed usage guide
├── requirements.txt            # Python dependencies
│
├── lineage/                    # Lineage extraction
│   ├── __init__.py
│   ├── extract_tables.py       # Main table extraction script
│   └── column_lineage.py       # Column-level analysis
│
├── impact/                     # Impact analysis
│   ├── __init__.py
│   ├── find_dependencies.py    # CLI tool to find table usage
│   └── impact_analyzer.py      # Assess impact of changes
│
├── graph/                      # Graph building
│   ├── __init__.py
│   ├── networkx_builder.py     # NetworkX graph builder
│   └── arango_integration.py   # ArangoDB stub (future)
│
├── dashboard/                  # Web interface
│   ├── __init__.py
│   └── app.py                  # Gradio dashboard
│
├── utils/                      # Utilities
│   ├── __init__.py
│   └── sql_parser.py           # SQL parsing with sqlglot
│
└── reports/                    # Generated reports
    ├── lineage/
    │   ├── table_lineage.json
    │   └── column_lineage.json
    ├── impact/
    └── graphs/
        ├── lineage_graph.graphml
        ├── lineage_graph.json
        └── lineage_graph.gpickle
```

## 🎮 Usage Examples

### Extract Table Lineage

```bash
cd Utilities/SQLMesh/analysis
python lineage/extract_tables.py
```

Output:
```
📁 Found 250 SQL files
📊 Extracting table lineage...
✅ Extraction complete!
  Total files: 250
  Successful: 245
  Failed: 5
  Unique tables: 87
```

### Find Table Dependencies

```bash
python impact/find_dependencies.py --table WORK_ORDER
```

Output shows all SQL files that reference the table.

### Analyze Impact

```bash
python impact/impact_analyzer.py --table PART
```

Provides:
- Impact level (none/low/medium/high)
- List of affected files
- Recommendations for safe changes

### Build Graph

```bash
python graph/networkx_builder.py
```

Exports graph in multiple formats:
- GraphML (for Gephi, yEd)
- JSON (for D3.js, Cytoscape.js)
- Pickle (for Python NetworkX)

### Launch Dashboard

```bash
python dashboard/app.py
```

Features:
- **Overview**: Summary statistics and top tables
- **Search Tables**: Find files using specific tables
- **File Details**: View all tables used by a file
- **All Tables**: Sortable complete table list
- **Ambiguous Columns**: Identify columns needing qualifiers
- **Query Analyzer**: Analyze any SQL query in real-time

## ⚙️ Configuration

Edit `config.yaml` to customize:

```yaml
sql_dialect: tsql
dashboard:
  port: 5000
important_tables:
  - WORK_ORDER
  - CUSTOMER_ORDER
```

## 🔒 Important Notes

### Read-Only Operation
This system is **completely safe** for production environments:
- ❌ **NO database connections**
- ❌ **NO SQL execution**
- ❌ **NO modifications to source files**
- ✅ **Only reads and parses SQL files**
- ✅ **Static analysis only using sqlglot**

### Supported SQL Syntax
- SQL Server T-SQL dialect
- Fully qualified table names: `database.schema.table`
- Table aliases
- CTEs (Common Table Expressions)
- Subqueries
- All JOIN types

### Error Handling
- Gracefully handles parse errors
- Continues processing even if individual files fail
- Logs all errors for review
- Uses `encoding='utf-8', errors='ignore'` for file reading

## 📊 Output Reports

### Table Lineage Report
`reports/lineage/table_lineage.json`:
```json
{
  "files": [...],
  "summary": {
    "total_files": 250,
    "unique_tables": 87
  },
  "most_used_tables": [...]
}
```

### Column Lineage Report
`reports/lineage/column_lineage.json`:
```json
{
  "files": [...],
  "ambiguous_files": [...],
  "summary": {
    "files_with_ambiguous_columns": 45
  }
}
```

### Graph Exports
- `reports/graphs/lineage_graph.graphml` - For visualization tools
- `reports/graphs/lineage_graph.json` - For web applications
- `reports/graphs/lineage_graph.gpickle` - For Python analysis

## 🔄 Integration with CI/CD

The system includes a GitHub Actions workflow (`.github/workflows/sql-lineage.yml`) that:
1. Runs automatically when SQL files change
2. Extracts lineage data
3. Uploads reports as artifacts
4. Commits reports back to repository

## 🚀 Future Enhancements

Planned features:
- [ ] ArangoDB integration for graph queries
- [ ] Visual graph rendering in dashboard
- [ ] Change detection (compare lineage over time)
- [ ] SQL query suggestions for optimization
- [ ] Export to Confluence/GitBook
- [ ] Integration with SQLMesh models
- [ ] Email alerts for high-impact changes

## 🐛 Troubleshooting

### Dashboard won't start
```bash
# Check if port 5000 is available
lsof -i :5000

# Use different port
python dashboard/app.py  # Edit to change port
```

### Parse errors
- Check SQL syntax for T-SQL compatibility
- Review error logs in output
- Most parse errors are non-fatal and logged for review

### Missing reports
```bash
# Ensure lineage extraction ran first
python lineage/extract_tables.py
python lineage/column_lineage.py
```

## 📚 Dependencies

Core dependencies:
- `sqlglot>=23.0.0` - SQL parsing
- `networkx>=3.0` - Graph operations
- `pandas>=2.0.0` - Data manipulation
- `gradio>=4.0.0` - Web dashboard
- `pyyaml>=6.0` - Configuration

Optional:
- `python-arango>=7.0.0` - ArangoDB integration (future)
- `matplotlib>=3.7.0` - Graph visualization (future)

## 🤝 Contributing

To extend this system:
1. Add new analysis modules in appropriate subdirectory
2. Update dashboard to expose new features
3. Add tests for new functionality
4. Update documentation

## 📝 License

Part of the Skills-Inc-Org/SQL-Projects repository.

## 🔗 Related Documentation

- [USAGE.md](USAGE.md) - Detailed usage guide
- [config.yaml](config.yaml) - Configuration reference
- [GitHub Actions Workflow](../../.github/workflows/sql-lineage.yml) - CI integration

## 📧 Support

For questions or issues:
1. Check existing reports in `reports/` directory
2. Review logs for error messages
3. Consult USAGE.md for advanced examples
4. Create an issue in the repository
