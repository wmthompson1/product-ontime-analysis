from sentence_transformers import SentenceTransformer, util
import psycopg2from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer('all-MiniLM-L6-v2')

# Fetch descriptions
cur.execute("SELECT id, description FROM products")
rows = cur.fetchall()

# Compute embeddings
descriptions = [r[1] for r in rows]
embeddings = model.encode(descriptions, convert_to_tensor=True)

# Find matches (e.g., via cosine similarity)
similarities = util.pytorch_cos_sim(embeddings, embeddings)

# Post-process to cluster or associate products with inferred SKU group
🔧