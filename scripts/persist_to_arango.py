#!/usr/bin/env python3
"""Persist the generated GraphML to ArangoDB using Entry Point 020 helper.

Prefers ARANGO_* env vars (ARANGO_URL, ARANGO_USER, ARANGO_PASSWORD, ARANGO_DB)
but will accept older DATABASE_* names as fallbacks during migration.
Make sure to `source .env` (or export) before running.
"""
import os
import sys
from pathlib import Path
import logging
import traceback

GRAPHML_PATH = Path('data/schema_018.graphml')


def _normalize_arango_env():
    """Allow configuration via ARANGO_* env vars while keeping DATABASE_* fallbacks.

    This makes the script work with either the old `DATABASE_` names or newer
    `ARANGO_` names used in some hosts (Replit, etc.).
    """
    env = os.environ
    # Map ARANGO_* -> DATABASE_* if DATABASE_* not set
    if env.get('ARANGO_URL') and not env.get('DATABASE_HOST'):
        env['DATABASE_HOST'] = env.get('ARANGO_URL')
    if env.get('ARANGO_USER') and not env.get('DATABASE_USERNAME'):
        env['DATABASE_USERNAME'] = env.get('ARANGO_USER')
    if env.get('ARANGO_PASSWORD') and not env.get('DATABASE_PASSWORD'):
        env['DATABASE_PASSWORD'] = env.get('ARANGO_PASSWORD')
    if env.get('ARANGO_DB') and not env.get('DATABASE_NAME'):
        env['DATABASE_NAME'] = env.get('ARANGO_DB')
    # also support ARANGO_ROOT_PASSWORD as a source for DATABASE_PASSWORD
    if env.get('ARANGO_ROOT_PASSWORD') and not env.get('DATABASE_PASSWORD'):
        env['DATABASE_PASSWORD'] = env.get('ARANGO_ROOT_PASSWORD')


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

    # Ensure each node contains a 'table' attribute (used as collection/name)
    # GraphML nodes often use the node id as the table name; if attributes are empty,
    # copy the node identifier into the 'table' attribute so Arango documents retain
    # readable table names instead of numeric keys.
    for n in G.nodes():
        attrs = G.nodes[n]
        if not attrs.get('table') and not attrs.get('name'):
            attrs['table'] = str(n)
        # also set a friendly `name` property for UI display
        if not attrs.get('name'):
            attrs['name'] = str(n)

    # Ensure nodes have readable names/keys when persisted to ArangoDB.
    # nx-arangodb will auto-generate document keys if none are provided; to keep
    # table names visible in Arango we set a `_key` and `name` attribute for each node
    # when it's missing. `_key` must be URL-safe and unique per node.
    for n in list(G.nodes()):
        attrs = G.nodes[n]
        # set a human-friendly name if not present
        if not attrs.get('name'):
            attrs['name'] = str(n)
        # set document key to the node id (sanitized) if no explicit key present
        if not attrs.get('_key') and not attrs.get('key'):
            # sanitize key: replace slashes/spaces with underscore
            safe = str(n).replace('/', '_').replace(' ', '_')
            attrs['_key'] = safe
            # also set 'key' and 'label' to help nx-arangodb preserve names
            attrs['key'] = safe
            attrs['label'] = str(n)

    # Normalize env vars (allow ARANGO_* names) and build ArangoDB config from env
    try:
        _normalize_arango_env()
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

Requires environment variables for ArangoDB (prefer ARANGO_URL/ARANGO_USER/ARANGO_PASSWORD/ARANGO_DB)
to be set. DATABASE_* names are supported as fallbacks. Expects `data/schema_018.graphml` to exist.
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
    _normalize_arango_env()
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
