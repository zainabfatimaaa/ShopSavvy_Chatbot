import os
from groq import Groq
from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from pinecone import Pinecone
from functools import lru_cache
import asyncio
import re

# Product cache
product_cache = {}

class OptimizedChatbot:
    def __init__(self):
        self.groq_client = Groq(api_key="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")
        self.vector_store = None
        self.conversation_context = {}
        self.initialize_vector_store()
        self.load_product_cache()
        
    def initialize_vector_store(self):
        pc = Pinecone("pcsk_iAgUU_FXUSfemuBAKgQTBG1eKLxZyoxA9RfUMgdpQJNkF8H1dYSaQtRbRAauDzviDsQ8w")
        index_name = "llms-project"
        
        embeddings = HuggingFaceEmbeddings()
        index = pc.Index(index_name)
        self.vector_store = PineconeVectorStore(index=index, embedding=embeddings)
    
    def load_product_cache(self):
        # Preload common product details
        global product_cache
        from pymongo import MongoClient
        
        client = MongoClient("mongodb+srv://JB:Ahmad123@shopsavvy.xaqy1.mongodb.net/?retryWrites=true&w=majority&appName=ShopSavvy")
        db = client["test"]
        collection = db["productdata"]
        
        products = collection.find({}, {"_id": 1, "detailed_description": 1})
        for product in products:
            product_cache[str(product["_id"])] = {
                "description": product.get("detailed_description", "")
            }
    
    def extract_search_terms(self, llm_response):
        pattern = r"\[SEARCH_TERMS\](.*?)\[/SEARCH_TERMS\]"
        match = re.search(pattern, llm_response, re.DOTALL)
        if match:
            return [term.strip() for term in match.group(1).split(",")]
        return []
    
    def extract_response_template(self, llm_response):
        pattern = r"\[RESPONSE_TEMPLATE\](.*?)\[/RESPONSE_TEMPLATE\]"
        match = re.search(pattern, llm_response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return "Here are some style suggestions for you: {products}"
    
    @lru_cache(maxsize=100)
    def cached_vector_search(self, query_text, product_type=None):
        # Optimize search with caching
        filter_dict = {"type": product_type} if product_type else None
        
        retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={
                "k": 1, 
                "filter": filter_dict
            }
        )
        return retriever.get_relevant_documents(query_text)
    
    async def generate_search_terms(self, user_message):
        # Generate search terms from user query using a smaller model
        prompt = f"""
        Based on the user's fashion query: "{user_message}"
        
        Identify 2-4 specific product descriptions that would match items in a fashion database.
        Format your response as follows:
        
        [SEARCH_TERMS]
        term1, term2, term3
        [/SEARCH_TERMS]
        
        [RESPONSE_TEMPLATE]
        Here are some great suggestions to go with your {extract_main_item(user_message)}:
        - {{product1}} would look amazing
        - {{product2}} provides a perfect complement
        [/RESPONSE_TEMPLATE]
        """
        
        chat_completion = self.groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",  # Much smaller, faster model
        )
        
        response = chat_completion.choices[0].message.content
        return response
    
    async def search_products(self, search_terms):
        # Perform parallel vector searches
        tasks = []
        for term in search_terms:
            product_type = extract_product_type(term)
            tasks.append(asyncio.create_task(
                self.async_vector_search(term, product_type)
            ))
        
        results = await asyncio.gather(*tasks)
        product_ids = []
        
        for docs in results:
            for doc in docs:
                if 'mongo_id' in doc.metadata:
                    product_ids.append(doc.metadata['mongo_id'])
        
        return product_ids
    
    async def async_vector_search(self, query, product_type=None):
        # Async wrapper for vector search
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.cached_vector_search, query, product_type
        )
    
    def fill_response_template(self, template, product_ids):
        # Fill template with actual product descriptions
        products = []
        
        for product_id in product_ids:
            if product_id in product_cache:
                products.append(product_cache[product_id]["description"])
            else:
                # Fallback to DB lookup if needed
                products.append(f"Product {product_id}")
        
        # Simple template filling
        placeholders = [f"{{product{i+1}}}" for i in range(len(products))]
        for i, placeholder in enumerate(placeholders):
            if i < len(products):
                template = template.replace(placeholder, products[i])
        
        return template
    
    async def process_chat(self, user_message):
        try:
            # Step 1: Generate search terms and response template
            llm_response = await self.generate_search_terms(user_message)
            
            # Step 2: Extract search terms and template
            search_terms = self.extract_search_terms(llm_response)
            response_template = self.extract_response_template(llm_response)
            
            # Step 3: Search for products
            product_ids = await self.search_products(search_terms)
            
            # Step 4: Fill template with product details
            final_response = self.fill_response_template(response_template, product_ids)
            
            return {"response": final_response, "ids": product_ids}
        except Exception as e:
            return {"response": f"I couldn't find the perfect match right now. {str(e)}", "ids": []}

# Helper functions
def extract_product_type(search_term):
    # Extract product type from search term (e.g., "black pants" -> "pants")
    common_types = ["shirt", "pants", "dress", "shoes", "boots", "jacket", "sweater"]
    for type in common_types:
        if type in search_term.lower():
            return type
    return None

def extract_main_item(query):
    # Extract the main item the user is asking about
    common_items = ["shirt", "pants", "dress", "shoes", "boots", "jacket", "sweater"]
    for item in common_items:
        if item in query.lower():
            return item
    return "outfit"