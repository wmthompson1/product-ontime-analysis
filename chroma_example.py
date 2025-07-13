
import chromadb
from sentence_transformers import SentenceTransformer

# Initialize ChromaDB (stores locally)
client = chromadb.Client()
collection = client.create_collection("products")

# Initialize model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Add documents
documents = [
    "High-quality wireless headphones with noise cancellation",
    "Canon T7 18MP Digital Camera",
    "Nike Air Max running shoes"
]

# Generate embeddings and add to collection
for i, doc in enumerate(documents):
    embedding = model.encode(doc).tolist()
    collection.add(
        embeddings=[embedding],
        documents=[doc],
        ids=[f"doc_{i}"]
    )

# Query
query = "bluetooth headphones"
query_embedding = model.encode(query).tolist()

results = collection.query(
    query_embeddings=[query_embedding],
    n_results=3
)

print("Results:", results['documents'][0])
