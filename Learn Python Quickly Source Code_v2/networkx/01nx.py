import networkx as nx
G = nx.Graph()
G.add_node(1)
G.add_nodes_from([2, 3])
G.add_edge(1, 2)
G.add_edges_from([(2, 3), (3, 1)])      
print("Nodes:", G.nodes())
print("Edges:", G.edges())
G.add_nodes_from([(4, {"color": "red"}), (5, {"color": "green"})])
print("Node 4 attributes:", G.nodes[4])
print("Node 5 attributes:", G.nodes[5])

