from arango import ArangoClient
import os
from dotenv import load_dotenv


# Load environment variables from the .env file
load_dotenv(dotenv_path="/Users/williamthompson/bbb/20241019 Python/Learn Python Quickly Source Code_v2/code3/pgvector-python-starter/.env")

# Retrieve environment variables
ARANGO_host = os.environ["ARANGO_HOST"]
ARANGO_username = os.environ["ARANGO_USER"]
ARANGO_password = os.environ["ARANGO_PASSWORD"]
ARANGO_name = os.environ["ARANGO_DB"]

# Initialize the ArangoDB client
client = ArangoClient(hosts=ARANGO_host)

try:
    # Attempt to connect to the "_system" database
    sys_db = client.db(
        ARANGO_name,
        username=ARANGO_username,
        password=ARANGO_password
    )
    print("Connected to ArangoDB server!")

    # Create a new database
    new_ARANGO_name = "manufacturing_db"
    if not sys_db.has_database(new_ARANGO_name):
        sys_db.create_database(new_ARANGO_name)
        print(f"Database '{new_ARANGO_name}' created successfully!")
    else:
        print(f"Database '{new_ARANGO_name}' already exists.")
except Exception as e:
    print(f"Failed to connect to ArangoDB: {e}")