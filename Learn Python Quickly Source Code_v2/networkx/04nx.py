import networkx as nx
import matplotlib.pyplot as plt

# Create the Karate Club graph
G = nx.karate_club_graph()

# Choose a layout
pos = nx.spring_layout(G)  # Spring layout positions nodes for better visualization

# Draw the graph
nx.draw_networkx(G, pos, with_labels=True, node_color='lightblue', edge_color='gray', node_size=500, font_size=10)

# Display the graph
plt.show()