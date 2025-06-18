import logging
from fastapi import FastAPI, HTTPException
from azure.cosmos import CosmosClient
from azure.storage.blob import (
    BlobServiceClient,
    generate_blob_sas,
    BlobSasPermissions
)
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Azure config
COSMOS_URI = os.getenv("COSMOS_URI")
COSMOS_KEY = os.getenv("COSMOS_KEY")
DATABASE_NAME = os.getenv("DATABASE_NAME")
BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING")

# FastAPI App
app = FastAPI()

# Cosmos DB clients
cosmos_client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
db = cosmos_client.get_database_client(DATABASE_NAME)
user_container = db.get_container_client("users")
wardrobe_container = db.get_container_client("wardrobe")

# Blob client
blob_service = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)

# Generate SAS URL for a blob
def generate_sas_url(container_name: str, blob_name: str) -> str:
    sas_token = generate_blob_sas(
        account_name=blob_service.account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=blob_service.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(minutes=30)
    )
    return f"https://{blob_service.account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"

# Find user by name
def get_user_by_name(first_name: str, last_name: str):
    query = f"""
    SELECT * FROM users u 
    WHERE LOWER(u["first name"]) = '{first_name.lower()}' 
    AND LOWER(u["last name"]) = '{last_name.lower()}'
    """
    results = list(user_container.query_items(query=query, enable_cross_partition_query=True))
    return results[0] if results else None

# Endpoint: Get wardrobe data for user
@app.get("/profile/{first_name}/{last_name}")
async def get_user_profile(first_name: str, last_name: str):
    logger.info(f"➡️ Request received for user: {first_name} {last_name}")

    # Step 1: Find user
    user = get_user_by_name(first_name, last_name)
    if not user:
        logger.warning(f"❌ User not found: {first_name} {last_name}")
        raise HTTPException(status_code=404, detail="User not found")

    user_id = user["id"]
    logger.info(f"✅ Found user_id: {user_id}")

    # Step 2: Fetch wardrobe entries for this user
    query = f"""
    SELECT c.image_id, c.image_url, c.tags FROM wardrobe c 
    WHERE c.user_id = @user_id
    """
    results = list(wardrobe_container.query_items(
        query=query,
        parameters=[{"name": "@user_id", "value": user_id}],
        enable_cross_partition_query=True
    ))

    # Step 3: Format response
    response_payload = {
        "user_id": user_id,
        "full_name": f"{user['first name']} {user['last name']}",
        "gender": user.get("gender", "Unspecified"),
        "ageRange": user.get("ageRange", "Unspecified"),
        "total_images": len(results),
        "wardrobe": results
    }

    logger.info(f"✅ Responding with {len(results)} wardrobe items for {user_id}")
    return response_payload
