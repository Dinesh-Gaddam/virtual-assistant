import os
from azure.cosmos import CosmosClient
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

#COSMOS_URI = os.getenv("COSMOS_URI")
#COSMOS_KEY = os.getenv("COSMOS_KEY")
#DATABASE_NAME = os.getenv("DATABASE_NAME")

client = CosmosClient(COSMOS_URI, COSMOS_KEY)
database = client.get_database_client(DATABASE_NAME)

user_container = database.get_container_client("users")
query_container = database.get_container_client("promotedQueries")

now = datetime.utcnow().isoformat()

users = [
    {
        "id": "user1",
        "ageRange": "25-30",
        "gender": "Female",
        "first name": "Rachel",
        "last name": "Ong",
        "createdAt": now,
        "updatedAt": now
    },
    {
        "id": "user2",
        "ageRange": "30-35",
        "gender": "Male",
        "first name": "John",
        "last name": "Smith",
        "createdAt": now,
        "updatedAt": now
    },
    {
        "id": "user3",
        "ageRange": "20-25",
        "gender": "Male",
        "first name": "Michael",
        "last name": "Lee",
        "createdAt": now,
        "updatedAt": now
    }
]

# Queries + responses with 3 shirts or dresses each
queries_and_responses = [
    ("What should I wear for my interview?", ["Business Suit", "Formal Shirt & Trousers", "Blazer & Skirt"]),
    ("Best exercises for weight loss?", ["Running Shirt", "Sweat-Wicking T-Shirt", "Breathable Tank Top"]),
    ("Top programming languages in 2025?", ["Tech Conference Tee", "Hoodie", "Smart Casual Shirt"]),
    ("How to manage time effectively?", ["Comfortable Polo Shirt", "Classic Dress Shirt", "Relaxed Fit T-Shirt"]),
    ("Healthy breakfast ideas?", ["Apron Dress", "Chef's Shirt", "Casual Linen Dress"]),
    ("Tips for improving sleep quality?", ["Soft Cotton Pajamas", "Silk Nightgown", "Breathable Sleep Shirt"]),
    ("How to learn AI quickly?", ["Geeky T-Shirt", "Lab Coat Style Shirt", "Comfort Hoodie"]),
    ("Best places to visit in Europe?", ["Travel Jacket", "Light Sweater", "Outdoor Performance Shirt"]),
    ("How to reduce stress at work?", ["Relaxed Fit Shirt", "Breathable Polo", "Casual Dress Shirt"]),
    ("Recommended books for leadership?", ["Business Casual Shirt", "Formal Dress Shirt", "Blazer"])
]

query_id_counter = 1

# Insert users
for user in users:
    try:
        user_container.create_item(body=user)
        print(f"Inserted user: {user['id']}")
    except Exception as e:
        print(f"Error inserting user {user['id']}: {str(e)}")

# Insert queries per user
for user in users:
    for query_text, response_items in queries_and_responses:
        promoted_query = {
            "id": f"promotedQuery{query_id_counter}",
            "userId": user["id"],
            "query": query_text,
            "response": response_items,
            "createdAt": now
        }
        try:
            query_container.create_item(body=promoted_query)
            print(f"Inserted promoted query {promoted_query['id']} for user {user['id']}")
        except Exception as e:
            print(f"Error inserting query {promoted_query['id']}: {str(e)}")
        query_id_counter += 1

print("All users and queries with specific clothing responses inserted successfully.")
