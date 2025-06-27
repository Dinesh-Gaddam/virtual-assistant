import re
import pandas as pd
from pathlib import Path, PureWindowsPath

file_path = Path(r"C:\Users\likit\virtual-assistant\images\American\resized_images\women\Women_Tags")  # Change this to your actual file path

data = []
current = {}

def save_to_cosmos(user_id, image_name, caption, confidence, tags):
    blob_url = f"{BLOB_BASE_URL}/{user_id}/{image_name}{SAS_TOKEN}"
    item = {
        "id": f"{user_id}_{image_name}_{uuid4()}",
        "user_id": user_id,
        "image_url": blob_url,
        "caption": caption,
        "confidence_score": confidence,
        "tags": tags,
        "created_at": datetime.utcnow().isoformat()
    }
    try:
        container.upsert_item(item)
        logger.info(f"Uploaded {item['id']}")
    except Exception as e:
        logger.error(f"Error saving {item['id']}: {e}")

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

# Add last parsed item
if current:
    data.append(current)

# Add TagConfidenceMap and ImageName
for entry in data:
    entry["TagConfidenceMap"] = {
        tag: conf for tag, conf in zip(entry["Tags"], entry["TagConfidences"])
    }
    entry["ImageName"] = PureWindowsPath(entry["ImagePath"]).name
 
# Create DataFrame
df = pd.DataFrame(data)
print(df[["ImageName", "Caption", "CaptionConfidence", "Tags", "TagConfidenceMap"]])