from fastapi import FastAPI, HTTPException, Query
from azure.cosmos import CosmosClient
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

# Cosmos DB configuration
#COSMOS_URI = os.getenv("COSMOS_URI")
#COSMOS_KEY = os.getenv("COSMOS_KEY")
#DATABASE_NAME = os.getenv("DATABASE_NAME")

# Initialize Cosmos client
client = CosmosClient(COSMOS_URI, COSMOS_KEY)
database = client.get_database_client(DATABASE_NAME)
user_container = database.get_container_client("users")
query_container = database.get_container_client("promotedQueries")

@app.get("/")
def health_check():
    return {"status": "API is up and running"}

@app.get("/get-user-id")
def get_user_id_by_name(first_name: str = Query(...), last_name: str = Query(...)):
    query = f"""
        SELECT * FROM users u
        WHERE u."first name" = '{first_name}' AND u."last name" = '{last_name}'
    """
    users = list(user_container.query_items(query=query, enable_cross_partition_query=True))
    if not users:
        raise HTTPException(status_code=404, detail="User not found")
    return {"userId": users[0]["id"]}

@app.get("/user/{user_id}/latest-queries")
def get_latest_queries(user_id: str):
    query = f"""
        SELECT * FROM promotedQueries p
        WHERE p.userId = '{user_id}'
        ORDER BY p.createdAt DESC OFFSET 0 LIMIT 3
    """
    results = list(query_container.query_items(query=query, enable_cross_partition_query=True))
    return {"latestQueries": results}
