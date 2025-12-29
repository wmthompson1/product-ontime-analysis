import psycopg2
from sentence_transformers import SentenceTransformer
import numpy as np

# --- DB CONFIG ---
conn = psycopg2.connect(
    dbname="postgres",
    user="williamthompson",       # <-- change this
    password="Delmont88",  # <-- change this
    host="localhost",
    port=5432
)
cursor = conn.cursor()

# --- PGVECTOR SETUP ---
cursor.execute("""
    CREATE EXTENSION IF NOT EXISTS vector;
    DROP TABLE IF EXISTS documents;
    CREATE TABLE documents (
        id SERIAL PRIMARY KEY,
        content TEXT,
        embedding vector(384)
    );
""")
conn.commit()

# --- EMBEDDING MODEL ---
model = SentenceTransformer('all-MiniLM-L6-v2')  # Embedding dim = 384

texts = [
    "The quick brown fox jumps over the lazy dog.",
    "A fox is a wild animal.",
    "Cats are great pets.",
    "PostgreSQL is a powerful database.",
    "Vector search enables similarity comparisons."
]

# --- INSERT EMBEDDINGS ---
for text in texts:
    vec = model.encode(text).tolist()
    cursor.execute(
        "INSERT INTO documents (content, embedding) VALUES (%s, %s)",
        (text, vec)
    )
conn.commit()

# --- SEARCH EXAMPLE ---
query = "What animal jumps over things?"
query_vec = model.encode(query).tolist()

cursor.execute("""
    SELECT id, content, embedding <#> %s AS distance
    FROM documents
    ORDER BY embedding <#> %s
    LIMIT 3
""", (query_vec, query_vec))

print("🔍 Top matches:")
for row in cursor.fetchall():
    print(f"• (score: {row[2]:.4f}) {row[1]}")

# --- Cleanup ---
cursor.close()
conn.close()
