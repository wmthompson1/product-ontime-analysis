"""
Advanced Semantic Reasoning Module

Demonstrates 4 advanced patterns for semantic graph traversal:
1. Intent factor weight → query plan changes
2. Probabilistic intent resolution
3. Automatic intent inference from SQL shape
4. ArangoDB/Neo4j traversal syntax mapping
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import text
from dataclasses import dataclass


@dataclass
class QueryPlan:
    """Represents a semantic query plan with field interpretations"""
    intent: str
    perspective: str
    field_mappings: Dict[str, str]
    suppressed_concepts: List[str]
    elevated_concepts: List[str]
    suggested_joins: List[str]
    explanation: str


@dataclass
class IntentScore:
    """Probabilistic intent score"""
    intent_name: str
    confidence: float
    matched_concepts: List[str]
    matched_fields: List[str]
    explanation: str


def get_query_plan_by_intent(engine, table_name: str, field_name: str, intent_name: str) -> QueryPlan:
    """
    Feature 1: Show how intent_factor_weight changes query plans
    
    Demonstrates how different intents produce different SQL interpretations
    for the same field by following graph edges with weight filtering.
    """
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                i.intent_name,
                p.perspective_name,
                c.concept_name,
                c.description,
                ic.intent_factor_weight,
                ic.explanation
            FROM schema_concept_fields cf
            JOIN schema_concepts c ON cf.concept_id = c.concept_id
            JOIN schema_intent_concepts ic ON c.concept_id = ic.concept_id
            JOIN schema_intents i ON ic.intent_id = i.intent_id
            JOIN schema_intent_perspectives ip ON i.intent_id = ip.intent_id
            JOIN schema_perspectives p ON ip.perspective_id = p.perspective_id
            JOIN schema_perspective_concepts pc ON p.perspective_id = pc.perspective_id 
                AND c.concept_id = pc.concept_id
            WHERE cf.table_name = :table_name 
              AND cf.field_name = :field_name
              AND i.intent_name = :intent_name
              AND ip.intent_factor_weight = 1.0
        """), {"table_name": table_name, "field_name": field_name, "intent_name": intent_name})
        
        elevated = []
        suppressed = []
        field_mapping = None
        perspective = None
        
        for row in result.fetchall():
            perspective = row[1]
            if row[4] == 1.0:
                elevated.append(row[2])
                field_mapping = row[2]
            else:
                suppressed.append(row[2])
        
        result2 = conn.execute(text("""
            SELECT DISTINCT cf.table_name
            FROM schema_concept_fields cf
            JOIN schema_concepts c ON cf.concept_id = c.concept_id
            JOIN schema_intent_concepts ic ON c.concept_id = ic.concept_id
            WHERE ic.intent_id = (SELECT intent_id FROM schema_intents WHERE intent_name = :intent_name)
              AND ic.intent_factor_weight = 1.0
              AND cf.table_name != :table_name
        """), {"intent_name": intent_name, "table_name": table_name})
        
        suggested_joins = [r[0] for r in result2.fetchall()]
        
        return QueryPlan(
            intent=intent_name,
            perspective=perspective or "Unknown",
            field_mappings={f"{table_name}.{field_name}": field_mapping or "Unresolved"},
            suppressed_concepts=suppressed,
            elevated_concepts=elevated,
            suggested_joins=suggested_joins,
            explanation=f"Intent '{intent_name}' operates within '{perspective}' perspective, "
                       f"elevating {len(elevated)} concepts and suppressing {len(suppressed)}."
        )


