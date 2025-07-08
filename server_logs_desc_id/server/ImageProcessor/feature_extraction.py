from azure.storage.blob import BlobServiceClient
from azure.ai.vision import ImageAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.cosmos import CosmosClient
from typing import List, Dict

class WardrobeRecommender:
    def __init__(self, blob_connection_string: str, cosmos_endpoint: str, cosmos_key: str, cognitive_services_endpoint: str, cognitive_services_key: str):
        # Azure Blob Storage Client Setup
        self.blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
        
        # Cosmos DB Client Setup
        self.cosmos_client = CosmosClient(cosmos_endpoint, cosmos_key)
        self.database_name = "UserDatabase"
        self.container_name_wardrobe_images = "UserWardrobeImages"
        self.container_wardrobe_images = self.cosmos_client.get_database_client(self.database_name).get_container_client(self.container_name_wardrobe_images)
        
        # Azure Cognitive Services - Computer Vision Setup
        self.vision_client = ImageAnalysisClient(
            endpoint=cognitive_services_endpoint,
            credential=AzureKeyCredential(cognitive_services_key)
        )
        
    def extract_features_from_image(self, image_url: str) -> Dict:
        """Extracts features from a given image using Azure Cognitive Services."""
        # Analyze the image using the Cognitive Services Computer Vision API
        poller = self.vision_client.begin_analyze_image(image_url, features=["Categories", "Color", "Tags", "Objects"])
        result = poller.result()

        categories = [category.name for category in result.categories]
        dominant_colors = [color.primary for color in result.color.dominant_colors]
        tags = result.tags  # Tags like "formal", "dress", etc.
        objects = [obj.name for obj in result.objects]  # Detect objects (clothing types)

        # Return extracted features
        return {
            "categories": categories,
            "dominant_colors": dominant_colors,
            "tags": tags,
            "objects": objects
        }
    
    def save_features_to_cosmos(self, image_url: str, features: Dict):
        """Save the extracted features into Cosmos DB."""
        item = {
            "id": image_url,  # Using the image URL as the unique ID
            "imageUrl": image_url,
            "categories": features["categories"],
            "dominant_colors": features["dominant_colors"],
            "tags": features["tags"],
            "objects": features["objects"],
            "createdAt": "2025-06-07T00:00:00",  # Timestamp
            "updatedAt": "2025-06-07T00:00:00"
        }

        # Upsert item into Cosmos DB (insert or update)
        self.container_wardrobe_images.upsert_item(item)
        print(f"Saved features for image: {image_url}")
    
    def recommend_from_wardrobe(self, user_query: str) -> List[str]:
        """Recommend wardrobe items based on the user query and the features stored in Cosmos DB."""
        relevant_tag = "formal" if "formal" in user_query.lower() else "casual"

        # Query Cosmos DB to fetch wardrobe items with relevant tags
        query = f"SELECT * FROM UserWardrobeImages WHERE ARRAY_CONTAINS(tags, '{relevant_tag}')"
        query_results = list(self.container_wardrobe_images.query_items(
            query=query,
            enable_cross_partition_query=True
        ))

        # Collect recommended items (image URLs)
        recommended_items = [item["imageUrl"] for item in query_results]

        return recommended_items

    # def process_and_recommend(self, image_url: str, user_query: str):
    #     """Process an image to extract features, save to Cosmos DB, and provide recommendations."""
    #     # Extract features from the image
    #     features = self.extract_features_from_image(image_url)

    #     # Save features to Cosmos DB
    #     self.save_features_to_cosmos(image_url, features)

    #     # Get wardrobe recommendations based on the user's query
    #     recommendations = self.recommend_from_wardrobe(user_query)

    #     return recommendations

        def process(self, image_url: str, user_query: str):
        """Process an image to extract features, save to Cosmos DB, and provide recommendations."""
        # Extract features from the image
        features = self.extract_features_from_image(image_url)

        # Save features to Cosmos DB
        self.save_features_to_cosmos(image_url, features)

        
        return recommendations


# Example usage:
 if __name__ == "__main__":    
    # Initialize the recommender with your Azure credentials
    recommender = WardrobeRecommender(
        blob_connection_string="your_blob_connection_string",
        cosmos_endpoint="your_cosmos_endpoint",
        cosmos_key="your_cosmos_key",
        cognitive_services_endpoint="your_cognitive_services_endpoint",
        cognitive_services_key="your_cognitive_services_key"
    )


    # Example image URL and user query
    image_url = "https://example.com/path/to/wardrobe_image.jpg"
    user_query = "What should I wear for my formal event?"

    # Process the image and get recommendations
    recommendations = recommender.process_and_recommend(image_url, user_query)
    print("Recommended wardrobe items:", recommendations)
