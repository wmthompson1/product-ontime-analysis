from dotenv import load_dotenv
import os

# Load environment variables from the .env file
#load_dotenv()
load_dotenv(dotenv_path="/Users/williamthompson/bbb/20241019 Python/Learn Python Quickly Source Code_v2/code3/pgvector-python-starter/.env")

# Access environment variables
database_host = os.getenv("DATABASE_HOST")
database_username = os.getenv("DATABASE_USERNAME")
database_password = os.getenv("DATABASE_PASSWORD")
database_name = os.getenv("DATABASE_NAME")

print("Database Host:", database_host)
print("Database Username:", database_username)
print("Database Name:", database_name)