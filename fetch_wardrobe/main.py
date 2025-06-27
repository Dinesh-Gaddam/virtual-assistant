<<<<<<< HEAD
import os
import re
import traceback
import logging
import pandas as pd
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Query
from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta
from recommender_engine import RecommenderEngine
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logging setup
=======
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
>>>>>>> 62de66664f6184027c959efb493cb4ad79f21ab6
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs.log"),
        logging.StreamHandler()
    ]
)
<<<<<<< HEAD
logger = logging.getLogger(_name_)

# Azure configuration
=======
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Azure config
>>>>>>> 62de66664f6184027c959efb493cb4ad79f21ab6
COSMOS_URI = os.getenv("COSMOS_URI")
COSMOS_KEY = os.getenv("COSMOS_KEY")
DATABASE_NAME = os.getenv("DATABASE_NAME")
BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING")

<<<<<<< HEAD
# Clients
=======
# FastAPI App
app = FastAPI()

# Cosmos DB clients
>>>>>>> 62de66664f6184027c959efb493cb4ad79f21ab6
cosmos_client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
db = cosmos_client.get_database_client(DATABASE_NAME)
user_container = db.get_container_client("users")
wardrobe_container = db.get_container_client("wardrobe")
<<<<<<< HEAD
promoted_queries_container = db.get_container_client("promotedQueries")
blob_service = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)

# FastAPI app
app = FastAPI()

# SAS URL generator
=======

# Blob client
blob_service = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)

# Generate SAS URL for a blob
>>>>>>> 62de66664f6184027c959efb493cb4ad79f21ab6
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

<<<<<<< HEAD
# Get user by name
=======
# Find user by name
>>>>>>> 62de66664f6184027c959efb493cb4ad79f21ab6
def get_user_by_name(first_name: str, last_name: str):
    query = f"""
    SELECT * FROM users u 
    WHERE LOWER(u["first name"]) = '{first_name.lower()}' 
    AND LOWER(u["last name"]) = '{last_name.lower()}'
    """
    results = list(user_container.query_items(query=query, enable_cross_partition_query=True))
    return results[0] if results else None

<<<<<<< HEAD
@app.get("/profile/{first_name}/{last_name}")
async def get_user_profile(first_name: str, last_name: str):
    logger.info(f"➡ Request received for user: {first_name} {last_name}")
=======
# Endpoint: Get wardrobe data for user
@app.get("/profile/{first_name}/{last_name}")
async def get_user_profile(first_name: str, last_name: str):
    logger.info(f"➡️ Request received for user: {first_name} {last_name}")

    # Step 1: Find user
>>>>>>> 62de66664f6184027c959efb493cb4ad79f21ab6
    user = get_user_by_name(first_name, last_name)
    if not user:
        logger.warning(f"❌ User not found: {first_name} {last_name}")
        raise HTTPException(status_code=404, detail="User not found")

    user_id = user["id"]
    logger.info(f"✅ Found user_id: {user_id}")

<<<<<<< HEAD
    query = """
=======
    # Step 2: Fetch wardrobe entries for this user
    query = f"""
>>>>>>> 62de66664f6184027c959efb493cb4ad79f21ab6
    SELECT c.image_id, c.image_url, c.tags FROM wardrobe c 
    WHERE c.user_id = @user_id
    """
    results = list(wardrobe_container.query_items(
        query=query,
        parameters=[{"name": "@user_id", "value": user_id}],
        enable_cross_partition_query=True
    ))

<<<<<<< HEAD
    return {
=======
    # Step 3: Format response
    response_payload = {
>>>>>>> 62de66664f6184027c959efb493cb4ad79f21ab6
        "user_id": user_id,
        "full_name": f"{user['first name']} {user['last name']}",
        "gender": user.get("gender", "Unspecified"),
        "ageRange": user.get("ageRange", "Unspecified"),
        "total_images": len(results),
        "wardrobe": results
    }

<<<<<<< HEAD
@app.get("/recommendation/{user_id}")
def get_recommendation(user_id: str, query: str = Query(..., description="Clothing request")):
    try:
        # 1. Get user details
        user = user_container.read_item(item=user_id, partition_key=user_id)
        gender = user.get("gender", "").lower()

        # 2. Load appropriate tag file
        engine = RecommenderEngine("imageconfig.json")
        #if gender == "male":
            #df = engine.load_tagged_data(r"C:\Users\likit\virtual-assistant\images\American\resized_images\men\Orginal_Men_Tags")
        #elif gender == "female":
            #df = engine.load_tagged_data(r"C:\Users\likit\virtual-assistant\images\American\resized_images\women\Women_Original_Tags")
        #else:
            #raise HTTPException(status_code=400, detail="Unsupported or missing gender")
            #pull data from wardrobe tags 
        engine.df = df

        # 3. Generate recommendation
        recommendation_text = engine.get_dress_recommendation(query)
        #image_ids = re.findall(r"([A-Z] ?\d+\.jpg)", recommendation_text)
        #image_ids = [img.strip() for img in image_ids]

        results = []
        for img in image_ids:
            row = df[df["ImageName"] == img]
            if not row.empty:
                results.append({
                    "image_id": img,
                    "description": row.iloc[0]["Caption"],
                    "tags": row.iloc[0]["Tags"]
                })

        # 4. Create sequential query ID like user2_query1
        count_query = f"SELECT VALUE COUNT(1) FROM c WHERE c.userId = @uid"
        count_result = list(promoted_queries_container.query_items(
            query=count_query,
            parameters=[{"name": "@uid", "value": user_id}],
            enable_cross_partition_query=True
        ))
        query_number = (count_result[0] if count_result else 0) + 1
        query_id = f"{user_id}_query{query_number}"

        # 5. Store query record
        promoted_queries_container.create_item(body={
            "id": query_id,
            "userId": user_id,
            "query": query,
            "responses": [r["description"] for r in results],
            "createdAt": datetime.utcnow().isoformat()
        })

        return {
            "user_id": user_id,
            "query_id": query_id,
            "query": query,
            "recommendations": results
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
=======
    logger.info(f"✅ Responding with {len(results)} wardrobe items for {user_id}")
    return response_payload
>>>>>>> 62de66664f6184027c959efb493cb4ad79f21ab6
