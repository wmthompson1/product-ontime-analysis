#!/bin/bash
# Quick verification script for SQL Lineage Analysis System

echo "🧪 SQL Lineage Analysis System - Quick Verification"
echo "======================================================"
echo ""

cd "$(dirname "$0")"

echo "📁 Current directory: $(pwd)"
echo ""

# Check Python version
echo "🐍 Python Version:"
python3 --version
echo ""

# Check dependencies
echo "📦 Checking dependencies..."
python3 -c "import sqlglot; import networkx; import pandas; import gradio; import yaml; print('✅ All dependencies installed')" 2>&1
echo ""

# Check file structure
echo "📂 Directory structure:"
find . -type f -name "*.py" | sort
echo ""

# Count files
PY_FILES=$(find . -type f -name "*.py" | wc -l)
JSON_FILES=$(find reports -type f -name "*.json" 2>/dev/null | wc -l)
echo "📊 Statistics:"
echo "  - Python modules: $PY_FILES"
echo "  - Generated reports: $JSON_FILES"
echo ""

# Test SQL parser
echo "🧪 Testing SQL Parser..."
python3 -c "
from utils.sql_parser import SQLParser
parser = SQLParser(dialect='tsql')
test_sql = 'SELECT * FROM WORK_ORDER WHERE STATUS = \\'F\\''
tables = parser.extract_tables_from_query(test_sql)
print(f'✅ Parser extracted {len(tables)} table(s)')
" 2>&1
echo ""

# Check reports exist
echo "📄 Checking generated reports..."
if [ -f "reports/lineage/table_lineage.json" ]; then
    SIZE=$(ls -lh reports/lineage/table_lineage.json | awk '{print $5}')
    echo "  ✅ table_lineage.json exists ($SIZE)"
else
    echo "  ❌ table_lineage.json not found"
fi

if [ -f "reports/lineage/column_lineage.json" ]; then
    SIZE=$(ls -lh reports/lineage/column_lineage.json | awk '{print $5}')
    echo "  ✅ column_lineage.json exists ($SIZE)"
else
    echo "  ❌ column_lineage.json not found"
fi

if [ -f "reports/graphs/lineage_graph.json" ]; then
    SIZE=$(ls -lh reports/graphs/lineage_graph.json | awk '{print $5}')
    echo "  ✅ lineage_graph.json exists ($SIZE)"
else
    echo "  ❌ lineage_graph.json not found"
fi

echo ""

# Test CLI tools
echo "🔧 Testing CLI tools..."
python3 impact/find_dependencies.py --help > /dev/null 2>&1 && echo "  ✅ find_dependencies.py" || echo "  ❌ find_dependencies.py"
python3 impact/impact_analyzer.py --help > /dev/null 2>&1 && echo "  ✅ impact_analyzer.py" || echo "  ❌ impact_analyzer.py"
echo ""

echo "======================================================"
echo "✅ Verification complete!"
echo ""
echo "🚀 Ready to use:"
echo "  • python lineage/extract_tables.py"
echo "  • python impact/find_dependencies.py --table TABLE_NAME"
echo "  • python impact/impact_analyzer.py --table TABLE_NAME"
echo "  • python dashboard/app.py  # Port 5000"
echo ""
