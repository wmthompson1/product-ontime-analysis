from sentence_transformers import SentenceTransformer, util
import psycopg2
import os

# Connect using connection string
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()

cursor.execute("""
CREATE EXTENSION IF NOT EXISTS vector;
""")
conn.commit()