from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import bcrypt
from RecommendationSystem import RecommendationSystem
from hashlib import sha256
from collections import deque
from RecommendationSystem import


# app = FastAPI()

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")

try:
    client = MongoClient(MONGODB_URI)
    client.admin.command('ping')
    print("Connected to MongoDB successfully!")
except Exception as e:
    print("Failed to connect to MongoDB:", e)
    exit(1)

# Select the database and collection
db = client["test"]
collection = db["productdata"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

user_messages = deque(maxlen=7)  
chatbot_responses = deque(maxlen=7) 
conversation_history = {}

chatbot = Chatbot()

class User(BaseModel):
    username: str
    password: str
    email: str

class Preferences(BaseModel):
    username: str
    email: str
    password: str
    preferredColors: list
    wearTypes: list
    fashionStyles: list
    
class UserLogin(BaseModel):
    email: str
    password: str

class ChatRequest(BaseModel):
    message: str

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password


@app.get("/")
async def root():
    return {"message": "API is running!"}


@app.post("/recommendations")

async def recommendations_endpoint(preferences: str):
    print("Preferences received:", preferences)
    rec_sys = RecommendationSystem()

    # Step 1: Generate response from the model
    response_text = rec_sys.generate_with_groq(preferences)

    # Step 2: Extract recommended product IDs
    retrieved_ids = rec_sys.extract_preferenced_items(response_text)

    # Step 3: Fetch product details from MongoDB
    retrieved_object_ids = [ObjectId(id) for id in retrieved_ids]
    products = list(collection.find({"_id": {"$in": retrieved_object_ids}}))

    return {"recommendedProducts": products}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  
    uvicorn.run(app, host="0.0.0.0", port=port)  
# if __name__ == "__main__":
#     # Initialize the recommendation system
#     rec_sys = RecommendationSystem()

#     # Step 1: Generate recommendations from preferences
#     response_text = rec_sys.generate_with_groq(dummy_preferences)

#     # Step 2: Extract item IDs based on the response
#     retrieved_ids = rec_sys.extract_preferenced_items(response_text)

#     # Step 3: Print the retrieved item IDs
#     print("Retrieved IDs:", retrieved_ids)
#     load_dotenv()

#     MONGODB_URI = os.getenv("MONGODB_URI")

#     try:
#         client = MongoClient(MONGODB_URI)
#         client.admin.command('ping')
#         print("Connected to MongoDB successfully!")
#     except Exception as e:
#         print("Failed to connect to MongoDB:", e)
#         exit(1)

#     # Select the database and collection
#     db = client["test"]
#     collection = db["productdata"]

#     from bson import ObjectId  # Ensure ObjectIds are correctly formatted

#     # Convert string IDs to ObjectId
#     retrieved_object_ids = [ObjectId(id) for id in retrieved_ids]

#     # Fetch product details
#     product_details = fetch_product_details(retrieved_object_ids)

#     # Print the fetched products
#     for product in product_details:
#         print(product)
