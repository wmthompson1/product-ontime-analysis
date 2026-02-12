"""
ArangoDB Integration for SQLMesh

This module provides integration with ArangoDB for storing and querying
schema lineage graphs. It enables GitHub Copilot and other tools to query
table relationships, dependencies, and metadata from the graph database.

Configuration:
    Set environment variables or create a .env file:
    - DATABASE_HOST: ArangoDB host (default: http://127.0.0.1:8529)
    - DATABASE_USERNAME: Username (default: root)
    - DATABASE_PASSWORD: Password
    - DATABASE_NAME: Database name (default: manufacturing_graph)

Usage:
    from analysis.graph.arango_integration import ArangoLineageStore
    
    store = ArangoLineageStore()
    if store.connect():
        # Query table dependencies
        reports = store.query_table_dependencies("PAYABLE")
        
        # Query tables used by a file
        tables = store.query_file_dependencies("SQL_Reports/Finance/AP_Aging.sql")
"""

from typing import Dict, Any, List, Optional, Set, Tuple
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Check if python-arango is available
try:
    from arango import ArangoClient
    from arango.database import StandardDatabase
    from arango.exceptions import (
        DatabaseConnectError, 
        ServerConnectionError,
        DocumentGetError
    )
    ARANGO_AVAILABLE = True
except ImportError:
    ARANGO_AVAILABLE = False
    logger.warning("python-arango not available. Install with: pip install python-arango")


def load_dotenv_if_exists():
    """Load environment variables from .env file if it exists."""
    env_locations = [
        Path.cwd() / '.env',
        Path(__file__).parent.parent.parent / '.env',
        Path(__file__).parent.parent.parent.parent / '.env',
    ]
    
    for env_path in env_locations:
        if env_path.is_file():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        value = value.strip().strip('"').strip("'")
                        os.environ.setdefault(key.strip(), value)
            logger.debug(f"Loaded environment from {env_path}")
            return


