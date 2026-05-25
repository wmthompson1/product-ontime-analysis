"""
Tests that the "Reference only" disclaimer banners exist in the Cypher and AQL
tab definitions inside hf-space-inventory-sqlgen/app.py, and that each
disclaimer appears *before* the corresponding gr.Code call (so a refactor
cannot accidentally move them below the code block).

The SQL Equivalent tab is separately asserted to carry no such disclaimer.
"""
import re
import pathlib

APP_PY = pathlib.Path(__file__).parent.parent / "hf-space-inventory-sqlgen" / "app.py"
DISCLAIMER_TEXT = "Reference only"


def _load_source():
    return APP_PY.read_text(encoding="utf-8")


def _extract_tab_block(source: str, tab_header: str) -> str:
    """
    Return the lines that belong to the named gr.Tab(...) block.

    Extraction stops when we encounter a non-empty, non-continuation line
    whose indentation is less than or equal to that of the opening
    ``with gr.Tab(...)`` line, ensuring we never bleed into code that
    follows the tab block (e.g. helper functions at the same nesting level).
    """
    lines = source.splitlines()
    start = None
    for i, line in enumerate(lines):
        if f'gr.Tab("{tab_header}")' in line:
            start = i
            break
    assert start is not None, f"Could not find tab: {tab_header!r} in app.py"

    header_indent = len(lines[start]) - len(lines[start].lstrip())

    block_lines = []
    for line in lines[start + 1:]:
        stripped = line.lstrip()
        if stripped == "":
            block_lines.append(line)
            continue
        line_indent = len(line) - len(stripped)
        if line_indent <= header_indent:
            break
        block_lines.append(line)
    return "\n".join(block_lines)


# ---------------------------------------------------------------------------
# Cypher tab
# ---------------------------------------------------------------------------

class TestCypherTabDisclaimer:
    def test_disclaimer_present_in_cypher_tab(self):
        """Disclaimer text must appear somewhere inside the Cypher tab block."""
        block = _extract_tab_block(_load_source(), "Cypher (Neo4j)")
        assert DISCLAIMER_TEXT in block, (
            "The 'Reference only' disclaimer is missing from the Cypher (Neo4j) tab "
            "in hf-space-inventory-sqlgen/app.py."
        )

    def test_disclaimer_before_gr_code_in_cypher_tab(self):
        """
        The disclaimer Markdown must appear *before* the gr.Code call so it
        is rendered above the code block in the UI.
        """
        block = _extract_tab_block(_load_source(), "Cypher (Neo4j)")
        disclaimer_pos = block.find(DISCLAIMER_TEXT)
        code_pos = block.find("gr.Code(")
        assert disclaimer_pos != -1, "Disclaimer not found in Cypher tab block."
        assert code_pos != -1, "gr.Code not found in Cypher tab block."
        assert disclaimer_pos < code_pos, (
            "The 'Reference only' disclaimer must appear before the gr.Code call "
            "in the Cypher (Neo4j) tab, but it was found after it."
        )


# ---------------------------------------------------------------------------
# AQL tab
# ---------------------------------------------------------------------------

class TestAQLTabDisclaimer:
    def test_disclaimer_present_in_aql_tab(self):
        """Disclaimer text must appear somewhere inside the AQL tab block."""
        block = _extract_tab_block(_load_source(), "AQL (ArangoDB)")
        assert DISCLAIMER_TEXT in block, (
            "The 'Reference only' disclaimer is missing from the AQL (ArangoDB) tab "
            "in hf-space-inventory-sqlgen/app.py."
        )

    def test_disclaimer_before_gr_code_in_aql_tab(self):
        """
        The disclaimer Markdown must appear *before* the gr.Code call so it
        is rendered above the code block in the UI.
        """
        block = _extract_tab_block(_load_source(), "AQL (ArangoDB)")
        disclaimer_pos = block.find(DISCLAIMER_TEXT)
        code_pos = block.find("gr.Code(")
        assert disclaimer_pos != -1, "Disclaimer not found in AQL tab block."
        assert code_pos != -1, "gr.Code not found in AQL tab block."
        assert disclaimer_pos < code_pos, (
            "The 'Reference only' disclaimer must appear before the gr.Code call "
            "in the AQL (ArangoDB) tab, but it was found after it."
        )


# ---------------------------------------------------------------------------
# SQL Equivalent tab — must NOT carry a disclaimer
# ---------------------------------------------------------------------------

class TestSQLEquivalentTabNoDisclaimer:
    def test_no_disclaimer_in_sql_equivalent_tab(self):
        """
        The SQL Equivalent tab is a plain output pane and must not contain
        a 'Reference only' disclaimer banner.
        """
        block = _extract_tab_block(_load_source(), "SQL Equivalent")
        assert DISCLAIMER_TEXT not in block, (
            "An unexpected 'Reference only' disclaimer was found in the SQL Equivalent "
            "tab. Only Cypher and AQL tabs should carry this warning."
        )
