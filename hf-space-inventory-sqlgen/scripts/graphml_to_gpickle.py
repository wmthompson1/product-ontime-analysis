#!/usr/bin/env python3
import networkx as nx
from pathlib import Path
import pickle
p = Path('data')
p.mkdir(exist_ok=True)
graphml = Path('data') / 'schema.graphml'
if not graphml.exists():
    raise FileNotFoundError(f'GraphML not found: {graphml}')
G = nx.read_graphml(str(graphml))
out = Path('data') / 'schema.gpickle'
with open(out, 'wb') as fh:
    pickle.dump(G, fh)
print('Wrote gpickle to', out)
