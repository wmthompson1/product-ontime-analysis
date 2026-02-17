import os
import sqlglot
from sqlglot import exp
from arangodb_persistence import ArangoDBConfig, ArangoDBGraphPersistence

GRAPH_NAME = os.getenv("ARANGO_DB", "manufacturing_graph")
VERTEX_COLLECTION = f"{GRAPH_NAME}_node"
EDGE_COLLECTION = "SCHEMA_EDGE"

def project_solder_edges(model_sql, table_name, fk_map):
    """
    Parses a SQLMesh model AST and generates Column-Edges.
    f(x = table.column) -> {joins, intents, derivations}
    """
    tree = sqlglot.parse_one(model_sql)
    edges = []

    for expression in tree.find_all(exp.Alias):
        col_name = expression.alias
        source_col = expression.find(exp.Column).name

        target_key = f"{table_name}.{col_name}"
        if target_key in fk_map:
            to_node = f"table_{fk_map[target_key]['to_table']}"
            rel_type = "FOREIGN_KEY"
        else:
            to_node = f"concept_{col_name.upper()}"
            rel_type = "SEMANTIC_ATTRIBUTE"

        edges.append({
            "from": f"table_{table_name}",
            "to": to_node,
            "label": col_name,
            "relationship": rel_type,
            "derivation": f"AST_EXP: {expression.sql()}",
            "solder_type": "binary" if rel_type == "FOREIGN_KEY" else "semantic"
        })

    return edges

def main():
    config = ArangoDBConfig()
    persistence = ArangoDBGraphPersistence(config)

    fk_map = {
        "production_schedule.line_id": {"to_table": "production_lines", "type": "integer"},
    }

    sample_sql = """
    SELECT 
        schedule_id AS id, 
        line_id, 
        product_line, 
        scheduled_date 
    FROM raw.production_schedule
    """

    print(f"Projecting edges for table: production_schedule")
    new_edges = project_solder_edges(sample_sql, "production_schedule", fk_map)

    persistence.persist_from_dicts(
        name=GRAPH_NAME,
        nodes=[],
        edges=new_edges,
        vertex_collection=VERTEX_COLLECTION,
        edge_collection=EDGE_COLLECTION,
        overwrite=False
    )
    print(f"Successfully soldered {len(new_edges)} column-edges.")

if __name__ == "__main__":
    main()
