"""
AutoBrain API - FastAPI Backend
"""
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import json
import os
from datetime import datetime
import uuid

app = FastAPI(title="AutoBrain API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class ChatRequest(BaseModel):
    org_id: str
    conversation_id: Optional[str] = None
    message: str
    tools: List[str] = []

class IngestRequest(BaseModel):
    org_id: str
    url: str
    source: str = "web"

class SummaryRequest(BaseModel):
    org_id: str
    query: str
    days: int = 7

# In-memory storage (replace with PostgreSQL in production)
conversations = {}
documents = {}

@app.get("/")
async def root():
    return {
        "service": "AutoBrain API",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/auth/verify")
async def verify_auth(request: Request):
    """Verify authentication token and upsert user/org"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = auth_header.replace("Bearer ", "")
    # In production, verify with Clerk/Auth.js
    
    return {
        "user_id": str(uuid.uuid4()),
        "org_id": "demo-org",
        "email": "demo@autobrain.ai",
        "role": "admin"
    }

@app.post("/chat/query")
async def chat_query(req: ChatRequest):
    """Handle chat query with RAG and agent orchestration"""
    from packages.orchestrator.graph import run_graph
    
    conv_id = req.conversation_id or str(uuid.uuid4())
    
    # Initialize conversation if new
    if conv_id not in conversations:
        conversations[conv_id] = {
            "id": conv_id,
            "org_id": req.org_id,
            "messages": []
        }
    
    # Add user message
    conversations[conv_id]["messages"].append({
        "role": "user",
        "content": req.message,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Run orchestration graph
    ctx = {
        "org_id": req.org_id,
        "conversation_id": conv_id,
        "tools": req.tools
    }
    
    result = await run_graph(ctx, req.message)
    
    # Add assistant response
    conversations[conv_id]["messages"].append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result.get("sources", []),
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {
        "conversation_id": conv_id,
        "answer": result["answer"],
        "sources": result.get("sources", []),
        "metadata": result.get("metadata", {})
    }

@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Stream chat response with SSE"""
    async def event_generator():
        from packages.orchestrator.graph import run_graph_stream
        
        conv_id = req.conversation_id or str(uuid.uuid4())
        ctx = {
            "org_id": req.org_id,
            "conversation_id": conv_id,
            "tools": req.tools
        }
        
        async for chunk in run_graph_stream(ctx, req.message):
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0.01)
        
        yield f"data: {json.dumps({'done': True})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@app.post("/ingest/url")
async def ingest_url(req: IngestRequest):
    """Ingest content from URL and index it"""
    doc_id = str(uuid.uuid4())
    
    # In production, enqueue this to Celery/RQ worker
    documents[doc_id] = {
        "id": doc_id,
        "org_id": req.org_id,
        "source": req.source,
        "uri": req.url,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat()
    }
    
    return {
        "doc_id": doc_id,
        "status": "queued",
        "message": "Document queued for ingestion"
    }

@app.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    """Get document status"""
    if doc_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    return documents[doc_id]

@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation history"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversations[conversation_id]

@app.post("/actions/summarize-weekly")
async def schedule_summary(req: SummaryRequest):
    """Schedule weekly summary generation"""
    job_id = str(uuid.uuid4())
    
    return {
        "job_id": job_id,
        "status": "scheduled",
        "message": "Weekly summary job scheduled"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
