import psycopg2

# Connect to PostgreSQL
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="postgres",
    user="postgres",
    password="Delmont88"
)

cur = conn.cursor()

# Query example: list all tables
cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public';
""")

tables = cur.fetchall()
for table in tables:
    print(table[0])

cur.close()
conn.close()


