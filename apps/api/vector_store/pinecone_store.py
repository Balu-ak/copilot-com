# apps/api/vector_store/pinecone_store.py
import os
from pinecone import Pinecone, ServerlessSpec

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "autobrain-dev")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-large")
EMBED_DIM = 3072 if "large" in EMBED_MODEL else 1536

pc = Pinecone(api_key=PINECONE_API_KEY)

def get_or_create_index():
    names = {i.name for i in pc.list_indexes()}
    if PINECONE_INDEX not in names:
        pc.create_index(
            name=PINECONE_INDEX,
            dimension=EMBED_DIM,
            metric="cosine",
            # for serverless, environment is just the region string (e.g., us-east-1)
            spec=ServerlessSpec(cloud="aws", region=PINECONE_ENVIRONMENT),
        )
    return pc.Index(PINECONE_INDEX)
