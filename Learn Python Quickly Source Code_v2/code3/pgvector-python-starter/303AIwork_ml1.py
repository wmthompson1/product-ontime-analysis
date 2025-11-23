"""
303AIwork_ml1.py
https://chatgpt.com/c/68730826-eefc-800b-9688-560f8e93931c
"""

from sentence_transformers import SentenceTransformer, util
import psycopg2
import os

from dotenv import load_dotenv

load_dotenv()

# Connect using db url
# conn = psycopg2.connect(os.getenv('DATABASE_URL'))

# Connect using paraeters
conn = psycopg2.connect(host=os.getenv("PGHOST"),
                        port=os.getenv("PGPORT"),
                        dbname=os.getenv("PGDATABASE"),
                        user=os.getenv("PGUSER"),
                        password=os.getenv("PGPASSWORD"))
cursor = conn.cursor()

model = SentenceTransformer('all-MiniLM-L6-v2')
# template 303 - insert products

cursor.execute("""
INSERT INTO products (description) VALUES
('Canon DSLR Rebel T7 Camera'),
('Canon T7 18MP Digital Camera'),
('Red Nike Air Max shoes'),
('Nike Air Max Sneakers, Red'),
('Apple Lightning USB cable'),
('iPhone charger cord');
""")

# Fetch descriptions
cursor.execute("SELECT id, description FROM products WHERE embedding IS NULL")
rows = cursor.fetchall()

# Generate embeddings
for row in rows:
    prod_id, desc = row
    embedding = model.encode(desc).tolist()
    cursor.execute("UPDATE products SET embedding = %s WHERE id = %s",
                   (embedding, prod_id))

conn.commit()
cursor.close()
conn.close()
