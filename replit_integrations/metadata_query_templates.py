#!/usr/bin/env python3
"""
metadata_query_templates.py — Pre-built SQL query library for manufacturing.db metadata.

Every function returns a plain SQL string (or a tuple of SQL string + params list).
Pass the return value directly to ``get_graph_metadata()`` in graph_metadata_queries.py.

All queries are read-only SELECTs against the semantic layer tables defined in
hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql.

Usage:
    from replit_integrations.graph_metadata_queries import get_graph_metadata
    from replit_integrations.metadata_query_templates import list_perspectives

    df = get_graph_metadata(list_perspectives())
"""


# =============================================================================
# PERSPECTIVE queries
# =============================================================================

def list_perspectives() -> str:
    """Return all rows from schema_perspectives ordered by perspective_id.

    Columns: perspective_id, perspective_name, description,
             stakeholder_role, priority_focus, created_at
    """
    return """
SELECT
    perspective_id,
    perspective_name,
    description,
    stakeholder_role,
    priority_focus,
    created_at
FROM schema_perspectives
ORDER BY perspective_id
""".strip()


def perspective_concept_map() -> str:
    """Return every perspective-concept relationship with concept details.

    Joins schema_perspective_concepts → schema_perspectives → schema_concepts.

    Columns: perspective_name, concept_name, concept_type, domain,
             relationship_type, priority_weight
    """
    return """
SELECT
    sp.perspective_name,
    sc.concept_name,
    sc.concept_type,
    sc.domain,
    spc.relationship_type,
    spc.priority_weight
FROM schema_perspective_concepts spc
JOIN schema_perspectives sp ON sp.perspective_id = spc.perspective_id
JOIN schema_concepts sc ON sc.concept_id = spc.concept_id
ORDER BY sp.perspective_name, spc.priority_weight DESC, sc.concept_name
""".strip()


def perspective_intent_weights() -> str:
    """Return perspective-intent activation weights (OPERATES_WITHIN relationships).

    Joins schema_intent_perspectives → schema_intents → schema_perspectives.

    Weight semantics: 1 = active path, 0 = neutral, -1 = suppressed.

    Columns: perspective_name, intent_name, intent_category,
             intent_factor_weight, explanation
    """
    return """
SELECT
    sp.perspective_name,
    si.intent_name,
    si.intent_category,
    sip.intent_factor_weight,
    sip.explanation
FROM schema_intent_perspectives sip
JOIN schema_intents si ON si.intent_id = sip.intent_id
JOIN schema_perspectives sp ON sp.perspective_id = sip.perspective_id
ORDER BY sp.perspective_name, si.intent_category, si.intent_name
""".strip()


# =============================================================================
# CONCEPT queries
# =============================================================================

def concept_hierarchy() -> str:
    """Return concepts with their parent concept (REFINES relationship).

    Self-join on schema_concepts.parent_concept_id.  Top-level concepts
    (no parent) appear with NULL in the parent_concept_name column.

    Columns: concept_id, concept_name, concept_type, domain,
             parent_concept_id, parent_concept_name
    """
    return """
SELECT
    c.concept_id,
    c.concept_name,
    c.concept_type,
    c.domain,
    c.parent_concept_id,
    p.concept_name AS parent_concept_name
FROM schema_concepts c
LEFT JOIN schema_concepts p ON p.concept_id = c.parent_concept_id
ORDER BY c.domain, c.concept_type, c.concept_name
""".strip()


def concept_field_mappings() -> str:
    """Return all field-to-concept mappings (CAN_MEAN relationships).

    Joins schema_concept_fields → schema_concepts.

    Columns: table_name, field_name, concept_name, concept_type, domain,
             is_primary_meaning, context_hint
    """
    return """
SELECT
    scf.table_name,
    scf.field_name,
    sc.concept_name,
    sc.concept_type,
    sc.domain,
    scf.is_primary_meaning,
    scf.context_hint
FROM schema_concept_fields scf
JOIN schema_concepts sc ON sc.concept_id = scf.concept_id
ORDER BY scf.table_name, scf.field_name, scf.is_primary_meaning DESC
""".strip()


