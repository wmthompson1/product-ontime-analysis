"""
305AIwork_db1.py
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
# template 305 - db

#query = "Canon digital camera"
query = "bluetooth headphones"
query_vec = model.encode(query).tolist()

cursor.execute(
    """
    SELECT id, description, 1 - (embedding <=> %s::vector) AS similarity
    FROM products
    ORDER BY embedding <=> %s::vector
    LIMIT 5
""", (query_vec, query_vec))
matches = cursor.fetchall()
# need to render the matches
for match in matches:
    id_val, description, distance = match
    # Ensure distance is non-negative (handle floating-point precision issues)
    distance = max(0.0, distance)
    print("")
    print(
        f"ID: {id_val}, Description: {description}, Distance: {distance:.6f}")
    print("")
