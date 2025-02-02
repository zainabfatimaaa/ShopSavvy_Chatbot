import os
from groq import Groq
from dotenv import load_dotenv
from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from pinecone import Pinecone, ServerlessSpec
from RecTemplate import retriever_template
from pymongo import MongoClient
from fastapi import FastAPI
from pydantic import BaseModel
from bson import ObjectId

load_dotenv()

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for testing, can be restricted later
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

client = Groq(
    api_key=os.getenv("GROQ_API")  # Ensure the GROQ_API environment variable is set
)

mongo_client = MongoClient(os.getenv("MONGODB_URI"))
db = mongo_client["test"]
collection = db["productdata"]

class RecommendationSystem:
    def __init__(self):
        self.vector_store = None
        self.initialize_vector_store()
        self.retriever = self.vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 5, "score_threshold": 0.7},
        )

    def initialize_vector_store(self):
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        pc = Pinecone(pinecone_api_key)
        index_name = "llms-project"
        
        if index_name not in pc.list_indexes().names():
            pc.create_index(
                name=index_name,
                dimension=768,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )

        embeddings = HuggingFaceEmbeddings()
        index = pc.Index(index_name)
        self.vector_store = PineconeVectorStore(index=index, embedding=embeddings)

    def extract_preferenced_items(self, input_text):
        ids = []
        keyword = "Description:"
        extracted_items = [
            line.split(f"{keyword} ")[1].strip()
            for line in input_text.splitlines()
            if keyword in line and f"{keyword} " in line
        ]
        retriever = self.vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 1, "score_threshold": 0.8}
        )
        
        for item in extracted_items:
            results = retriever.get_relevant_documents(item)
            for doc in results:
                if 'mongo_id' in doc.metadata:
                    ids.append(doc.metadata['mongo_id'])
        
        return list(set(ids))  

    def generate_with_groq(self, preferences):
        prompt = retriever_template.format(preferences=preferences)
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": prompt},
            ],
            model="llama3-70b-8192",
        )
        return chat_completion.choices[0].message.content



@app.get("/")
async def root():
    return {"message": "API is running!"}

class PreferencesRequest(BaseModel):
    input_text: str

# Initialize your RecommendationSystem
recommendation_system = RecommendationSystem()

@app.post("/recommendations")
async def get_product_ids(preferences_request: PreferencesRequest):
    # Extract product IDs based on the provided preferences
    preferences = preferences_request.input_text
    print(preferences)
    response_text = recommendation_system.generate_with_groq(preferences)
    print(response_text)
    product_ids = recommendation_system.extract_preferenced_items(response_text)
    
    # Return the list of product IDs as a response
    return {"product_ids": product_ids}

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