class ArangoLineageStore:
    """
    ArangoDB lineage storage and query interface.
    
    Provides methods for querying schema relationships, table dependencies,
    and report-to-table mappings stored in ArangoDB.
    """
    
    def __init__(
        self, 
        host: Optional[str] = None,
        port: int = 8529,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize ArangoDB connection.
        
        Args:
            host: ArangoDB host (defaults to env DATABASE_HOST or localhost)
            port: ArangoDB port (default: 8529)
            database: Database name (defaults to env DATABASE_NAME or manufacturing_graph)
            username: Username (defaults to env DATABASE_USERNAME or root)
            password: Password (defaults to env DATABASE_PASSWORD)
        """
        if not ARANGO_AVAILABLE:
            self.enabled = False
            logger.error("❌ python-arango not installed. Install with: pip install python-arango")
            return
        
        # Load .env file if exists
        load_dotenv_if_exists()
        
        # Get connection parameters from args or environment
        self.host = host or os.getenv('DATABASE_HOST', 'http://127.0.0.1:8529')
        if not self.host.startswith('http'):
            self.host = f'http://{self.host}:{port}'
        
        self.database_name = database or os.getenv('DATABASE_NAME', 'manufacturing_graph')
        self.username = username or os.getenv('DATABASE_USERNAME', 'root')
        self.password = password or os.getenv('DATABASE_PASSWORD', '')
        
        self.client: Optional[ArangoClient] = None
        self.db: Optional[StandardDatabase] = None
        self.enabled = False
        
        logger.info(f"🔌 ArangoDB connection configured: {self.host} / {self.database_name}")
    
    def connect(self) -> bool:
        """
        Connect to ArangoDB database.
        
        Returns:
            True if connection successful, False otherwise
        """
        if not ARANGO_AVAILABLE:
            logger.error("❌ python-arango not available")
            return False
        
        try:
            self.client = ArangoClient(hosts=self.host)
            self.db = self.client.db(
                self.database_name,
                username=self.username,
                password=self.password
            )
            
            # Test connection by getting database name
            _ = self.db.name
            
            self.enabled = True
            logger.info(f"✅ Connected to ArangoDB: {self.database_name}")
            return True
            
        except (DatabaseConnectError, ServerConnectionError) as e:
            logger.error(f"❌ Failed to connect to ArangoDB: {e}")
            self.enabled = False
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error connecting to ArangoDB: {e}")
            self.enabled = False
            return False
    
    def create_collections(self):
        """Create necessary collections in ArangoDB if they don't exist."""
        if not self.enabled or not self.db:
            logger.warning("⚠️  Not connected to ArangoDB")
            return
        
        try:
            collections = {
                'tables': False,      # Document collection for schema tables
                'reports': False,     # Document collection for SQL reports
                'nodes': False,       # Generic node collection
                'dependencies': True, # Edge collection for report→table
                'edges': True,        # Generic edge collection
            }
            
            for col_name, is_edge in collections.items():
                if not self.db.has_collection(col_name):
                    self.db.create_collection(col_name, edge=is_edge)
                    logger.info(f"   ✅ Created collection: {col_name}")
            
            logger.info("✅ Collections verified/created")
            
        except Exception as e:
            logger.error(f"❌ Failed to create collections: {e}")
    
    def store_lineage_graph(self, graph_data: Dict[str, Any]):
        """
        Store lineage graph in ArangoDB (stub - use nx_to_arango.py instead).
        
        Args:
            graph_data: Graph data from NetworkX
        
        Note:
            For bulk graph persistence, use scripts/nx_to_arango.py instead.
            This method is reserved for future incremental updates.
        """
        logger.warning("⚠️  Use scripts/nx_to_arango.py for graph persistence")
        logger.info("   This method is for future incremental updates")
    
    def _normalize_table_key(self, table_name: str) -> str:
        """
        Normalize table name to ArangoDB key format.
        
        Args:
            table_name: Table name (e.g., 'PAYABLE', 'Live.dbo.PAYABLE')
            
        Returns:
            Normalized key (e.g., 'table_PAYABLE', 'table_Live_dbo_PAYABLE')
        """
        # Remove schema prefixes for matching
        clean_name = table_name.upper()
        if '.' in clean_name:
            parts = clean_name.split('.')
            clean_name = parts[-1]  # Get table name only
        
        # Create key pattern for matching
        return f"table_{clean_name}"
    
    def _normalize_report_key(self, file_path: str) -> str:
        """
        Normalize file path to ArangoDB key format.
        
        Args:
            file_path: File path (e.g., 'SQL_Reports/Finance/AP_Aging.sql')
            
        Returns:
            Normalized key pattern
        """
        # Replace path separators and special chars with underscores
        normalized = file_path.replace('\\', '_').replace('/', '_').replace('.', '_')
        return f"report_{normalized}"
    
    def query_table_dependencies(self, table_name: str) -> List[str]:
        """
        Query reports/files that depend on a table.
        
        Args:
            table_name: Name of the table (e.g., 'PAYABLE', 'Live.dbo.PAYABLE')
            
        Returns:
            List of file paths that reference this table
        """
        if not self.enabled or not self.db:
            logger.warning("⚠️  Not connected to ArangoDB")
            return []
        
        try:
            # Normalize table name for query
            table_key_pattern = self._normalize_table_key(table_name)
            
            # AQL query to find all reports that depend on this table
            aql = """
            FOR edge IN dependencies
                FILTER edge._to LIKE @table_pattern OR edge._to LIKE @table_pattern_alt
                LET report = DOCUMENT(edge._from)
                RETURN DISTINCT report.original_id
            """
            
            cursor = self.db.aql.execute(
                aql,
                bind_vars={
                    'table_pattern': f'%{table_key_pattern}%',
                    'table_pattern_alt': f'%{table_name.upper()}%'
                }
            )
            
            results = [r for r in cursor if r]
            logger.info(f"Found {len(results)} reports using table '{table_name}'")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to query table dependencies: {e}")
            return []
    
    def query_file_dependencies(self, file_path: str) -> List[str]:
        """
        Query tables used by a report/file.
        
        Args:
            file_path: Path to the file (e.g., 'SQL_Reports/Finance/AP_Aging.sql')
            
        Returns:
            List of table names used by this file
        """
        if not self.enabled or not self.db:
            logger.warning("⚠️  Not connected to ArangoDB")
            return []
        
        try:
            # Normalize file path for query
            report_key_pattern = self._normalize_report_key(file_path)
            
            # AQL query to find all tables used by this report
            aql = """
            FOR edge IN dependencies
                FILTER edge._from LIKE @report_pattern
                LET table = DOCUMENT(edge._to)
                RETURN DISTINCT table.original_id
            """
            
            cursor = self.db.aql.execute(
                aql,
                bind_vars={
                    'report_pattern': f'%{report_key_pattern}%'
                }
            )
            
            results = [r for r in cursor if r]
            logger.info(f"Found {len(results)} tables used by '{file_path}'")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to query file dependencies: {e}")
            return []
    
    def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a table from the graph.
        
        Args:
            table_name: Table name
            
        Returns:
            Dictionary with table metadata or None if not found
        """
        if not self.enabled or not self.db:
            logger.warning("⚠️  Not connected to ArangoDB")
            return None
        
        try:
            table_key_pattern = self._normalize_table_key(table_name)
            
            aql = """
            FOR doc IN tables
                FILTER doc._key LIKE @key_pattern OR doc.original_id LIKE @name_pattern
                LIMIT 1
                RETURN doc
            """
            
            cursor = self.db.aql.execute(
                aql,
                bind_vars={
                    'key_pattern': f'%{table_key_pattern}%',
                    'name_pattern': f'%{table_name.upper()}%'
                }
            )
            
            results = list(cursor)
            return results[0] if results else None
            
        except Exception as e:
            logger.error(f"❌ Failed to get table info: {e}")
            return None
    
    def search_tables(self, pattern: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for tables matching a pattern.
        
        Args:
            pattern: Search pattern (case-insensitive)
            limit: Maximum number of results
            
        Returns:
            List of matching table documents
        """
        if not self.enabled or not self.db:
            logger.warning("⚠️  Not connected to ArangoDB")
            return []
        
        try:
            aql = """
            FOR doc IN tables
                FILTER LOWER(doc.original_id) LIKE LOWER(@pattern)
                LIMIT @limit
                RETURN {
                    name: doc.original_id,
                    key: doc._key,
                    type: doc.type
                }
            """
            
            cursor = self.db.aql.execute(
                aql,
                bind_vars={
                    'pattern': f'%{pattern}%',
                    'limit': limit
                }
            )
            
            return list(cursor)
            
        except Exception as e:
            logger.error(f"❌ Failed to search tables: {e}")
            return []
    
    def get_downstream_tables(
        self, 
        table_name: str, 
        max_depth: int = 3
    ) -> List[Tuple[str, int]]:
        """
        Get tables that depend on the given table (downstream dependencies).
        
        Args:
            table_name: Starting table name
            max_depth: Maximum traversal depth
            
        Returns:
            List of (table_name, depth) tuples
        """
        if not self.enabled or not self.db:
            logger.warning("⚠️  Not connected to ArangoDB")
            return []
        
        try:
            table_key_pattern = self._normalize_table_key(table_name)
            
            aql = """
            FOR v, e, p IN 1..@max_depth OUTBOUND
                CONCAT('tables/', @table_key)
                GRAPH 'manufacturing_ground_truth_graph'
                FILTER v.type == 'table'
                RETURN {
                    table: v.original_id,
                    depth: LENGTH(p.edges)
                }
            """
            
            # Try to find the exact key first
            tables_col = self.db.collection('tables')
            matching_docs = []
            
            # Search for matching table
            for doc in tables_col:
                if table_key_pattern.lower() in doc.get('_key', '').lower():
                    matching_docs.append(doc)
            
            if not matching_docs:
                logger.info(f"No table found matching '{table_name}'")
                return []
            
            table_key = matching_docs[0]['_key']
            
            cursor = self.db.aql.execute(
                aql,
                bind_vars={
                    'table_key': table_key,
                    'max_depth': max_depth
                }
            )
            
            results = [(r['table'], r['depth']) for r in cursor]
            logger.info(f"Found {len(results)} downstream tables from '{table_name}'")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to get downstream tables: {e}")
            return []


# Convenience function for quick queries
def quick_query_table_deps(table_name: str) -> List[str]:
    """
    Quick function to query table dependencies without managing connection.
    
    Args:
        table_name: Table name to query
        
    Returns:
        List of file paths that depend on this table
    """
    store = ArangoLineageStore()
    if store.connect():
        return store.query_table_dependencies(table_name)
    return []


def quick_query_file_deps(file_path: str) -> List[str]:
    """
    Quick function to query file dependencies without managing connection.
    
    Args:
        file_path: File path to query
        
    Returns:
        List of table names used by this file
    """
    store = ArangoLineageStore()
    if store.connect():
        return store.query_file_dependencies(file_path)
    return []


# Example usage for testing
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🔍 ArangoDB Integration Test")
    print("=" * 60)
    
    store = ArangoLineageStore()
    
    if not store.connect():
        print("❌ Failed to connect to ArangoDB")
        print("   Make sure ArangoDB is running and credentials are set")
        sys.exit(1)
    
    # Test queries
    print("\n📊 Testing table dependency query...")
    reports = store.query_table_dependencies("PAYABLE")
    print(f"Reports using PAYABLE: {len(reports)}")
    for report in reports[:5]:
        print(f"  - {report}")
    
    print("\n📊 Testing table search...")
    tables = store.search_tables("PAY", limit=10)
    print(f"Tables matching 'PAY': {len(tables)}")
    for table in tables[:5]:
        print(f"  - {table.get('name', 'N/A')}")
    
    print("\n" + "=" * 60)
    print("✅ Test complete")