def polymorphic_field_meanings(table_name: str, field_name: str) -> str:
    """Return all concept meanings registered for a specific table/field pair.

    A field is polymorphic when it has more than one concept row in
    schema_concept_fields — i.e. its value can be interpreted differently
    depending on the active perspective or intent.

    Args:
        table_name: ERP table name, e.g. ``'work_order'``.
        field_name: Column name within that table, e.g. ``'status'``.

    Returns:
        SQL string with ``?`` placeholders; pass ``[table_name, field_name]``
        as the ``params`` argument to ``get_graph_metadata()``.

    Columns: table_name, field_name, concept_name, concept_type, domain,
             is_primary_meaning, context_hint
    """
    return """
SELECT
    scf.table_name,
    scf.field_name,
    sc.concept_name,
    sc.concept_type,
    sc.domain,
    scf.is_primary_meaning,
    scf.context_hint
FROM schema_concept_fields scf
JOIN schema_concepts sc ON sc.concept_id = scf.concept_id
WHERE scf.table_name = ?
  AND scf.field_name = ?
ORDER BY scf.is_primary_meaning DESC, sc.concept_name
""".strip()


# =============================================================================
# INTENT queries
# =============================================================================

def intent_concept_elevations(intent_id: int) -> str:
    """Return concept weight activations for a specific intent.

    Weight semantics: 1 = elevated, 0 = neutral, -1 = suppressed.

    Args:
        intent_id: Integer primary key from schema_intents.

    Returns:
        SQL string with a single ``?`` placeholder; pass ``[intent_id]``
        as the ``params`` argument to ``get_graph_metadata()``.

    Columns: intent_name, intent_category, concept_name, concept_type,
             domain, intent_factor_weight, explanation
    """
    return """
SELECT
    si.intent_name,
    si.intent_category,
    sc.concept_name,
    sc.concept_type,
    sc.domain,
    sic.intent_factor_weight,
    sic.explanation
FROM schema_intent_concepts sic
JOIN schema_intents si ON si.intent_id = sic.intent_id
JOIN schema_concepts sc ON sc.concept_id = sic.concept_id
WHERE sic.intent_id = ?
ORDER BY sic.intent_factor_weight DESC, sc.concept_name
""".strip()


def intent_perspective_constraints(intent_id: int) -> str:
    """Return perspective constraints (OPERATES_WITHIN) for a specific intent.

    Args:
        intent_id: Integer primary key from schema_intents.

    Returns:
        SQL string with a single ``?`` placeholder; pass ``[intent_id]``
        as the ``params`` argument to ``get_graph_metadata()``.

    Columns: intent_name, perspective_name, stakeholder_role,
             intent_factor_weight, explanation
    """
    return """
SELECT
    si.intent_name,
    sp.perspective_name,
    sp.stakeholder_role,
    sip.intent_factor_weight,
    sip.explanation
FROM schema_intent_perspectives sip
JOIN schema_intents si ON si.intent_id = sip.intent_id
JOIN schema_perspectives sp ON sp.perspective_id = sip.perspective_id
WHERE sip.intent_id = ?
ORDER BY sip.intent_factor_weight DESC, sp.perspective_name
""".strip()


def intent_query_mappings() -> str:
    """Return all intent-to-ground-truth-query mappings.

    Joins schema_intent_queries → schema_intents.

    Columns: intent_name, intent_category, query_category, query_file,
             query_index, query_name
    """
    return """
SELECT
    si.intent_name,
    si.intent_category,
    siq.query_category,
    siq.query_file,
    siq.query_index,
    siq.query_name
FROM schema_intent_queries siq
JOIN schema_intents si ON si.intent_id = siq.intent_id
ORDER BY si.intent_category, si.intent_name, siq.query_index
""".strip()


# =============================================================================
# SCHEMA queries
# =============================================================================

def table_metadata() -> str:
    """Return all rows from schema_nodes (ERP table registry).

    Columns: table_name, table_type, description, created_at
    """
    return """
SELECT
    table_name,
    table_type,
    description,
    created_at
FROM schema_nodes
ORDER BY table_name
""".strip()


