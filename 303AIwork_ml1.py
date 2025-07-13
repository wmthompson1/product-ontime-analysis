from sentence_transformers import SentenceTransformer, util
import psycopg2
import os

# Connect using connection string
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()


model = SentenceTransformer('all-MiniLM-L6-v2')
# template 303 

cursor.execute(
    """
INSERT INTO products (description) VALUES
('Canon DSLR Rebel T7 Camera'),
('Canon T7 18MP Digital Camera'),
('Red Nike Air Max shoes'),
('Nike Air Max Sneakers, Red'),
('Apple Lightning USB cable'),
('iPhone charger cord');
"""
)

    # Fetch descriptions
cursor.execute("SELECT id, description FROM products WHERE embedding IS NULL")
rows = cursor.fetchall()

# Generate embeddings
for row in rows:
    prod_id, desc = row
    embedding = model.encode(desc).tolist()
    cursor.execute("UPDATE products SET embedding = %s WHERE id = %s", (embedding, prod_id))

conn.commit()
cursor.close()
conn.close()

    
