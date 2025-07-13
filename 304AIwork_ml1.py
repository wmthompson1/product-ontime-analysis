from sentence_transformers import SentenceTransformer, util
import psycopg2
import os

# Connect using connection string
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()

model = SentenceTransformer('all-MiniLM-L6-v2')
# template 304

query = "Canon digital camera"
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
    print(f"ID: {id_val}, Description: {description}, Distance: {distance:.6f}")
    print("")
