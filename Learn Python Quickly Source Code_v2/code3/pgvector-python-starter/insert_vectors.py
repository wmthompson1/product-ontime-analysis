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
texts = [
    'Canon DSLR Rebel T7 Camera',
    'Canon T7 18MP Digital Camera',
    'Red Nike Air Max shoes',
    'Nike Air Max Sneakers, Red',
    'Apple Lightning USB cable',
    'iPhone charger cord'
]

for text in texts:
    vec = model.encode(text).tolist()
    cursor.execute(
        "INSERT INTO documents (content, embedding) VALUES (%s, %s)", (text, vec)
    )

conn.commit()
cursor.close()
conn.close()
print("✅ Inserted embeddings.")
