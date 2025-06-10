from azure.cosmos import CosmosClient
from dotenv import load_dotenv
import os

load_dotenv()

# Environment variables
#COSMOS_URI = os.getenv("COSMOS_URI")
#COSMOS_KEY = os.getenv("COSMOS_KEY")
#DATABASE_NAME = os.getenv("DATABASE_NAME")

# Initialize Cosmos client
client = CosmosClient(COSMOS_URI, COSMOS_KEY)
database = client.get_database_client(DATABASE_NAME)
user_container = database.get_container_client("users")
query_container = database.get_container_client("promotedQueries")

# Function to get user by first and last name
def get_user_by_name(first_name, last_name):
    query = f"SELECT * FROM users u WHERE u.\"first name\" = '{first_name}' AND u.\"last name\" = '{last_name}'"
    users = list(user_container.query_items(query=query, enable_cross_partition_query=True))
    return users[0] if users else None

# Function to get latest 3 queries by userId
def get_latest_3_queries_by_userid(user_id):
    query = f"SELECT * FROM promotedQueries p WHERE p.userId = '{user_id}' ORDER BY p.createdAt DESC OFFSET 0 LIMIT 3"
    return list(query_container.query_items(query=query, enable_cross_partition_query=True))

# Test execution
first_name = "Rachel"
last_name = "Ong"

user = get_user_by_name(first_name, last_name)
if user:
    print(f"User found: {user['id']}")
    latest_queries = get_latest_3_queries_by_userid(user['id'])
    for q in latest_queries:
        print(f"- {q['query']}: {q['response']}")
else:
    print("User not found.")