def compare_query_plans(engine, table_name: str, field_name: str) -> List[Dict[str, Any]]:
    """
    Compare how different intents interpret the same field differently.
    Returns a list of query plans for all valid intents.
    """
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT i.intent_name
            FROM schema_intents i
            JOIN schema_intent_perspectives ip ON i.intent_id = ip.intent_id AND ip.intent_factor_weight = 1.0
            JOIN schema_perspective_concepts pc ON ip.perspective_id = pc.perspective_id
            JOIN schema_concept_fields cf ON pc.concept_id = cf.concept_id
            JOIN schema_intent_concepts ic ON i.intent_id = ic.intent_id 
                AND cf.concept_id = ic.concept_id AND ic.intent_factor_weight = 1.0
            WHERE cf.table_name = :table_name AND cf.field_name = :field_name
        """), {"table_name": table_name, "field_name": field_name})
        
        plans = []
        for row in result.fetchall():
            plan = get_query_plan_by_intent(engine, table_name, field_name, row[0])
            plans.append({
                "intent": plan.intent,
                "perspective": plan.perspective,
                "resolves_to": plan.field_mappings.get(f"{table_name}.{field_name}"),
                "elevated": plan.elevated_concepts,
                "suppressed": plan.suppressed_concepts,
                "suggested_joins": plan.suggested_joins
            })
        
        return plans


def resolve_intent_probabilistic(engine, fields: List[Tuple[str, str]]) -> List[IntentScore]:
    """
    Feature 2: Probabilistic intent resolution
    
    Given a list of (table_name, field_name) tuples, compute confidence scores
    for each intent based on how many fields it can semantically resolve.
    
    Confidence = (matched_fields / total_fields) * avg(intent_factor_weight)
    """
    with engine.connect() as conn:
        all_intents = conn.execute(text("""
            SELECT intent_id, intent_name, description FROM schema_intents
        """)).fetchall()
        
        scores = []
        
        for intent_id, intent_name, description in all_intents:
            matched_fields = []
            matched_concepts = []
            total_weight = 0.0
            
            for table_name, field_name in fields:
                result = conn.execute(text("""
                    SELECT c.concept_name, ic.intent_factor_weight
                    FROM schema_concept_fields cf
                    JOIN schema_concepts c ON cf.concept_id = c.concept_id
                    JOIN schema_intent_concepts ic ON c.concept_id = ic.concept_id
                    JOIN schema_intent_perspectives ip ON ic.intent_id = ip.intent_id
                    JOIN schema_perspective_concepts pc ON ip.perspective_id = pc.perspective_id 
                        AND c.concept_id = pc.concept_id
                    WHERE cf.table_name = :table_name 
                      AND cf.field_name = :field_name
                      AND ic.intent_id = :intent_id
                      AND ip.intent_factor_weight = 1.0
                      AND ic.intent_factor_weight = 1.0
                    LIMIT 1
                """), {"table_name": table_name, "field_name": field_name, "intent_id": intent_id})
                
                row = result.fetchone()
                if row:
                    matched_fields.append(f"{table_name}.{field_name}")
                    matched_concepts.append(row[0])
                    total_weight += row[1]
            
            if matched_fields:
                confidence = (len(matched_fields) / len(fields)) * (total_weight / len(matched_fields))
                scores.append(IntentScore(
                    intent_name=intent_name,
                    confidence=round(confidence, 3),
                    matched_concepts=matched_concepts,
                    matched_fields=matched_fields,
                    explanation=f"Matched {len(matched_fields)}/{len(fields)} fields with avg weight {total_weight/len(matched_fields):.2f}"
                ))
        
        return sorted(scores, key=lambda x: x.confidence, reverse=True)


def infer_intent_from_sql(engine, sql: str) -> List[IntentScore]:
    """
    Feature 3: Automatic intent inference from SQL shape
    
    Parse SQL to extract table.column references, then use probabilistic
    intent resolution to determine the most likely intent.
    
    Patterns detected:
    - Table names in FROM/JOIN clauses
    - Column references in SELECT/WHERE/GROUP BY
    - Aggregation patterns (COUNT, SUM, AVG)
    - Filter patterns (date ranges, status checks)
    """
    sql_upper = sql.upper()
    sql_clean = sql.lower()
    
    from_match = re.findall(r'\bFROM\s+(\w+)', sql, re.IGNORECASE)
    join_match = re.findall(r'\bJOIN\s+(\w+)', sql, re.IGNORECASE)
    tables = list(set(from_match + join_match))
    
    column_pattern = r'(\w+)\.(\w+)'
    column_refs = re.findall(column_pattern, sql)
    
    select_cols = re.findall(r'SELECT\s+(.+?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
    if select_cols:
        for match in re.findall(r'\b(\w+)\b', select_cols[0]):
            if match.upper() not in ('SELECT', 'AS', 'FROM', 'COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'DISTINCT'):
                for table in tables:
                    column_refs.append((table, match))
    
    fields = [(t.lower(), c.lower()) for t, c in column_refs if t.lower() in [tb.lower() for tb in tables]]
    
    if not fields:
        with engine.connect() as conn:
            for table in tables:
                result = conn.execute(text("""
                    SELECT DISTINCT table_name, field_name 
                    FROM schema_concept_fields 
                    WHERE table_name = :table_name
                """), {"table_name": table.lower()})
                for row in result.fetchall():
                    fields.append((row[0], row[1]))
    
    fields = list(set(fields))
    
    if not fields:
        return []
    
    scores = resolve_intent_probabilistic(engine, fields)
    
    for score in scores:
        if 'COUNT' in sql_upper or 'SUM' in sql_upper or 'AVG' in sql_upper:
            if 'analysis' in score.intent_name.lower() or 'trending' in score.intent_name.lower():
                score.confidence = min(1.0, score.confidence * 1.2)
                score.explanation += " [Boosted: aggregation detected]"
        
        if 'GROUP BY' in sql_upper:
            if 'trending' in score.intent_name.lower() or 'analysis' in score.intent_name.lower():
                score.confidence = min(1.0, score.confidence * 1.1)
                score.explanation += " [Boosted: grouping detected]"
        
        if 'supplier' in sql_clean:
            if 'supplier' in score.intent_name.lower():
                score.confidence = min(1.0, score.confidence * 1.3)
                score.explanation += " [Boosted: supplier context]"
        
        if 'defect' in sql_clean or 'quality' in sql_clean:
            if 'quality' in score.intent_name.lower() or 'defect' in score.intent_name.lower():
                score.confidence = min(1.0, score.confidence * 1.3)
                score.explanation += " [Boosted: quality context]"
    
    return sorted(scores, key=lambda x: x.confidence, reverse=True)


def get_cypher_traversal(intent_name: str, table_name: str, field_name: str) -> str:
    """
    Feature 4a: Neo4j Cypher traversal syntax
    
    Generate explicit Cypher query that follows the semantic path:
    (:Intent) -[:OPERATES_WITHIN]-> (:Perspective) -[:USES_DEFINITION]-> (:Concept) <-[:CAN_MEAN]- (:Field)
    """
    return f"""// Neo4j Cypher - Semantic Path Resolution
