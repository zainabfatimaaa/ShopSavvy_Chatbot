import os
from groq import Groq
from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
from pinecone import Pinecone, ServerlessSpec
from templates import retriever_template, response_template, general_template


client = Groq(
    api_key="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" # Ensure the GROQ_API_KEY environment variable is set
)
convo = {}

class Chatbot:
    def __init__(self):
        self.ids = []  #
        self.retriever = None
        self.vector_store = None
        self.initialize_vector_store()
        self.initialize_retriever()

    def initialize_vector_store(self):
        pc = Pinecone("pcsk_iAgUU_FXUSfemuBAKgQTBG1eKLxZyoxA9RfUMgdpQJNkF8H1dYSaQtRbRAauDzviDsQ8w")

        index_name = "llms-project"

        if index_name not in pc.list_indexes().names():
            pc.create_index(
                name=index_name,
                dimension=768,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )

        embeddings = HuggingFaceEmbeddings() 
        index = pc.Index(index_name)
        self.vector_store = PineconeVectorStore(index=index, embedding=embeddings)

    def extract_by_keyword(self, input_text):
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

    def initialize_retriever(self):
        self.retriever = self.vector_store.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": 1, "score_threshold": 0.9},
        )

    def generate_with_groq(self, question, conversation_history):
        print(conversation_history)
        prompt = retriever_template.format(question=question,conversation_history= conversation_history)
        
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama3-70b-8192",
        )

        return chat_completion.choices[0].message.content
    
    def generate_with_groq_two(self, question, descriptions, conversation_history):
        prompt = response_template.format(question=question, descriptions = descriptions, conversation_history = conversation_history)
        
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama3-70b-8192",
        )

        return chat_completion.choices[0].message.content

    def retrieval_chain(self, conversation_history, question: str) -> str:
        response = self.generate_with_groq(question, conversation_history)
        return response
    
    def response_chain(self,question: str, descriptions, conversation_history) -> str:
        response = self.generate_with_groq_two(question, descriptions, conversation_history)
        return response