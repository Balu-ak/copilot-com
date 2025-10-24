"""
LangGraph Orchestrator - Multi-Agent Workflow for AutoBrain
"""
import os
from typing import Dict, List, Any, AsyncGenerator
from dataclasses import dataclass
import json

try:
    from langgraph.graph import StateGraph, END
except ImportError:
    # Fallback if langgraph not installed
    StateGraph = None
    END = None

@dataclass
class GraphState:
    """State passed through the graph"""
    org_id: str
    conversation_id: str
    query: str
    route: str = ""
    retrieved_docs: List[Dict] = None
    answer: str = ""
    sources: List[Dict] = None
    metadata: Dict = None
    tools: List[str] = None
    
    def __post_init__(self):
        if self.retrieved_docs is None:
            self.retrieved_docs = []
        if self.sources is None:
            self.sources = []
        if self.metadata is None:
            self.metadata = {}
        if self.tools is None:
            self.tools = []

# LLM Provider Interface
class LLMProvider:
    """Abstract LLM provider"""
    
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "openai")
        
    async def completion(self, system: str, user: str, **kwargs) -> str:
        """Generate completion"""
        if self.provider == "openai":
            return await self._openai_completion(system, user, **kwargs)
        elif self.provider == "anthropic":
            return await self._anthropic_completion(system, user, **kwargs)
        else:
            return await self._openai_completion(system, user, **kwargs)
    
    async def _openai_completion(self, system: str, user: str, **kwargs) -> str:
        """OpenAI completion"""
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            response = await client.chat.completions.create(
                model=kwargs.get("model", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 1000)
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error calling OpenAI: {str(e)}"
    
    async def _anthropic_completion(self, system: str, user: str, **kwargs) -> str:
        """Anthropic completion"""
        try:
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            
            response = await client.messages.create(
                model=kwargs.get("model", "claude-3-5-sonnet-20241022"),
                max_tokens=kwargs.get("max_tokens", 1000),
                system=system,
                messages=[{"role": "user", "content": user}]
            )
            return response.content[0].text
        except Exception as e:
            return f"Error calling Anthropic: {str(e)}"

# Initialize LLM
llm = LLMProvider()

# Agent Nodes
async def router_node(state: GraphState) -> GraphState:
    """Route the query to appropriate agent"""
    system = """You are a routing agent. Classify the user's query into one of:
- 'qa': Question answering from knowledge base
- 'summarize': Summarization task
- 'action': Action/task execution (send email, create task, etc.)

Respond with just the category name."""
    
    route = await llm.completion(system, state.query, max_tokens=50)
    route = route.strip().lower()
    
    if route not in ['qa', 'summarize', 'action']:
        route = 'qa'  # default
    
    state.route = route
    state.metadata['route'] = route
    return state

async def retrieve_node(state: GraphState) -> GraphState:
    """Retrieve relevant documents from vector DB"""
    # In production, query Weaviate/Pinecone with org_id filter
    # For demo, return mock documents
    
    mock_docs = [
        {
            "id": "doc1",
            "content": "AutoBrain is a knowledge assistant that helps teams stay organized and informed.",
            "source": "docs",
            "score": 0.95
        },
        {
            "id": "doc2",
            "content": "The system uses RAG (Retrieval Augmented Generation) to provide accurate answers.",
            "source": "docs",
            "score": 0.87
        }
    ]
    
    state.retrieved_docs = mock_docs
    state.sources = [{"id": d["id"], "source": d["source"], "score": d["score"]} for d in mock_docs]
    return state

async def synthesize_node(state: GraphState) -> GraphState:
    """Synthesize answer from retrieved documents"""
    context = "\n\n".join([f"Document {i+1}: {doc['content']}" 
                           for i, doc in enumerate(state.retrieved_docs)])
    
    system = """You are a helpful AI assistant. Use the provided context to answer the user's question.
If the context doesn't contain relevant information, say so clearly.
Provide concise, accurate answers with citations to source documents."""
    
    user_prompt = f"""Context:
{context}

Question: {state.query}

Provide a helpful answer based on the context above."""
    
    answer = await llm.completion(system, user_prompt, max_tokens=500)
    state.answer = answer
    return state

async def action_node(state: GraphState) -> GraphState:
    """Execute actions (email, Slack, Jira, etc.)"""
    system = """You are an action execution agent. Based on the user's request, 
determine what action to take and provide a response."""
    
    # In production, actually execute actions via tools
    # For demo, simulate action
    
    answer = await llm.completion(
        system, 
        f"User wants to: {state.query}\n\nSimulate the action and respond.",
        max_tokens=300
    )
    
    state.answer = answer
    state.metadata['action_taken'] = "simulated"
    return state

# Build the graph
def build_graph():
    """Build the LangGraph workflow"""
    if StateGraph is None:
        return None
    
    graph = StateGraph(GraphState)
    
    # Add nodes
    graph.add_node("router", router_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("action", action_node)
    
    # Set entry point
    graph.set_entry_point("router")
    
    # Add conditional edges based on route
    def route_condition(state: GraphState):
        if state.route == "qa":
            return "retrieve"
        elif state.route == "summarize":
            return "synthesize"
        elif state.route == "action":
            return "action"
        return END
    
    graph.add_conditional_edges(
        "router",
        route_condition,
        {
            "retrieve": "retrieve",
            "synthesize": "synthesize", 
            "action": "action",
            END: END
        }
    )
    
    # After retrieve, synthesize
    graph.add_edge("retrieve", "synthesize")
    
    # End after synthesize or action
    graph.add_edge("synthesize", END)
    graph.add_edge("action", END)
    
    return graph.compile()

# Main execution functions
async def run_graph(ctx: Dict, query: str) -> Dict:
    """Run the orchestration graph"""
    state = GraphState(
        org_id=ctx["org_id"],
        conversation_id=ctx["conversation_id"],
        query=query,
        tools=ctx.get("tools", [])
    )
    
    # Simple fallback if LangGraph not available
    graph = build_graph()
    if graph is None:
        # Fallback: simple pipeline
        state = await router_node(state)
        if state.route in ["qa", "summarize"]:
            state = await retrieve_node(state)
            state = await synthesize_node(state)
        else:
            state = await action_node(state)
    else:
        # Use LangGraph
        result = await graph.ainvoke(state)
        state = result
    
    return {
        "answer": state.answer,
        "sources": state.sources,
        "metadata": state.metadata
    }

async def run_graph_stream(ctx: Dict, query: str) -> AsyncGenerator[Dict, None]:
    """Stream results from the graph"""
    state = GraphState(
        org_id=ctx["org_id"],
        conversation_id=ctx["conversation_id"],
        query=query,
        tools=ctx.get("tools", [])
    )
    
    # Yield routing decision
    yield {"type": "routing", "content": "Analyzing your query..."}
    state = await router_node(state)
    yield {"type": "route", "content": f"Route: {state.route}"}
    
    # Retrieve if needed
    if state.route in ["qa", "summarize"]:
        yield {"type": "retrieving", "content": "Searching knowledge base..."}
        state = await retrieve_node(state)
        yield {"type": "sources", "content": state.sources}
    
    # Synthesize answer
    yield {"type": "thinking", "content": "Generating answer..."}
    if state.route in ["qa", "summarize"]:
        state = await synthesize_node(state)
    else:
        state = await action_node(state)
    
    # Stream answer in chunks
    words = state.answer.split()
    for i in range(0, len(words), 5):
        chunk = " ".join(words[i:i+5])
        yield {"type": "answer", "content": chunk}
    
    yield {"type": "complete", "content": state.answer, "metadata": state.metadata}
