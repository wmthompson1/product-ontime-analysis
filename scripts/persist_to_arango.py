#!/usr/bin/env python3
"""Persist the generated GraphML to ArangoDB using Entry Point 020 helper.

Reads env vars (DATABASE_HOST, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME)
so make sure to `source .env` (or export) before running.
"""
import os
import sys
from pathlib import Path
import logging
import traceback

GRAPHML_PATH = Path('data/schema_018.graphml')


def main():
    if not GRAPHML_PATH.exists():
        print(f'GraphML file not found: {GRAPHML_PATH}')
        sys.exit(2)

    # enable verbose logging for HTTP/requests and python-arango
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('urllib3').setLevel(logging.DEBUG)
    logging.getLogger('requests').setLevel(logging.DEBUG)

    # import nx_arangodb helper module (Entry Point 020)
    import importlib.util
    spec = importlib.util.spec_from_file_location('arango_entrypoint', '020_Entry_Point_ArangoDB_Graph_Persistence.py')
    arango_mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(arango_mod)
    except Exception:
        print('Failed to load Arango entry point module:')
        traceback.print_exc()
        sys.exit(3)

    try:
        # Ensure nx-arangodb is available
        import nx_arangodb  # noqa: F401
    except Exception:
        print('nx-arangodb not installed or import failed:')
        traceback.print_exc()
        print("Install it into the venv: ./.venv/bin/pip install nx-arangodb")
        sys.exit(4)

    import networkx as nx

    print('Loading GraphML:', GRAPHML_PATH)
    try:
        G = nx.read_graphml(str(GRAPHML_PATH))
    except Exception:
        print('Failed to read GraphML:')
        traceback.print_exc()
        sys.exit(5)

    print('Loaded graph:', G.number_of_nodes(), 'nodes,', G.number_of_edges(), 'edges')

    # Build ArangoDB config from env
    try:
        cfg = arango_mod.ArangoDBConfig()
        info = cfg.get_connection_info()
        print('Arango config:', info)
    except Exception:
        print('Failed to build ArangoDBConfig:')
        traceback.print_exc()
        sys.exit(6)

    try:
        persistence = arango_mod.ArangoDBGraphPersistence(cfg)
    except Exception:
        print('Failed to initialize ArangoDBGraphPersistence:')
        traceback.print_exc()
        sys.exit(7)

    name = os.environ.get('ARANGO_GRAPH_NAME', 'manufacturing_schema_v1')
    try:
        adb_graph = persistence.persist_graph(G, name=name, write_batch_size=10000, overwrite=True)
        print('Persisted graph to ArangoDB:', name)
    except Exception:
        print('Persist failed with exception:')
        traceback.print_exc()
        sys.exit(8)

    print('Done')


if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""Load data/schema_018.graphml and persist to ArangoDB using Entry Point 020 classes.

Requires environment variables for ArangoDB (DATABASE_HOST, DATABASE_USERNAME,
DATABASE_PASSWORD, DATABASE_NAME) to be set. Expects `data/schema_018.graphml` to exist.
"""
import os
import sys
from pathlib import Path
import importlib.util

try:
    import networkx as nx
except Exception as e:
    print('networkx not installed:', e)
    sys.exit(2)

ROOT = Path.cwd()
graphml = ROOT / 'data' / 'schema_018.graphml'
if not graphml.exists():
    print('GraphML not found:', graphml)
    sys.exit(2)

# Load the Arango persistence module by path
module_path = ROOT / '020_Entry_Point_ArangoDB_Graph_Persistence.py'
if not module_path.exists():
    print('Arango persistence module not found:', module_path)
    sys.exit(2)

spec = importlib.util.spec_from_file_location('arango_persist', str(module_path))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

if not getattr(mod, 'NXADB_AVAILABLE', False):
    print('nx-arangodb is not available. Please install: pip install nx-arangodb')
    sys.exit(2)

ArangoDBConfig = getattr(mod, 'ArangoDBConfig')
ArangoDBGraphPersistence = getattr(mod, 'ArangoDBGraphPersistence')

def main():
    print('Loading graphml...', graphml)
    G = nx.read_graphml(str(graphml))
    print(f'Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges')

    # Use env vars set in the shell (or .env loaded prior to running)
    config = ArangoDBConfig()
    info = config.get_connection_info()
    print('Using Arango config:', info)

    try:
        persistence = ArangoDBGraphPersistence(config)
    except Exception as e:
        print('Failed to initialize ArangoDBGraphPersistence:', e)
        sys.exit(2)

    try:
        adb = persistence.persist_graph(G, name='manufacturing_schema_v1', write_batch_size=10000, overwrite=True)
        print('Persist returned:', type(adb))
    except Exception as e:
        print('Persist failed:', e)
        sys.exit(2)

if __name__ == '__main__':
    main()
