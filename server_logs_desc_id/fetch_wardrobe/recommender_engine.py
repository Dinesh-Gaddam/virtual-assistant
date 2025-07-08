import json
import re
import pandas as pd
from pathlib import Path, PureWindowsPath
from openai import OpenAI

class RecommenderEngine:
    def __init__(self, config_file='imageconfig.json'):
        self.config = self.load_config(config_file)
        self.vision_uri = self.config['AzureVisionService']['Uri']
        self.vision_key = self.config['AzureVisionService']['Key']
        self.azure_openai_uri = self.config['AzureOpenAIService']['Uri']
        self.azure_openai_key = self.config['AzureOpenAIService']['Key']
        self.openai_key = self.config['OpenAIService']['Key']
        self.df = None

    def load_config(self, config_file):
        with open(config_file, 'r') as file:
            config = json.load(file)
        return config

    def load_tagged_data(self, file_path):
        data = []
        current = {}

        def extract_confidence(text):
            match = re.search(r"\(Confidence:\s*([0-9.]+)\)", text)
            return float(match.group(1)) if match else None

        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                stripped = line.strip()

                if stripped.startswith("Analyzing image:"):
                    if current:
                        data.append(current)
                    current = {
                        "ImagePath": stripped.replace("Analyzing image:", "").strip(),
                        "Caption": "",
                        "CaptionConfidence": None,
                        "Tags": [],
                        "TagConfidences": []
                    }

                elif stripped.startswith("Caption:"):
                    caption_line = stripped.replace("Caption:", "").strip()
                    current["CaptionConfidence"] = extract_confidence(caption_line)
                    current["Caption"] = caption_line[:caption_line.rfind("(")].strip() if "(" in caption_line else caption_line

                elif stripped.startswith("-"):
                    tag_line = stripped[1:].strip()
                    confidence = extract_confidence(tag_line)
                    tag = tag_line[:tag_line.rfind("(")].strip() if "(" in tag_line else tag_line
                    current["Tags"].append(tag)
                    current["TagConfidences"].append(round(confidence, 3) if confidence else None)

        if current:
            data.append(current)

        for entry in data:
            entry["TagConfidenceMap"] = {
                tag: conf for tag, conf in zip(entry["Tags"], entry["TagConfidences"])
            }
            entry["ImageName"] = PureWindowsPath(entry["ImagePath"]).name

        self.df = pd.DataFrame(data)
        return self.df

    def get_dress_recommendation(self, user_query: str) -> str:
        if self.df is None:
            raise ValueError("Wardrobe DataFrame is not loaded. Please load using load_tagged_data().")

        prompt = f"The user asked: '{user_query}'\n\n"
        prompt += "Here are the wardrobe items:\n"
        for _, row in self.df.iterrows():
            prompt += f"Item: {row['ImageName']} \t Caption:{row['Caption']} \t Tags: {', '.join(row['Tags'])}\n"

        client = OpenAI(        
        api_key=self.openai_key
        )

        response = client.responses.create(
        model="gpt-4o",
        instructions="You are a fashion assistant. Based on the user's query and wardrobe items, recommend the top 3 most suitable dress items.Only respond with clothing recommendations if the user query is about fashion, style, or dress suggestions.If the query is unrelated to fashion, respond with:'Your query does not appear to be related to fashion. Please ask about clothing, style, or an upcoming occasion.",
        input=prompt,
        )
        return response.output_text
        

# ----------------------------
# Example Usage
# ----------------------------

#engine = RecommenderEngine('imageconfig.json')
#df = engine.load_tagged_data(r"D:\backup_1\images\American\resized_images\women\Women_Tags")
#user_query = "Recommend a dress for tomorrow's interview"
#user_query = "Recommend a dress for gala dinner"
#user_query = "Recommend a dress for dating"
#recommendation = engine.get_dress_recommendation(user_query)
#print("Recommended Items:\n", recommendation)
