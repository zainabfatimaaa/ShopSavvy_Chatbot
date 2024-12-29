from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
import bcrypt
from chatbot import Chatbot
from hashlib import sha256
from collections import deque


app = FastAPI()

mongo_client = MongoClient("mongodb+srv://AhmadJb:F6ndXplHiGRKfR56@products.btwmn.mongodb.net/")
db = mongo_client["LLMs_Project"]
users_collection = db["Users"]

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


@app.post("/register")
async def register(user: User):
    hashed_password = sha256(user.password.encode()).hexdigest()
    user_data = {
        "username": user.username,
        "password": hashed_password,
        "email": user.email,
        "preferences": {}
    }

    users_collection.insert_one(user_data)
    return {"message": "User registered successfully"}

@app.post("/login")
async def login_user(user: UserLogin):
    existing_user = users_collection.find_one({"email": user.email})
    if not existing_user:
        raise HTTPException(status_code=400, detail="Invalid email or password.")
    
    if not bcrypt.checkpw(user.password.encode('utf-8'), existing_user["password"]):
        raise HTTPException(status_code=400, detail="Invalid email or password.")
    
    return {"message": "Login successful!"}
    
@app.get("/")
async def read_root():
    return {"message": "Hello, world!"}


@app.post("/register_with_preferences")
async def register_with_preferences(preferences: Preferences):
    # Hash password
    hashed_password = sha256(preferences.password.encode()).hexdigest()
    
    # Find user and update their preferences
    users_collection.update_one(
        {"username": preferences.username},
        {
            "$set": {
                "preferences": {
                    "colors": preferences.preferredColors,
                    "wearTypes": preferences.wearTypes,
                    "fashionStyles": preferences.fashionStyles
                },
                "password": hashed_password
            }
        }
    )
    return {"message": "User registered with preferences successfully"}

@app.post("/chatbot")
async def chatbot_endpoint(request: ChatRequest):
    user_message = request.message

    try:
        # Maintain the conversation history
        for i in range(len(user_messages)):
            conversation_history[user_messages[i]] = chatbot_responses[i]

        # Generate chatbot responses
        bot_retrieval_chain_response = chatbot.retrieval_chain(conversation_history, user_message)
        bot_response = chatbot.response_chain(user_message, bot_retrieval_chain_response, conversation_history)

        # Update history queues
        chatbot_responses.append(bot_response)
        user_messages.append(user_message)

        # Extract IDs for image generation
        ids = chatbot.extract_by_keyword(bot_retrieval_chain_response)

        print("Conversation History:", conversation_history)
        return {"response": bot_response, "ids": ids}
    except Exception as e:
        return {"response": f"Error: {str(e)}", "ids": []}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  
    uvicorn.run(app, host="0.0.0.0", port=port)  