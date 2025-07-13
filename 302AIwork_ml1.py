"""
open my postgres database and run a query to first create extension then create table and then insert data into the table

"""

from sentence_transformers import SentenceTransformer, util
import psycopg2from sentence_transformers import SentenceTransformer, util

import psycopg2
import os

# Connect using individual parameters
conn = psycopg2.connect(
    host=os.getenv('PGHOST'),
    database=os.getenv('PGDATABASE'),
    user=os.getenv('PGUSER'),
    password=os.getenv('PGPASSWORD'),
    port=os.getenv('PGPORT')
)

# Or using connection string
conn = psycopg2.connect(os.getenv('DATABASE_URL'))

model = SentenceTransformer('all-MiniLM-L6-v2')

# Fetch descriptions
from db import cursor

cursor.execute(
CREATE EXTENSION IF NOT EXISTS vector;
)