# Median Time: 3 Minutes 
import pandas as pd
import networkx as nx
 
import os
import nx_arangodb as nxadb

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
 
os.environ["DATABASE_HOST"] = "http://127.0.0.1:8529"
os.environ["DATABASE_USERNAME"] = "root"
os.environ["DATABASE_PASSWORD"] = "Delmont88"
os.environ["DATABASE_NAME"] = "mfg" 
 
# Load the DiGraph into ArangoDB 
G_nxadb = nxadb.DiGraph(
    name="cit_patents",
    incoming_graph_data=G_nx,
    write_batch_size=50000
)