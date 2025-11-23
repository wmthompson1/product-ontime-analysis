from arango import ArangoClient
import os
from dotenv import load_dotenv


# Load environment variables from the .env file
load_dotenv(dotenv_path="/Users/williamthompson/bbb/20241019 Python/Learn Python Quickly Source Code_v2/code3/pgvector-python-starter/.env")

# Retrieve environment variables
database_host = os.environ["DATABASE_HOST"]
database_username = os.environ["DATABASE_USERNAME"]
database_password = os.environ["DATABASE_PASSWORD"]
database_name = os.environ["DATABASE_NAME"]

# Initialize the ArangoDB client
client = ArangoClient(hosts=database_host)

try:
    # Attempt to connect to the "_system" database
    sys_db = client.db(
        database_name,
        username=database_username,
        password=database_password
    )
    print("Connected to ArangoDB server!")

    # Create a new database
    new_database_name = "manufacturing_db"
    if not sys_db.has_database(new_database_name):
        sys_db.create_database(new_database_name)
        print(f"Database '{new_database_name}' created successfully!")
    else:
        print(f"Database '{new_database_name}' already exists.")
except Exception as e:
    print(f"Failed to connect to ArangoDB: {e}")