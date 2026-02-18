"""
SolderEngine Extended — Graph-sourced Information Schema
=========================================================
Extends SolderEngine with get_information_schema() that pulls
table_name, column_name, primary_key, and foreign_key metadata
directly from the ArangoDB graph (not SQLite).

The information_schema output is a clean, self-contained list of dicts
independent of any solder routing functions.
"""

import os
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from arangodb_persistence import ArangoDBConfig, ArangoDBGraphPersistence
from solder_engine import SolderEngine

GRAPH_NAME = os.getenv("ARANGO_DB", "manufacturing_graph")
VERTEX_COLLECTION = f"{GRAPH_NAME}_node"

INFO_SCHEMA_AQL = '''
FOR col IN @@vertex_collection
    FILTER col.table_name == @target_table
       AND col.node_type == "atomic_column"

    LET fk_edges = (
        FOR v, e IN 1..1 OUTBOUND col._id GRAPH @graph_name
            FILTER e.is_foreign_key == true
            RETURN {
                references_table: v.table_name,
                references_column: v.column_name
            }
    )

    LET fk = FIRST(fk_edges)

    RETURN {
        table_name: col.table_name,
        column_name: col.column_name,
        data_type: col.data_type,
        is_primary_key: col.is_primary_key,
        is_foreign_key: LENGTH(fk_edges) > 0,
        references_table: fk != null ? fk.references_table : null,
        references_column: fk != null ? fk.references_column : null
    }
'''

FK_DEPENDENTS_AQL = '''
FOR col_target IN @@vertex_collection
    FILTER col_target._key == @target_key

    FOR v, e IN 1..1 INBOUND col_target._id GRAPH @graph_name
        FILTER e.is_foreign_key == true
        RETURN DISTINCT {
            table_name: v.table_name
        }
'''

ALL_TABLES_AQL = '''
FOR col IN @@vertex_collection
    FILTER col.node_type == "atomic_column"
    COLLECT table_name = col.table_name
    RETURN table_name
'''


@dataclass
class InformationSchemaColumn:
    table_name: str
    column_name: str
    data_type: str
    is_primary_key: bool
    is_foreign_key: bool
    references_table: Optional[str] = None
    references_column: Optional[str] = None


@dataclass
class InformationSchemaResult:
    table_name: str
    columns: List[InformationSchemaColumn]
    source: str = "arangodb_graph"

    @property
    def primary_keys(self) -> List[str]:
        return [c.column_name for c in self.columns if c.is_primary_key]

    @property
    def foreign_keys(self) -> List[Dict[str, str]]:
        return [
            {
                "column": c.column_name,
                "references_table": c.references_table,
                "references_column": c.references_column,
            }
            for c in self.columns
            if c.is_foreign_key
        ]

    def to_dicts(self) -> List[Dict[str, Any]]:
        return [
            {
                "table_name": c.table_name,
                "column_name": c.column_name,
                "data_type": c.data_type,
                "is_primary_key": c.is_primary_key,
                "is_foreign_key": c.is_foreign_key,
                "references_table": c.references_table,
                "references_column": c.references_column,
            }
            for c in self.columns
        ]


@dataclass
class JoinSchemaResult:
    tables: List[InformationSchemaResult]
    join_edges: List[Dict[str, str]]
    source: str = "arangodb_graph"

    def to_dicts(self) -> List[Dict[str, Any]]:
        rows = []
        for t in self.tables:
            rows.extend(t.to_dicts())
        return rows


class SolderEngineExtended(SolderEngine):

    def __init__(self, db_path: str = None, manifest_path: str = None):
        super().__init__(db_path=db_path, manifest_path=manifest_path)
        self._arango_db = None

    def _get_arango_db(self):
        if self._arango_db is None:
            config = ArangoDBConfig()
            persistence = ArangoDBGraphPersistence(config)
            self._arango_db = persistence._db
        return self._arango_db

    def get_information_schema(self, table_name: str) -> InformationSchemaResult:
        db = self._get_arango_db()
        rows = list(db.aql.execute(
            INFO_SCHEMA_AQL,
            bind_vars={
                "@vertex_collection": VERTEX_COLLECTION,
                "target_table": table_name,
                "graph_name": GRAPH_NAME,
            },
        ))

        columns = [
            InformationSchemaColumn(
                table_name=r["table_name"],
                column_name=r["column_name"],
                data_type=r["data_type"],
                is_primary_key=r["is_primary_key"],
                is_foreign_key=r["is_foreign_key"],
                references_table=r.get("references_table"),
                references_column=r.get("references_column"),
            )
            for r in rows
        ]

        return InformationSchemaResult(table_name=table_name, columns=columns)

    def get_fk_dependents(self, table_name: str, pk_column: str) -> List[str]:
        db = self._get_arango_db()
        target_key = f"{table_name}.{pk_column}"
        rows = list(db.aql.execute(
            FK_DEPENDENTS_AQL,
            bind_vars={
                "@vertex_collection": VERTEX_COLLECTION,
                "target_key": target_key,
                "graph_name": GRAPH_NAME,
            },
        ))
        return [r["table_name"] for r in rows]

    def get_join_schema(self, base_table: str) -> JoinSchemaResult:
        base_info = self.get_information_schema(base_table)

        join_edges = []
        related_tables = set()

        for fk in base_info.foreign_keys:
            related_tables.add(fk["references_table"])
            join_edges.append({
                "from_table": base_table,
                "from_column": fk["column"],
                "to_table": fk["references_table"],
                "to_column": fk["references_column"],
                "direction": "outbound",
            })

        for pk_col in base_info.primary_keys:
            dependents = self.get_fk_dependents(base_table, pk_col)
            for dep_table in dependents:
                if dep_table != base_table:
                    related_tables.add(dep_table)
                    dep_info = self.get_information_schema(dep_table)
                    for fk in dep_info.foreign_keys:
                        if fk["references_table"] == base_table and fk["references_column"] == pk_col:
                            join_edges.append({
                                "from_table": dep_table,
                                "from_column": fk["column"],
                                "to_table": base_table,
                                "to_column": pk_col,
                                "direction": "inbound",
                            })

        all_schemas = [base_info]
        for rel_table in sorted(related_tables):
            all_schemas.append(self.get_information_schema(rel_table))

        return JoinSchemaResult(tables=all_schemas, join_edges=join_edges)

    def get_raw_graph_nodes(self, table_name: str) -> List[Dict[str, Any]]:
        db = self._get_arango_db()
        rows = list(db.aql.execute(
            INFO_SCHEMA_AQL,
            bind_vars={
                "@vertex_collection": VERTEX_COLLECTION,
                "target_table": table_name,
                "graph_name": GRAPH_NAME,
            },
        ))
        return rows

    def get_raw_graph_edges(self, table_name: str, pk_column: str) -> List[Dict[str, Any]]:
        db = self._get_arango_db()
        target_key = f"{table_name}.{pk_column}"
        rows = list(db.aql.execute(
            FK_DEPENDENTS_AQL,
            bind_vars={
                "@vertex_collection": VERTEX_COLLECTION,
                "target_key": target_key,
                "graph_name": GRAPH_NAME,
            },
        ))
        return rows

    def get_available_tables(self) -> List[str]:
        db = self._get_arango_db()
        rows = list(db.aql.execute(
            ALL_TABLES_AQL,
            bind_vars={"@vertex_collection": VERTEX_COLLECTION},
        ))
        return sorted(rows)
