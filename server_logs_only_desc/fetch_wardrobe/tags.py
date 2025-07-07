import os
import uuid
from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Azure configs
COSMOS_URI = os.getenv("COSMOS_URI")
COSMOS_KEY = os.getenv("COSMOS_KEY")
DATABASE_NAME = os.getenv("DATABASE_NAME")
BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING")

# Cosmos DB client
cosmos_client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
db = cosmos_client.get_database_client(DATABASE_NAME)
wardrobe_container = db.get_container_client("wardrobe")

# Blob client
blob_service = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)

# Map user_id to correct tags file
user_tags = {
    "user1": "output1.txt",
    "user2": "output.txt",
    "user3": "output.txt"
}

def parse_tags_file(filepath):
    entries = []
    with open(filepath, "r", encoding="utf-8") as file:
        lines = file.readlines()

    current = {}
    tags = []
    dense = []
    for line in lines:
        line = line.strip()
        if line.startswith("Analyzing image:"):
            if current:
                # Finalize previous image
                full_tag = f"Caption: {current['caption']}\nTags:\n" + "\n".join(tags)
                if dense:
                    full_tag += "\nDense Captions:\n" + "\n".join(dense)
                current['tags'] = full_tag
                entries.append(current)
                tags = []
                dense = []

            # New image
            path = line.split("Analyzing image:")[-1].strip()
            image_name = os.path.basename(path)
            image_id = os.path.splitext(image_name)[0]
            current = {"image_id": image_id}

        elif line.startswith("Caption:"):
            current['caption'] = line.replace("Caption:", "").strip()

        elif line.startswith("-"):
            tags.append(line)

        elif line.lower().startswith("- a ") or line.lower().startswith("- an "):
            dense.append(line)

    # Append last image
    if current:
        full_tag = f"Caption: {current.get('caption', '')}\nTags:\n" + "\n".join(tags)
        if dense:
            full_tag += "\nDense Captions:\n" + "\n".join(dense)
        current['tags'] = full_tag
        entries.append(current)

    return entries

def upload_to_cosmos(user_id, entries):
    for entry in entries:
        blob_name = f"{entry['image_id']}.jpg"
        image_url = f"https://{blob_service.account_name}.blob.core.windows.net/{user_id}/{blob_name}"

        doc = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "image_id": entry["image_id"],
            "image_url": image_url,
            "tags": entry["tags"]
        }

        wardrobe_container.upsert_item(doc)
        print(f"✅ Uploaded {entry['image_id']} for {user_id}")

# Process all users
for user_id, file_name in user_tags.items():
    print(f"\n📁 Processing {file_name} for {user_id}")
    if os.path.exists(file_name):
        entries = parse_tags_file(file_name)
        upload_to_cosmos(user_id, entries)
    else:
        print(f"❌ File not found: {file_name}")
