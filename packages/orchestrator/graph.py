# packages/orchestrator/graph.py
from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

from langgraph.graph import StateGraph, END

# Retrieval helper (our Pinecone adapter)
# Path assumes you mounted ./apps and ./packages as in docker-compose
from apps.api.vector_store.pinecone_store import query as pc_query

# OpenAI SDK (>=1.40.0)
from openai import OpenAI

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-large")  # -3-large (3072) or -3-small (1536)
CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")        # final answer model
MAX_CONTEXT_CHUNKS = int(os.getenv("MAX_CONTEXT_CHUNKS", "6"))

_openai_client = OpenAI()

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------
def embed_text(text: str) -> List[float]:
    """
    Returns a single embedding vector for `text` using OpenAI embeddings.
    """
    # OpenAI Embeddings API (responses differ by SDK version; this matches >=1.0.0)
    resp = _openai_client.embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding


def build_context_from_matches(matches: List[Dict[str, Any]], limit: int = MAX_CONTEXT_CHUNKS) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Given Pinecone query matches, select top `limit` and build a context string
    plus a sources array for the UI.
    We expect each match.metadata to contain a 'text' field; adjust if your schema differs.
    """
    ctx_parts: List[str] = []
    sources: List[Dict[str, Any]] = []

    for m in matches[:limit]:
        meta = m.get("metadata") or {}
        text = meta.get("text") or ""
        if not text:
            continue
        ctx_parts.append(text)
        # Build a source object; customize fields to your metadata
        sources.append({
            "id": m.get("id"),
            "score": m.get("score"),
            "title": meta.get("title") or "",
            "source": meta.get("source") or "",
        })

    return "\n\n".join(ctx_parts), sources


def call_llm_with_context(query: str, context: str) -> str:
    """
    Simple system+user prompt that uses context as retrieval result; returns model text.
    """
    system_prompt = (
        "You are a careful AI assistant. Use the provided context when it is relevant. "
        "If the context is not relevant, still answer concisely and accurately. "
        "Always cite provided sources when applicable."
    )

    user_content = f"USER QUESTION:\n{query}\n\nCONTEXT:\n{context}\n"

    resp = _openai_client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_content},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content or ""


# -----------------------------------------------------------------------------
# Graph state type (dict-based) and node functions
# -----------------------------------------------------------------------------
# LangGraph can work directly with dict state; no Pydantic required here.
StateType = dict  # keys we use: org_id, conversation_id, query, route, retrieved_docs, answer, sources, metadata, tools

def route_node(state: StateType) -> StateType:
    """
    Decide the route. This example always does retrieval; you can add heuristics.
    Return a dict patch.
    """
    # Example heuristic (very simple): if query is short, still retrieve
    route = "retrieve"
    return {"route": route}


def retrieve_node(state: StateType) -> StateType:
    """
    Embed the user query and fetch similar chunks from Pinecone.
    Attach documents (as a list of dicts) into 'retrieved_docs' and accumulate 'sources'.
    Return a dict patch.
    """
    org_id = state.get("org_id", "default")
    query_text = state.get("query", "")

    if not query_text:
        return {"retrieved_docs": [], "sources": []}

    # 1) embed query
    qvec = embed_text(query_text)

    # 2) query pinecone
    res = pc_query(qvec, top_k=MAX_CONTEXT_CHUNKS, namespace=str(org_id)) or {}
    matches = res.get("matches") or []

    # 3) convert matches → context + sources
    context, sources = build_context_from_matches(matches, limit=MAX_CONTEXT_CHUNKS)

    # Save raw docs as well if needed
    docs = []
    for m in matches[:MAX_CONTEXT_CHUNKS]:
        meta = (m.get("metadata") or {}).copy()
        meta["__id"] = m.get("id")
        meta["__score"] = m.get("score")
        docs.append(meta)

    # Stash both context (in metadata) and docs; `answer_node` will use metadata["context"]
    metadata = state.get("metadata") or {}
    metadata["context"] = context

    return {
        "retrieved_docs": docs,
        "sources": sources,
        "metadata": metadata,
    }


def answer_node(state: StateType) -> StateType:
    """
    Compose a final answer using the LLM and any context retrieved.
    Return a dict patch with 'answer' (and optionally updated 'sources').
    """
    query_text = state.get("query", "")
    context = (state.get("metadata") or {}).get("context", "") or ""

    answer = call_llm_with_context(query_text, context)
    # You can also enrich/normalize sources here if needed
    sources = state.get("sources", []) or []
    return {"answer": answer, "sources": sources}


# -----------------------------------------------------------------------------
# Build & export the compiled graph
# -----------------------------------------------------------------------------
def build_graph():
    """
    Build a simple 3-node graph:
      entry -> route -> retrieve -> answer -> END
    You can extend with tool nodes, re-routing, guardrails, etc.
    """
    g = StateGraph(StateType)

    # register nodes
    g.add_node("route", route_node)
    g.add_node("retrieve", retrieve_node)
    g.add_node("answer", answer_node)

    # edges
    g.set_entry_point("route")
    g.add_edge("route", "retrieve")
    g.add_edge("retrieve", "answer")
    g.add_edge("answer", END)

    # You can add a checkpointer here if desired.
    return g.compile()


# >>> Export a top-level 'graph' so `from packages.orchestrator.graph import graph` works
graph = build_graph()
