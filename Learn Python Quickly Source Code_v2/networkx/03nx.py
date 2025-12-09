import networkx as nx

# Create a graph
G = nx.Graph()

# Add nodes
G.add_nodes_from([1, 2, 3])

# Add edges
G.add_edges_from([(1, 2), (2, 3)])

G.add_node("spam")        # adds node "spam"
G.add_nodes_from("spam")  # adds 4 nodes: 's', 'p', 'a', 'm'
G.add_edge(2, 'm')



# Get the number of nodes
print(G.number_of_nodes())  # Output: ?
# Get the number of edges
print(G.number_of_edges())  # Output: 2
# Get the list of nodes
print(G.nodes())           # Output: [1, 2, 3, 'spam', 's', 'p', 'a', 'm']
# Get the list of edges 
print(G.edges())          # Output: [(1, 2), (2, 3), (2, 'm')]

print(G.adj[2])          # Output: AdjacencyView({1: {}, 3: {}, 'm': {}})
print(G.adj[2][1])       # Output: {}print(G.adj[2][3])       # Output: {}
print(G.adj[2]['m'])      # Output: {}
print(G[2])              # Output: AdjacencyView({1: {}, 3: {}, 'm': {}})
print(G[2][1])           # Output: {}
print(G[2][3])           # Output: {}print(G[2]['m'])         # Output: {}# Accessing neighbors of node 2
for neighbor in G.neighbors(2):
    print(neighbor)  # Output: 1, 3, 'm'
    # Accessing neighbors of node 2
for neighbor in G.neighbors(2):
    print(neighbor)  # Output: 1, 3, 'm'
print(list(G.nodes))  # Output: [1, 2, 3, 'spam', 's', 'p', 'a', 'm']

print(G.degree[1])  # the number of edges incident to 1
print(G.degree[2])  # the number of edges incident to 2
print(G.degree['m'])  # the number of some edges incident to 'spam'
