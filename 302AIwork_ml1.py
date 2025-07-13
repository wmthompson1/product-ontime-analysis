from sentence_transformers import SentenceTransformer, util
import psycopg2from sentence_transformers import SentenceTransformer, util

import psycopg2
import os

# Connect using individual parameters
conn = psycopg2.connect(
    host=os.getenv('PGHOST'),
    database=os.getenv('PGDATABASE'),
    user=os.getenv('PGUSER'),
    password=os.getenv('PGPASSWORD'),
    port=os.getenv('PGPORT')
)

# Or using connection string
conn = psycopg2.connect(os.getenv('DATABASE_URL'))

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