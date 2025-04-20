# from fastapi import FastAPI, HTTPException, Depends
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from pymongo import MongoClient
# import bcrypt
# from chatbot import Chatbot
# from hashlib import sha256
# from collections import deque
# import uvicorn
# import os

# app = FastAPI()

# MONGODB_URI ="mongodb+srv://JB:Ahmad123@shopsavvy.xaqy1.mongodb.net/?retryWrites=true&w=majority&appName=ShopSavvy"

# try:
#     mongo_client = MongoClient(MONGODB_URI)
#     mongo_client.admin.command('ping')
#     print("Connected to MongoDB successfully!")
# except Exception as e:
#     print("Failed to connect to MongoDB:", e)
#     exit(1)
    
    
# db = mongo_client["test"]
# collection = db["productdata"]
# users_collection = db["Accounts"]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  
#     allow_credentials=True,
#     allow_methods=["*"], 
#     allow_headers=["*"], 
# )

# user_messages = deque(maxlen=7)  
# chatbot_responses = deque(maxlen=7) 
# conversation_history = {}

# chatbot = Chatbot()

# class Preferences(BaseModel):
#     username: str
#     email: str
#     password: str
#     preferredColors: list
#     wearTypes: list
#     fashionStyles: list
    
# class ChatRequest(BaseModel):
#     message: str

# def hash_password(password: str) -> str:
#     salt = bcrypt.gensalt()
#     hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
#     return hashed_password

    
# @app.get("/")
# async def read_root():
#     return {"message": "Hello, world!"}


# @app.post("/register_with_preferences")
# async def register_with_preferences(preferences: Preferences):
#     # Hash password
#     hashed_password = sha256(preferences.password.encode()).hexdigest()
    
#     # Find user and update their preferences
#     users_collection.update_one(
#         {"username": preferences.username},
#         {
#             "$set": {
#                 "preferences": {
#                     "colors": preferences.preferredColors,
#                     "wearTypes": preferences.wearTypes,
#                     "fashionStyles": preferences.fashionStyles
#                 },
#                 "password": hashed_password
#             }
#         }
#     )
#     return {"message": "User registered with preferences successfully"}

# @app.post("/chatbot")
# async def chatbot_endpoint(request: ChatRequest):
#     user_message = request.message

#     try:
#         # Maintain the conversation history
#         for i in range(len(user_messages)):
#             conversation_history[user_messages[i]] = chatbot_responses[i]

#         # Generate chatbot responses
#         bot_retrieval_chain_response = chatbot.retrieval_chain(conversation_history, user_message)
#         bot_response = chatbot.response_chain(user_message, bot_retrieval_chain_response, conversation_history)

#         # Update history queues
#         chatbot_responses.append(bot_response)
#         user_messages.append(user_message)

#         # Extract IDs for image generation
#         ids = chatbot.extract_by_keyword(bot_retrieval_chain_response)

#         print("Conversation History:", conversation_history)
#         return {"response": bot_response, "ids": ids}
#     except Exception as e:
#         return {"response": f"Error: {str(e)}", "ids": []}

# # if __name__ == "__main__":
# #     port = int(os.environ.get("PORT", 8000))  
# #     uvicorn.run(app, host="0.0.0.0", port=port)  

# if __name__ == "__main__":
#     port = int(os.environ.get("PORT", 10000))  # Use Render-assigned PORT
#     print(f"Starting FastAPI server on port {port}...")
#     uvicorn.run(app, host="0.0.0.0", port=port)


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import time
from optimized_chatbot import OptimizedChatbot

# Load environment variables (you can use python-dotenv if needed)
MONGODB_URI = os.getenv("MONGODB_URI", "your_mongodb_uri")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "your_groq_api_key")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "your_pinecone_api_key")

app = FastAPI(title="Optimized Fashion Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize chatbot
print("Initializing chatbot...")
chatbot = OptimizedChatbot()

print("Chatbot initialized successfully")

class ChatRequest(BaseModel):
    message: str

@app.get("/")
async def read_root():
    return {"status": "online", "message": "Fashion Chatbot API is running"}

@app.post("/chatbot")
async def chatbot_endpoint(request: ChatRequest):
    start_time = time.time()
    print(f"Received request: {request.message}")
    
    try:
        result = await chatbot.process_chat(request.message)
        result["api_processing_time"] = time.time() - start_time
        return result
    except Exception as e:
        import traceback
        print(f"Error in endpoint: {str(e)}")
        print(traceback.format_exc())
        return {"response": "I'm having trouble processing your request right now.", "ids": [], "error": str(e)}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}

# For testing with curl or browser
@app.get("/test")
async def test_endpoint(message: str = "How to style black pants?"):
    return await chatbot_endpoint(ChatRequest(message=message))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    print(f"Starting FastAPI server on port {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)