// Resolves: {table_name}.{field_name} under intent '{intent_name}'

MATCH path = (intent:Intent {{name: '{intent_name}'}})
  -[:OPERATES_WITHIN]->(perspective:Perspective)
  -[:USES_DEFINITION]->(concept:Concept)
  <-[:CAN_MEAN]-(field:Field {{table: '{table_name}', column: '{field_name}'}})
WHERE EXISTS {{
  MATCH (intent)-[e:ELEVATES]->(concept)
  WHERE e.weight = 1.0
}}
RETURN 
  intent.name AS Intent,
  perspective.name AS Perspective,
  concept.name AS ResolvedConcept,
  concept.description AS Meaning,
  field.table + '.' + field.column AS PhysicalField

// Alternative: Get all possible meanings with weights
MATCH (field:Field {{table: '{table_name}', column: '{field_name}'}})
  -[:CAN_MEAN]->(concept:Concept)
OPTIONAL MATCH (intent:Intent {{name: '{intent_name}'}})
  -[:ELEVATES]->(concept)
RETURN 
  concept.name AS Concept,
  COALESCE(intent.name, 'N/A') AS ElevatedBy,
  CASE WHEN intent IS NOT NULL THEN 1.0 ELSE 0.0 END AS Weight
ORDER BY Weight DESC
"""


def get_aql_traversal(intent_name: str, table_name: str, field_name: str) -> str:
    """
    Feature 4b: ArangoDB AQL traversal syntax
    
    Generate explicit AQL query for graph traversal using edge collections.
    """
    return f"""// ArangoDB AQL - Semantic Path Resolution
