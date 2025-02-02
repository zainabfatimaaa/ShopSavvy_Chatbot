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

load_dotenv()

app = FastAPI()

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

@app.post("/recommendations")
async def chatbot_endpoint(preferences: str):
    rec_sys = RecommendationSystem()

    # Step 1: Generate response from the model
    response_text = rec_sys.generate_with_groq(preferences)

    # Step 2: Extract recommended product IDs
    retrieved_ids = rec_sys.extract_preferenced_items(response_text)

    # Step 3: Fetch product details from MongoDB
    retrieved_object_ids = [ObjectId(id) for id in retrieved_ids]
    products = list(collection.find({"_id": {"$in": retrieved_object_ids}}))

    return {"recommendedProducts": products}

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
