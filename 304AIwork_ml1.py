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
    SELECT id, description, embedding <#> %s::vector AS distance
    FROM products
    ORDER BY distance ASC
    LIMIT 5
""", (query_vec, ))
matches = cursor.fetchall()
# need to render the matches
for match in matches:
    print(match)
    # print(match[1])
    # print(match[2])
    print("")
