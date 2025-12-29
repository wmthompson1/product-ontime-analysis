# Median Time: 90 seconds 
 
import pandas as pd
import networkx as nx
 
# Read into Pandas 
pandas_edgelist = pd.read_csv(
    "cit-Patents.txt",
    skiprows=4,
    delimiter="\t",
    names=["src", "dst"],
    dtype={"src": "int32", "dst": "int32"},
)
 
# Create NetworkX Graph from Edgelist
G_nx = nx.from_pandas_edgelist(
    pandas_edgelist, source="src", target="dst", create_using=nx.DiGraph
)