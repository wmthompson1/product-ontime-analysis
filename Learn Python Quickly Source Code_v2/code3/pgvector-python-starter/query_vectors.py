import os
import psycopg2
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("PGHOST"),
    port=os.getenv("PGPORT"),
    dbname=os.getenv("PGDATABASE"),
    user=os.getenv("PGUSER"),
    password=os.getenv("PGPASSWORD")
)
cursor = conn.cursor()

model = SentenceTransformer('all-MiniLM-L6-v2')
query = "Animals that jump"
query_vec = model.encode(query).tolist()

cursor.execute("""
    SELECT content, embedding <#> %s::vector AS similarity
    FROM documents
    ORDER BY embedding <#> %s::vector
    LIMIT 3
""", (query_vec, query_vec))

print("🔍 Top matches:")
for row in cursor.fetchall():
    print(f"• (distance: {row[1]:.4f}) {row[0]}")

cursor.close()
conn.close()
