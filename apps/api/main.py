# apps/api/main.py
from __future__ import annotations

import os
import logging
from uuid import uuid4
from typing import List, Optional, Any, Dict

from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# IMPORTANT:
# Your LangGraph graph MUST accept a dict state and return a dict state.
# Every node should return partial dict updates (e.g., {"route": ...}, {"retrieved_docs": ...}).
# Do NOT return a Pydantic/dataclass GraphState object from nodes.
from packages.orchestrator.graph import graph

# -----------------------------------------------------------------------------
# App setup
# -----------------------------------------------------------------------------
APP_NAME = os.getenv("APP_NAME", "Autobrain API")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")

app = FastAPI(title=APP_NAME, version=APP_VERSION)

# CORS: allow your Next.js dev origin
frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("autobrain.api")

# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------
class ChatRequest(BaseModel):
    org_id: str = Field(default="demo-org")
    message: str = Field(min_length=1)
    tools: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# -----------------------------------------------------------------------------
# Health & root
# -----------------------------------------------------------------------------
@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> Dict[str, str]:
    return {"service": APP_NAME, "version": APP_VERSION}


# -----------------------------------------------------------------------------
# Chat endpoint
# -----------------------------------------------------------------------------
@app.post("/chat/query", response_model=ChatResponse)
def chat_query(payload: ChatRequest = Body(...)):
    """
    In:
      {
        "org_id": "demo-org",
        "message": "Hello test",
        "tools": [],
        "conversation_id": "optional-uuid"
      }

    Out:
      {
        "conversation_id": "...",
        "answer": "...",
        "sources": [...],
        "metadata": {...}
      }
    """
    try:
        conv_id = payload.conversation_id or str(uuid4())

        # LangGraph requires dict state (NOT a Pydantic object)
        initial_state: Dict[str, Any] = {
            "org_id": payload.org_id,
            "conversation_id": conv_id,
            "query": payload.message,
            "route": "",
            "retrieved_docs": [],
            "answer": "",
            "sources": [],
            "metadata": {},
            "tools": payload.tools or [],
        }

        # Invoke the compiled graph; it must return a dict-like state
        state: Dict[str, Any] = graph.invoke(initial_state)

        return ChatResponse(
            conversation_id=conv_id,
            answer=state.get("answer", ""),
            sources=state.get("sources", []) or [],
            metadata=state.get("metadata", {}) or {},
        )

    except Exception as e:
        # While debugging, surface the error; keep this or replace with generic message for prod
        logger.exception("chat/query failed")
        return JSONResponse(status_code=500, content={"error": str(e)})


# -----------------------------------------------------------------------------
# Optional: local dev runner (usually Docker runs uvicorn directly)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "apps.api.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )

