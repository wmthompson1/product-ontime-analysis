#!/usr/bin/env python3
"""
Lightweight in-memory directed graph shim to replace NetworkX for CI.

Provides SimpleDiGraph with the subset of nx.DiGraph methods used by
the manufacturing semantic-layer pipeline.  No external dependencies.
"""

from collections import deque
from typing import Any, Dict, Iterator, List, Optional, Tuple


class SimpleDiGraph:
    """Lightweight in-memory directed graph shim to replace NetworkX for CI."""

    def __init__(self):
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._edges: List[Tuple[str, str, Dict[str, Any]]] = []
        self._adj: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._pred: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def add_node(self, node, **attrs):
        self._nodes[node] = attrs
        self._adj.setdefault(node, {})
        self._pred.setdefault(node, {})

    def add_edge(self, u, v, **attrs):
        if u not in self._nodes:
            self.add_node(u)
        if v not in self._nodes:
            self.add_node(v)
        self._edges.append((u, v, attrs))
        self._adj[u][v] = attrs
        self._pred[v][u] = attrs

    def nodes(self, data=True):
        for n, a in self._nodes.items():
            yield (n, a) if data else n

    def edges(self, data=True):
        for u, v, a in self._edges:
            yield (u, v, a) if data else (u, v)

    def number_of_nodes(self) -> int:
        return len(self._nodes)

    def number_of_edges(self) -> int:
        return len(self._edges)

    def has_node(self, node) -> bool:
        return node in self._nodes

    def successors(self, node) -> Iterator[str]:
        return iter(self._adj.get(node, {}))

    def predecessors(self, node) -> Iterator[str]:
        return iter(self._pred.get(node, {}))

    def degree(self, node=None):
        if node is not None:
            return len(self._adj.get(node, {})) + len(self._pred.get(node, {}))
        return [(n, len(self._adj.get(n, {})) + len(self._pred.get(n, {})))
                for n in self._nodes]

    def is_directed(self) -> bool:
        return True

    def to_undirected(self) -> "SimpleGraph":
        g = SimpleGraph()
        for n, a in self._nodes.items():
            g.add_node(n, **a)
        for u, v, a in self._edges:
            g.add_edge(u, v, **a)
        return g


class SimpleGraph:
    """Lightweight undirected graph shim."""

    def __init__(self):
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._edges: List[Tuple[str, str, Dict[str, Any]]] = []
        self._adj: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def add_node(self, node, **attrs):
        self._nodes[node] = attrs
        self._adj.setdefault(node, {})

    def add_edge(self, u, v, **attrs):
        if u not in self._nodes:
            self.add_node(u)
        if v not in self._nodes:
            self.add_node(v)
        self._edges.append((u, v, attrs))
        self._adj[u][v] = attrs
        self._adj[v][u] = attrs

    def nodes(self, data=True):
        for n, a in self._nodes.items():
            yield (n, a) if data else n

    def edges(self, data=True):
        for u, v, a in self._edges:
            yield (u, v, a) if data else (u, v)

    def number_of_nodes(self) -> int:
        return len(self._nodes)

    def number_of_edges(self) -> int:
        return len(self._edges)

    def has_node(self, node) -> bool:
        return node in self._nodes

    def is_directed(self) -> bool:
        return False


class NodeNotFound(Exception):
    """Raised when a node is not in the graph."""
    pass


class NetworkXNoPath(Exception):
    """Raised when no path exists between two nodes."""
    pass


def shortest_path(graph, source, target):
    """BFS shortest path (unweighted)."""
    if not graph.has_node(source):
        raise NodeNotFound(f"Node '{source}' not found")
    if not graph.has_node(target):
        raise NodeNotFound(f"Node '{target}' not found")

    visited = {source}
    queue = deque([(source, [source])])
    adj = graph._adj

    while queue:
        node, path = queue.popleft()
        if node == target:
            return path
        for neighbor in adj.get(node, {}):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))

    raise NetworkXNoPath(f"No path between '{source}' and '{target}'")


def density(graph) -> float:
    """Graph density."""
    n = graph.number_of_nodes()
    if n < 2:
        return 0.0
    m = graph.number_of_edges()
    if graph.is_directed():
        return m / (n * (n - 1))
    return 2.0 * m / (n * (n - 1))


def degree_centrality(graph) -> Dict[str, float]:
    """Degree centrality for each node."""
    n = graph.number_of_nodes()
    if n <= 1:
        return {nd: 0.0 for nd in graph._nodes}
    deg = graph.degree()
    if isinstance(deg, list):
        return {nd: d / (n - 1) for nd, d in deg}
    return {}


def number_connected_components(graph) -> int:
    """Count connected components (undirected)."""
    visited = set()
    count = 0
    for node in graph._nodes:
        if node not in visited:
            count += 1
            queue = deque([node])
            while queue:
                n = queue.popleft()
                if n in visited:
                    continue
                visited.add(n)
                for neighbor in graph._adj.get(n, {}):
                    if neighbor not in visited:
                        queue.append(neighbor)
    return count
