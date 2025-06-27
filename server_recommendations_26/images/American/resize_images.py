import os
from PIL import Image

# Define input and output base directories
input_base = "original_images"   # corrected folder name
output_base = "resized_images"   # use consistent plural naming

# Define categories
categories = ["men", "women"]

# Target size (width, height)
target_size = (400, 800)

# Loop through both categories
for category in categories:
    input_folder = os.path.join(input_base, category)
    output_folder = os.path.join(output_base, category)

    # Check if input folder exists
    if not os.path.exists(input_folder):
        print(f"❌ Folder not found: {input_folder}")
        continue

    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Process each image in the folder
    for filename in os.listdir(input_folder):
        file_path = os.path.join(input_folder, filename)

        try:
            with Image.open(file_path) as img:
                img = img.resize(target_size)
                output_path = os.path.join(output_folder, filename)
                img.save(output_path)
                print(f"✅ Resized: {filename}")
        except Exception as e:
            print(f"⚠️ Error processing {filename}: {e}")
