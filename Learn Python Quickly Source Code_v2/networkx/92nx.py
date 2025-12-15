from dotenv import load_dotenv
import os

# Load environment variables from the .env file
#load_dotenv()
load_dotenv(dotenv_path="/Users/williamthompson/bbb/20241019 Python/Learn Python Quickly Source Code_v2/code3/pgvector-python-starter/.env")

# Access environment variables
ARANGO_host = os.getenv("DATABASE_HOST")
ARANGO_username = os.getenv("DATABASE_USERNAME")
ARANGO_password = os.getenv("DATABASE_PASSWORD")
ARANGO_name = os.getenv("DATABASE_NAME")

print("Database Host:", ARANGO_host)
print("Database Username:", ARANGO_username)
print("Database Name:", ARANGO_name)