def column_metadata(table_name: str) -> str:
    """Return column descriptions for a specific table from api_field_descriptions.

    Args:
        table_name: ERP table name, e.g. ``'purchase_order'``.

    Returns:
        SQL string with a single ``?`` placeholder; pass ``[table_name]``
        as the ``params`` argument to ``get_graph_metadata()``.

    Columns: table_name, column_name, display_name, description, example_value
    """
    return """
SELECT
    table_name,
    column_name,
    display_name,
    description,
    example_value
FROM api_field_descriptions
WHERE table_name = ?
ORDER BY column_name
""".strip()


def foreign_key_graph() -> str:
    """Return all schema edges (foreign-key / join relationships) between tables.

    Columns: edge_id, from_table, to_table, relationship_type, join_column,
             weight, join_column_description, natural_language_alias
    """
    return """
SELECT
    edge_id,
    from_table,
    to_table,
    relationship_type,
    join_column,
    weight,
    join_column_description,
    natural_language_alias
FROM schema_edges
ORDER BY from_table, to_table
""".strip()


def foreign_key_edges_from_table(table_name: str) -> str:
    """Return schema edges where from_table or to_table matches the given table.

    Args:
        table_name: ERP table name, e.g. ``'work_order'``.

    Returns:
        SQL string with two ``?`` placeholders (same value repeated);
        pass ``[table_name, table_name]`` as the ``params`` argument.

    Columns: edge_id, from_table, to_table, relationship_type, join_column,
             weight, join_column_description, natural_language_alias
    """
    return """
SELECT
    edge_id,
    from_table,
    to_table,
    relationship_type,
    join_column,
    weight,
    join_column_description,
    natural_language_alias
FROM schema_edges
WHERE from_table = ?
   OR to_table   = ?
ORDER BY from_table, to_table
""".strip()


# =============================================================================
# COMPONENT queries
# =============================================================================

def polymorphic_components() -> str:
    """Return fields that carry more than one concept meaning (polymorphic fields).

    A field is considered polymorphic when schema_concept_fields contains at least
    two concept rows for the same (table_name, field_name) pair.

    Columns: table_name, field_name, meaning_count, concept_names
             (concept_names is a comma-separated list of concept names)
    """
    return """
SELECT
    scf.table_name,
    scf.field_name,
    COUNT(scf.concept_id)                                AS meaning_count,
    GROUP_CONCAT(sc.concept_name, ', ')                  AS concept_names
FROM schema_concept_fields scf
JOIN schema_concepts sc ON sc.concept_id = scf.concept_id
GROUP BY scf.table_name, scf.field_name
HAVING COUNT(scf.concept_id) > 1
ORDER BY meaning_count DESC, scf.table_name, scf.field_name
""".strip()


def binding_key_resolution(component_id: int) -> str:
    """Return column binding slots resolved for a given concept (component).

    Looks up column_bindings rows whose intent_name appears in intents that
    elevate the given concept_id (intent_factor_weight = 1).  This shows
    which physical table/column pairs the SolderEngine will activate when
    the specified concept is elevated.

    Args:
        component_id: concept_id from schema_concepts.

    Returns:
        SQL string with a single ``?`` placeholder; pass ``[component_id]``
        as the ``params`` argument to ``get_graph_metadata()``.

    Columns: concept_name, intent_name, slot_name, table_name, column_name
    """
    return """
SELECT
    sc.concept_name,
    cb.intent_name,
    cb.slot_name,
    cb.table_name,
    cb.column_name
FROM column_bindings cb
JOIN schema_intents si ON si.intent_name = cb.intent_name
JOIN schema_intent_concepts sic
    ON sic.intent_id = si.intent_id
   AND sic.intent_factor_weight = 1
JOIN schema_concepts sc ON sc.concept_id = sic.concept_id
WHERE sic.concept_id = ?
ORDER BY cb.intent_name, cb.slot_name
""".strip()
