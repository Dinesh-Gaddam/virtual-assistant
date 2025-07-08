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
from dotenv import load_dotenv
from recommender_engine import RecommenderEngine
from logging.handlers import TimedRotatingFileHandler

# Load environment variables
load_dotenv()

# Create logs directory if not exists
os.makedirs("logs", exist_ok=True)

# Setup logging
logger = logging.getLogger("recommendation_logger")
logger.setLevel(logging.INFO)
handler = TimedRotatingFileHandler("logs/server.log", when="midnight", interval=1, backupCount=7)
handler.suffix = "%Y-%m-%d"
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# Azure config
COSMOS_URI = os.getenv("COSMOS_URI")
COSMOS_KEY = os.getenv("COSMOS_KEY")
DATABASE_NAME = os.getenv("DATABASE_NAME")
BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING")
STORAGE_ACCOUNT_NAME = os.getenv("STORAGE_ACCOUNT_NAME")
STORAGE_ACCOUNT_KEY = os.getenv("STORAGE_ACCOUNT_KEY")
BLOB_BASE_URL = f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net"

# Clients
cosmos_client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
db = cosmos_client.get_database_client(DATABASE_NAME)
user_container = db.get_container_client("users")
wardrobe_container = db.get_container_client("wardrobe")
promoted_queries_container = db.get_container_client("promotedQueries")
blob_service = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)

app = FastAPI()

def generate_sas_url(user_id, image_name):
    expiry_time = datetime.utcnow() + timedelta(days=1)
    sas_token = generate_blob_sas(
        account_name=STORAGE_ACCOUNT_NAME,
        container_name=user_id,
        blob_name=image_name,
        account_key=STORAGE_ACCOUNT_KEY,
        permission=BlobSasPermissions(read=True),
        expiry=expiry_time
    )
    return f"{BLOB_BASE_URL}/{user_id}/{image_name}?{sas_token}"

def get_user_by_id(user_id: str):
    try:
        return user_container.read_item(item=user_id, partition_key=user_id)
    except:
        return None

@app.get("/profile/{first_name}/{last_name}")
async def get_user_profile(first_name: str, last_name: str):
    query = f"""
    SELECT * FROM users u 
    WHERE LOWER(u["first name"]) = '{first_name.lower()}' 
    AND LOWER(u["last name"]) = '{last_name.lower()}'
    """
    results = list(user_container.query_items(query=query, enable_cross_partition_query=True))
    if not results:
        logger.warning(f"User not found: {first_name} {last_name}")
        raise HTTPException(status_code=404, detail="User not found")
    user = results[0]
    user_id = user["id"]

    try:
        container_client = blob_service.get_container_client(user_id)
        blobs = container_client.list_blobs()
        image_urls = [
            generate_sas_url(user_id, blob.name) for blob in blobs
        ]
    except Exception as e:
        logger.error(f"❌ Error accessing blob storage for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Error accessing blob storage")

    logger.info(f"Profile fetched for user: {first_name} {last_name} (user_id: {user_id})")

    return {
        "user_id": user_id,
        "full_name": f"{user['first name']} {user['last name']}",
        "gender": user.get("gender", "Unspecified"),
        "ageRange": user.get("ageRange", "Unspecified"),
        "total_images": len(image_urls),
        "images": image_urls
    }

@app.get("/recommendation/{user_id}")
def get_recommendation(user_id: str, query: str = Query(..., description="Clothing request")):
    try:
        logger.info(f"[QUERY]  User: {user_id}, Query: '{query}'")

        user = get_user_by_id(user_id)
        if not user:
            logger.error(f"[ERROR] User not found: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")

        wardrobe_items = list(wardrobe_container.query_items(
            query="SELECT * FROM c WHERE c.user_id = @uid",
            parameters=[{"name": "@uid", "value": user_id}],
            enable_cross_partition_query=True
        ))
        if not wardrobe_items:
            logger.error(f"[ERROR] No wardrobe items found for user: {user_id}")
            raise HTTPException(status_code=404, detail="No wardrobe items found")

        # Prepare DataFrame using image IDs only
        df = pd.DataFrame([{
            "ImageName": item["id"].split("_", 1)[-1],   # e.g., 'F_1.jpg'
            "Caption": item.get("caption", ""),
            "Tags": [list(t.keys())[0] for t in item.get("tags", [])],
            "BlobName": item["id"]                       # actual blob name
        } for item in wardrobe_items])

        # Run recommendation engine
        engine = RecommenderEngine("imageconfig.json")
        engine.df = df
        recommendation_text = engine.get_dress_recommendation(query)

        if "Your query does not appear to be related to fashion" in recommendation_text:
            logger.info(f"[RESPONSE] Not fashion-related: {recommendation_text.strip()}")
            return recommendation_text

        logger.info(f"[RESPONSE] Recommendation generated:\n{recommendation_text.strip()}")

        lines = recommendation_text.strip().splitlines()[1:]

        results = []
        for line in lines:
            if not line.strip() or ":" not in line:
                continue
            match = re.search(r"\*\*(?:.*?\b)?([FM]_\d+)\b.*?\*\*", line)
            item = match.group(1) if match else None
            desc = line
            if item:
                results.append({"item": item, "description": desc})

        response_collection = []
        for r in results:
            # Find the matching row based on ImageName
            match_row = df[df["ImageName"] == r["item"]]
            if match_row.empty:
                continue

            blob_name = match_row["BlobName"].iloc[0]  # actual image ID = blob name
            image_url = generate_sas_url(user_id, blob_name)

            cleaned_description = re.sub(r"^\d+\.\s*\*\*(?:Item:\s*)?[FM]_\d+\*\*[:\-–]?\s*", "", r["description"]).strip()


            response_collection.append({
                "image_url": image_url,
                "description": cleaned_description
            })

        return response_collection

    except Exception as e:
        logger.error(f"[ERROR] Failed recommendation for user {user_id}: {str(e)}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
