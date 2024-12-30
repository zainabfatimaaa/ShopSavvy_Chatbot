import os
import openai
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime
import logging

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)

# MongoDB connection setup
MONGODB_URI = os.getenv("MONGODB_URI")

# Connect to MongoDB
try:
    client = MongoClient(MONGODB_URI)
    # Ping the database to check if the connection is successful
    client.admin.command('ping')
    logging.info("Connected to MongoDB successfully!")
except Exception as e:
    logging.error(f"Failed to connect to MongoDB: {e}")
    exit(1)

# Select the database and collection
db = client["ShopSavvy"]
collection = db["productdata"]

# Setting up the Hugging Face API key
gptApiKey = os.getenv("OPENAI_API_KEY")
openai.api_key = gptApiKey

# OpenAI API URL and headers
API_URL = "https://api.openai.com/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {gptApiKey}",
    "Content-Type": "application/json"
}

# Fetch products from MongoDB
products = collection.find()

# Process each product
for product in products:
    try:
        if product.get("Embeddings Created") is True:
            logging.info(f"Product with MongoDB ID {product['_id']} already has embeddings created. Skipping...")
            continue

        # Extract product data from MongoDB
        product_data = {
            "name": product.get('product'),
            "colors": product.get('colors', []),
            "sizes": product.get('sizes', []),
            "primary_color": product.get('primary_color', ''),
            "type": product.get('type', ''),
            "gender": product.get('gender', ''),
        }

        logging.info(f"Processing product: {product_data['name']}")

        # Define the few-shot prompt
        few_shot_prompt = (
            "Here are the few examples with attributes of a product as input, and the detailed description of the product as the output.\n"
            "You have to generate the description once only, and don't add any examples. You have to simply give the detailed description of the product based on its attributes.\n"
            "\nExample 1:\n"
            "Attributes: {'name': 'DAILY CREW NECK TEE', 'colors': ['BLACK', 'DARK OLIVE', 'IVORY'], 'sizes': ['SMALL', 'MEDIUM', 'LARGE', 'X-LARGE', 'XX-LARGE'], 'primary_color': 'DARK OLIVE', 'type': 'T-Shirt', 'gender': 'Men'}\n"
            "Description: A versatile dark olive crew neck tee designed for men, perfect for everyday casual wear. Its understated color pairs well with jeans, chinos, or shorts for a relaxed and stylish look. Ideal for laid-back outings, layering under jackets, or lounging at home. Available in sizes SMALL, MEDIUM, LARGE, X-LARGE, and XX-LARGE, and in colors BLACK, DARK OLIVE, and IVORY\n\n"
            "Example 2:\n"
            "Attributes: {'name': 'RIBBED KNIT TROUSER', 'colors': ['NAVY', 'CAMEL', 'BLACK'], 'sizes': ['SMALL', 'MEDIUM', 'LARGE', 'X-LARGE', 'XX-LARGE'], 'primary_color': 'CAMEL', 'type': 'Bottoms', 'gender': 'Men'}\n"
            "Description: Comfortable and versatile camel ribbed knit trousers designed for men, perfect for casual outings or relaxed settings. These trousers combine style and ease, making them ideal for pairing with a simple tee, sweater, or casual shirt. The ribbed texture adds a modern touch, while the camel color complements a variety of outfits. Available in sizes SMALL, MEDIUM, LARGE, X-LARGE, and XX-LARGE, and in colors NAVY, CAMEL, and BLACK\n\n"
            "Example 3:\n"
            "Attributes: {'name': 'LEATHER LACE-UP SNEAKERS', 'colors': ['ALL BLACK', 'OLIVE', 'TAUPE'], 'sizes': ['40', '41', '42', '43', '44', '45', '46'], 'primary_color': 'TAUPE', 'type': 'Sneakers', 'gender': 'Men'} \n"
            "Description: Stylish taupe leather lace-up sneakers designed for men, perfect for casual outings or smart-casual occasions. These sneakers offer a refined yet versatile look, pairing effortlessly with jeans, chinos, or even tailored trousers. Suitable for day-to-day wear or semi-formal settings, they are a comfortable and chic addition to any wardrobe. Available in sizes 40, 41, 42, 43, 44, 45, and 46, and in colors ALL BLACK, OLIVE, and TAUPE\n\n"
            "Now, generate a description for the following product, keeping in mind that the language should be direct, with no extra embellishments:\n\n"
        )

        # Construct the prompt for OpenAI API
        prompt = (
            f"Provide a clear, concise product description for the item named '{product_data['name']}', "
            f"a {product_data['primary_color']} {product_data['type']} for {product_data['gender']}. "
            "Only use the information provided in the attributes and do not add unnecessary details about fabric, fit, or qualities not listed in the attributes. "
            "The description should explain how and where the item might be worn based on its style. "
            "Avoid formal or promotional language like 'introducing' or 'order yours today.' "
            "Do add information about the product size and colors in the response if it is given in the input attributes.\n\n"
            f"Attributes: {product_data}\n{few_shot_prompt}"
        )

        # Call OpenAI API to generate description
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",  # Use a valid OpenAI model
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates product descriptions."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=200,
                temperature=0.7
            )

            output = response['choices'][0]['message']['content']
            if not output:
                logging.warning(f"No description generated for product {product_data['name']}")
                continue

            logging.info(f"Generated Description for {product_data['name']}:\n{output}")

            # Update MongoDB with generated description
            try:
                collection.update_one(
                    {"_id": product["_id"]},
                    {
                        "$set": {
                            "detailed_description": output,
                            "Embeddings Created": True  # Mark as processed
                        }
                    }
                )
                logging.info(f"Updated product {product_data['name']} in MongoDB.")
            except Exception as e:
                logging.error(f"Error updating MongoDB for product {product_data['name']}: {e}")

        except openai.error.OpenAIError as e:
            logging.error(f"Error generating description for {product_data['name']}: {e}")
            continue

    except Exception as e:
        logging.error(f"Error processing product {product['_id']}: {e}")
