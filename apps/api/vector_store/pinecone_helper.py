"""
Pinecone Vector Database Helper
Handles document ingestion, embedding, and retrieval
"""
import os
from typing import List, Dict, Any
import hashlib

try:
    from pinecone import Pinecone, ServerlessSpec
    from openai import OpenAI
except ImportError:
    Pinecone = None
    OpenAI = None

class PineconeManager:
    """Manages Pinecone vector database operations"""
    
    def __init__(self):
        """Initialize Pinecone connection"""
        if Pinecone is None:
            raise ImportError("pinecone-client not installed. Run: pip install pinecone-client")
        
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise ValueError("PINECONE_API_KEY environment variable not set")
        
        self.pc = Pinecone(api_key=api_key)
        self.index_name = os.getenv("PINECONE_INDEX", "autobrain-dev")
        self.environment = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
        
        # Initialize OpenAI for embeddings
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if OpenAI else None
    
    def create_index_if_not_exists(self, dimension: int = 1536, metric: str = "cosine"):
        """Create Pinecone index if it doesn't exist"""
        existing_indexes = [index.name for index in self.pc.list_indexes()]
        
        if self.index_name not in existing_indexes:
            self.pc.create_index(
                name=self.index_name,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(
                    cloud='aws',
                    region=self.environment
                )
            )
            print(f"Created Pinecone index: {self.index_name}")
        else:
            print(f"Pinecone index already exists: {self.index_name}")
    
    def get_index(self):
        """Get Pinecone index instance"""
        return self.pc.Index(self.index_name)
    
    def get_embedding(self, text: str, model: str = "text-embedding-ada-002") -> List[float]:
        """Generate embedding for text using OpenAI"""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized. Set OPENAI_API_KEY")
        
        response = self.openai_client.embeddings.create(
            input=text,
            model=model
        )
        return response.data[0].embedding
    
    def upsert_document(
        self,
        doc_id: str,
        text: str,
        metadata: Dict[str, Any],
        org_id: str
    ) -> Dict[str, Any]:
        """
        Insert or update a document in Pinecone
        
        Args:
            doc_id: Unique document identifier
            text: Document text to embed
            metadata: Additional metadata (source, title, etc.)
            org_id: Organization ID for filtering
        
        Returns:
            Dict with operation status
        """
        index = self.get_index()
        
        # Generate embedding
        embedding = self.get_embedding(text)
        
        # Add org_id to metadata for filtering
        metadata['org_id'] = org_id
        metadata['text'] = text  # Store original text
        
        # Upsert to Pinecone
        index.upsert(
            vectors=[{
                "id": doc_id,
                "values": embedding,
                "metadata": metadata
            }]
        )
        
        return {
            "doc_id": doc_id,
            "status": "upserted",
            "embedding_dimension": len(embedding)
        }
    
    def upsert_documents_batch(
        self,
        documents: List[Dict[str, Any]],
        org_id: str,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Batch upsert multiple documents
        
        Args:
            documents: List of dicts with 'id', 'text', and 'metadata'
            org_id: Organization ID
            batch_size: Number of documents per batch
        
        Returns:
            Dict with operation stats
        """
        index = self.get_index()
        total_docs = len(documents)
        vectors = []
        
        for doc in documents:
            # Generate embedding
            embedding = self.get_embedding(doc['text'])
            
            # Prepare metadata
            metadata = doc.get('metadata', {})
            metadata['org_id'] = org_id
            metadata['text'] = doc['text']
            
            vectors.append({
                "id": doc['id'],
                "values": embedding,
                "metadata": metadata
            })
            
            # Upsert in batches
            if len(vectors) >= batch_size:
                index.upsert(vectors=vectors)
                vectors = []
        
        # Upsert remaining vectors
        if vectors:
            index.upsert(vectors=vectors)
        
        return {
            "total_documents": total_docs,
            "status": "completed"
        }
    
    def search(
        self,
        query: str,
        org_id: str,
        top_k: int = 5,
        min_score: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents
        
        Args:
            query: Search query text
            org_id: Organization ID to filter by
            top_k: Number of results to return
            min_score: Minimum similarity score threshold
        
        Returns:
            List of matching documents with scores
        """
        index = self.get_index()
        
        # Generate query embedding
        query_embedding = self.get_embedding(query)
        
        # Query Pinecone with org filter
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter={"org_id": org_id}
        )
        
        # Format results
        documents = []
        for match in results.get('matches', []):
            if match['score'] >= min_score:
                documents.append({
                    "id": match['id'],
                    "score": match['score'],
                    "content": match['metadata'].get('text', ''),
                    "source": match['metadata'].get('source', 'unknown'),
                    "metadata": match['metadata']
                })
        
        return documents
    
    def delete_documents(self, doc_ids: List[str]) -> Dict[str, Any]:
        """Delete documents by IDs"""
        index = self.get_index()
        index.delete(ids=doc_ids)
        
        return {
            "deleted_count": len(doc_ids),
            "status": "completed"
        }
    
    def delete_by_org(self, org_id: str) -> Dict[str, Any]:
        """Delete all documents for an organization"""
        index = self.get_index()
        index.delete(filter={"org_id": org_id})
        
        return {
            "org_id": org_id,
            "status": "deleted"
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        index = self.get_index()
        stats = index.describe_index_stats()
        
        return {
            "total_vectors": stats.get('total_vector_count', 0),
            "dimension": stats.get('dimension', 0),
            "index_name": self.index_name
        }


# Helper functions for easy use

def init_pinecone_index():
    """Initialize Pinecone index - run once on setup"""
    try:
        manager = PineconeManager()
        manager.create_index_if_not_exists()
        return {"status": "success", "message": "Pinecone index initialized"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def ingest_document(doc_id: str, text: str, org_id: str, metadata: Dict = None) -> Dict:
    """Quick function to ingest a single document"""
    try:
        manager = PineconeManager()
        result = manager.upsert_document(
            doc_id=doc_id,
            text=text,
            metadata=metadata or {},
            org_id=org_id
        )
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}


def search_documents(query: str, org_id: str, top_k: int = 5) -> List[Dict]:
    """Quick function to search documents"""
    try:
        manager = PineconeManager()
        results = manager.search(query=query, org_id=org_id, top_k=top_k)
        return results
    except Exception as e:
        return [{"error": str(e)}]


if __name__ == "__main__":
    # Example usage
    print("Pinecone Manager - Example Usage")
    print("=" * 50)
    
    # Initialize index
    result = init_pinecone_index()
    print(f"Initialize: {result}")
    
    # Example: Ingest a document
    # result = ingest_document(
    #     doc_id="doc123",
    #     text="AutoBrain is an AI knowledge assistant.",
    #     org_id="demo-org",
    #     metadata={"source": "docs", "title": "Introduction"}
    # )
    # print(f"Ingest: {result}")
    
    # Example: Search
    # results = search_documents(
    #     query="What is AutoBrain?",
    #     org_id="demo-org"
    # )
    # print(f"Search results: {len(results)} documents found")
