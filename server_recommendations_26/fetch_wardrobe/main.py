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

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

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

def generate_sas_url(container_name: str, blob_name: str) -> str:
    sas_token = generate_blob_sas(
        account_name=blob_service.account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=blob_service.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(minutes=60)
    )
    return f"https://{blob_service.account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"

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
        logger.error(f"❌ Error accessing blob storage: {e}")
        raise HTTPException(status_code=500, detail="Error accessing blob storage")

    return {
        "user_id": user_id,
        "full_name": f"{user['first name']} {user['last name']}",
        "gender": user.get("gender", "Unspecified"),
        "ageRange": user.get("ageRange", "Unspecified"),
        "total_images": len(image_urls),
        "images": image_urls
    }
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

@app.get("/recommendation/{user_id}")
def get_recommendation(user_id: str, query: str = Query(..., description="Clothing request")):
    try:
        user = get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        wardrobe_items = list(wardrobe_container.query_items(
            query="SELECT * FROM c WHERE c.user_id = @uid",
            parameters=[{"name": "@uid", "value": user_id}],
            enable_cross_partition_query=True
        ))
        if not wardrobe_items:
            raise HTTPException(status_code=404, detail="No wardrobe items found")

        # Step 1: Build DataFrame
        df = pd.DataFrame([
            {
                "ImageName": item["id"].split("_", 1)[-1],
                "Caption": item.get("caption", ""),
                "Tags": [list(t.keys())[0] for t in item.get("tags", [])],
                "ImageURL": item["image_url"]
            }
            for item in wardrobe_items
        ])
        #logger.info(df["ImageName"])
        engine = RecommenderEngine("imageconfig.json")
        engine.df = df
        recommendation_text = engine.get_dress_recommendation(query)
        logger.info(recommendation_text)
        if "Your query does not appear to be related to fashion" in recommendation_text:
            return recommendation_text
        lines = recommendation_text.strip().splitlines()[1:]

        
# Store the results
        results = []

        for line in lines:
            # Skip blank lines
            if not line.strip() or ":" not in line:
                continue
    
        # Extract item inside ** **
            #match = re.search(r"\*\*(.*?)\*\*", line)
            match = re.search(r"\*\*(?:.*?\b)?([FM]_\d+)\b.*?\*\*", line)
            item = match.group(1) if match else None
            #print(item)
            logger.info(item)
            # Extract description after the first colon
            #desc = line.split(":", 1)[1].strip() if ":" in line else ""
            desc = line
            if item:
                results.append({"item": item, "description": desc})
        
        response_collection = []
        response_collection_description = []
        for r in results:
            url = df[df["ImageName"]==r["item"]]["ImageURL"].iloc[0]
        
        #re.search(rf"{re.escape(r["item"])}\.(jpg|png)", url)
            url_match = re.search(rf"{re.escape(r["item"])}\.(jpg|png)", url)
            image_id = url_match.group(0)
            image_url = generate_sas_url(user_id,image_id)
            #print(image_url)
            logger.info(image_url)
            response_collection.append(image_url)
            response_collection_description.append({"image_url": image_url, "description": r["description"]})

        return response_collection_description

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