// Resolves: {table_name}.{field_name} under intent '{intent_name}'

// Find intent vertex
LET intent = FIRST(
  FOR i IN schema_intents
    FILTER i.intent_name == '{intent_name}'
    RETURN i
)

// Traverse: Intent -> Perspective -> Concept <- Field
FOR v, e, p IN 1..3 OUTBOUND intent
  GRAPH 'semantic_graph'
  OPTIONS {{bfs: true}}
  FILTER p.vertices[1]._id LIKE 'schema_perspectives/%'
  FILTER p.vertices[2]._id LIKE 'schema_concepts/%'
  
  // Join with field edge (reverse direction)
  LET field_edge = FIRST(
    FOR fe IN schema_concept_fields
      FILTER fe._to == p.vertices[2]._id
      FILTER fe.table_name == '{table_name}'
      FILTER fe.field_name == '{field_name}'
      RETURN fe
  )
  
  FILTER field_edge != null
  
  // Check elevation weight
  LET elevation = FIRST(
    FOR ic IN schema_intent_concepts
      FILTER ic._from == intent._id
      FILTER ic._to == p.vertices[2]._id
      FILTER ic.intent_factor_weight == 1.0
      RETURN ic
  )
  
  FILTER elevation != null
  
  RETURN {{
    intent: intent.intent_name,
    perspective: p.vertices[1].perspective_name,
    concept: p.vertices[2].concept_name,
    description: p.vertices[2].description,
    physical_field: CONCAT('{table_name}', '.', '{field_name}'),
    elevation_weight: elevation.intent_factor_weight
  }}

// Alternative: Shortest path query
FOR v, e IN OUTBOUND SHORTEST_PATH 
  'schema_intents/{intent_name}' TO 'schema_fields/{table_name}.{field_name}'
  GRAPH 'semantic_graph'
  RETURN {{vertex: v, edge: e}}
"""


def get_graph_syntax_examples(engine, intent_name: str, table_name: str, field_name: str) -> Dict[str, str]:
    """
    Return both Cypher and AQL examples for the given semantic path.
    """
    return {
        "cypher": get_cypher_traversal(intent_name, table_name, field_name),
        "aql": get_aql_traversal(intent_name, table_name, field_name),
        "sql_equivalent": f"""-- SQL Equivalent (current implementation)
SELECT 
    i.intent_name AS Intent,
    p.perspective_name AS Perspective,
    c.concept_name AS ResolvedConcept,
    c.description AS Meaning,
    '{table_name}.{field_name}' AS PhysicalField
FROM schema_concept_fields cf
JOIN schema_concepts c ON cf.concept_id = c.concept_id
JOIN schema_intent_concepts ic ON c.concept_id = ic.concept_id
JOIN schema_intents i ON ic.intent_id = i.intent_id
JOIN schema_intent_perspectives ip ON i.intent_id = ip.intent_id
JOIN schema_perspectives p ON ip.perspective_id = p.perspective_id
JOIN schema_perspective_concepts pc ON p.perspective_id = pc.perspective_id 
    AND c.concept_id = pc.concept_id
WHERE cf.table_name = '{table_name}' 
  AND cf.field_name = '{field_name}'
  AND i.intent_name = '{intent_name}'
  AND ip.intent_factor_weight = 1.0
  AND ic.intent_factor_weight = 1.0;
"""
    }
