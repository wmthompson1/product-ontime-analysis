from sentence_transformers import SentenceTransformer, util
import psycopg2
import os

# Connect using connection string
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()

cursor.execute("""
CREATE EXTENSION IF NOT EXISTS vector;
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    description TEXT NOT NULL,
    embedding vector(384)  -- For MiniLM
);
""")

conn.commit()

# Example: Insert a product with embedding
model = SentenceTransformer('all-MiniLM-L6-v2')

# Sample product
description = "High-quality wireless headphones with noise cancellation"
embedding = model.encode(description).tolist()

cursor.execute(
    """
INSERT INTO products (description, embedding) 
VALUES (%s, %s)
""", (description, embedding))

conn.commit()

# Example: Query similar products
query_text = "bluetooth headphones"
query_embedding = model.encode(query_text).tolist()

cursor.execute(
    """
SELECT id, description, 1 - (embedding <=> %s::vector) as similarity
FROM products 
ORDER BY embedding <=> %s::vector 
LIMIT 5;
""", (query_embedding, query_embedding))

results = cursor.fetchall()
for row in results:
  print(f"ID: {row[0]}, Description: {row[1]}, Similarity: {row[2]:.4f}")
