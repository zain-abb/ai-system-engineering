"""Main entry point for SE-Agent application."""

# Fix threading conflicts between NumExpr/sentence-transformers and ChromaDB
# MUST be set before any imports that might trigger these libraries
import os
os.environ["NUMEXPR_MAX_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# Disable ChromaDB telemetry to avoid gRPC/protobuf mutex issues
os.environ["ANONYMIZED_TELEMETRY"] = "false"
os.environ["CHROMA_TELEMETRY"] = "false"

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import Optional

import json
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.config import config
from src.agent import AgentController, create_agent
from src.capabilities.base import CapabilityType
from src.streaming import EventEmitter, set_emitter

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.app.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Global agent instance
agent: AgentController | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global agent

    # Startup
    logger.info("Starting SE-Agent...")
    try:
        config.validate()
        agent = create_agent(use_llm_routing=True)
        logger.info("SE-Agent started successfully")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down SE-Agent...")


# Create FastAPI app
app = FastAPI(
    title="SE-Agent",
    description="AI-powered Software Engineering Assistant",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Production build
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class GenerateRequest(BaseModel):
    """Request model for generation tasks."""
    prompt: str
    task_type: Optional[str] = None  # auto, code_generation, test_generation, code_review, requirements, documentation
    context: Optional[str] = None
    language: str = "python"
    options: Optional[dict] = None


class GenerateResponse(BaseModel):
    """Response model for generation."""
    success: bool
    result: str
    task_type: str
    confidence: float
    usage: dict
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    agent_ready: bool
    capabilities: list[str]


class CodeGenRequest(BaseModel):
    """Request for code generation."""
    requirements: str
    language: str = "python"
    context: Optional[str] = None


class TestGenRequest(BaseModel):
    """Request for test generation."""
    code: str
    language: str = "python"
    framework: str = "pytest"


class CodeReviewRequest(BaseModel):
    """Request for code review."""
    code: str
    language: str = "python"
    focus: Optional[str] = None


# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    agent_ready = agent is not None
    return HealthResponse(
        status="healthy" if agent_ready else "degraded",
        version="0.1.0",
        agent_ready=agent_ready,
        capabilities=[ct.value for ct in CapabilityType]
    )


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """
    Generate code, tests, documentation, or analyze requirements.

    If task_type is not specified, the agent will automatically classify the intent.
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    # Map task type to capability
    capability_map = {
        "code_generation": CapabilityType.CODE_GENERATION,
        "test_generation": CapabilityType.TEST_GENERATION,
        "code_review": CapabilityType.CODE_REVIEW,
        "requirements": CapabilityType.REQUIREMENTS,
        "documentation": CapabilityType.DOCUMENTATION,
    }

    force_capability = None
    if request.task_type and request.task_type != "auto":
        force_capability = capability_map.get(request.task_type)

    try:
        response = agent.process(
            user_input=request.prompt,
            context=request.context,
            language=request.language,
            force_capability=force_capability,
            options=request.options
        )

        return GenerateResponse(
            success=response.success,
            result=response.result,
            task_type=response.capability_used.value if response.capability_used else "unknown",
            confidence=response.intent_classification.confidence if response.intent_classification else 0.0,
            usage=response.usage or {},
            error=response.error
        )

    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/stream")
async def generate_stream(request: GenerateRequest):
    """Generic generation with real-time status updates via SSE."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    emitter = EventEmitter()

    # Map task type to capability
    capability_map = {
        "code_generation": CapabilityType.CODE_GENERATION,
        "test_generation": CapabilityType.TEST_GENERATION,
        "code_review": CapabilityType.CODE_REVIEW,
        "requirements": CapabilityType.REQUIREMENTS,
        "documentation": CapabilityType.DOCUMENTATION,
    }

    force_capability = None
    if request.task_type and request.task_type != "auto":
        force_capability = capability_map.get(request.task_type)

    async def event_generator():
        set_emitter(emitter)

        task = asyncio.create_task(
            asyncio.to_thread(
                agent.process,
                user_input=request.prompt,
                context=request.context,
                language=request.language,
                force_capability=force_capability,
                options=request.options
            )
        )

        while not task.done():
            try:
                event = await asyncio.wait_for(emitter.get_event(), timeout=0.1)
                yield f"event: {event.type.value}\ndata: {json.dumps(event.to_dict())}\n\n"
            except asyncio.TimeoutError:
                continue

        while not emitter._queue.empty():
            try:
                event = emitter._queue.get_nowait()
                yield f"event: {event.type.value}\ndata: {json.dumps(event.to_dict())}\n\n"
            except asyncio.QueueEmpty:
                break

        try:
            response = task.result()
            yield f"event: done\ndata: {json.dumps({'type': 'done', 'result': response.result, 'usage': response.usage or {}, 'capability_used': response.capability_used.value if response.capability_used else None, 'success': response.success, 'error': response.error, 'confidence': response.intent_classification.confidence if response.intent_classification else 0.0})}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"

        set_emitter(None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/code/generate")
async def generate_code(request: CodeGenRequest):
    """Generate code from requirements."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    response = agent.generate_code(
        requirements=request.requirements,
        language=request.language,
        context=request.context
    )

    if not response.success:
        raise HTTPException(status_code=500, detail=response.error)

    return {"result": response.result, "usage": response.usage}


@app.post("/code/generate/stream")
async def generate_code_stream(request: CodeGenRequest):
    """Generate code from requirements with real-time status updates via SSE."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    emitter = EventEmitter()

    async def event_generator():
        # Set emitter in context for the current task
        set_emitter(emitter)

        # Run generation in background thread (since it's sync code)
        task = asyncio.create_task(
            asyncio.to_thread(
                agent.generate_code,
                requirements=request.requirements,
                language=request.language,
                context=request.context
            )
        )

        # Stream events while the task is running
        while not task.done():
            try:
                event = await asyncio.wait_for(emitter.get_event(), timeout=0.1)
                yield f"event: {event.type.value}\ndata: {json.dumps(event.to_dict())}\n\n"
            except asyncio.TimeoutError:
                continue

        # Get any remaining events
        while not emitter._queue.empty():
            try:
                event = emitter._queue.get_nowait()
                yield f"event: {event.type.value}\ndata: {json.dumps(event.to_dict())}\n\n"
            except asyncio.QueueEmpty:
                break

        # Get the result and send final done event
        try:
            response = task.result()
            yield f"event: done\ndata: {json.dumps({'type': 'done', 'result': response.result, 'usage': response.usage or {}, 'capability_used': response.capability_used.value if response.capability_used else None, 'success': response.success, 'error': response.error})}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"

        # Clear emitter from context
        set_emitter(None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/tests/generate")
async def generate_tests(request: TestGenRequest):
    """Generate tests for code."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    response = agent.generate_tests(
        code=request.code,
        language=request.language,
        framework=request.framework
    )

    if not response.success:
        raise HTTPException(status_code=500, detail=response.error)

    return {"result": response.result, "usage": response.usage}


@app.post("/tests/generate/stream")
async def generate_tests_stream(request: TestGenRequest):
    """Generate tests for code with real-time status updates via SSE."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    emitter = EventEmitter()

    async def event_generator():
        set_emitter(emitter)

        task = asyncio.create_task(
            asyncio.to_thread(
                agent.generate_tests,
                code=request.code,
                language=request.language,
                framework=request.framework
            )
        )

        while not task.done():
            try:
                event = await asyncio.wait_for(emitter.get_event(), timeout=0.1)
                yield f"event: {event.type.value}\ndata: {json.dumps(event.to_dict())}\n\n"
            except asyncio.TimeoutError:
                continue

        while not emitter._queue.empty():
            try:
                event = emitter._queue.get_nowait()
                yield f"event: {event.type.value}\ndata: {json.dumps(event.to_dict())}\n\n"
            except asyncio.QueueEmpty:
                break

        try:
            response = task.result()
            yield f"event: done\ndata: {json.dumps({'type': 'done', 'result': response.result, 'usage': response.usage or {}, 'capability_used': response.capability_used.value if response.capability_used else None, 'success': response.success, 'error': response.error})}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"

        set_emitter(None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/code/review")
async def review_code(request: CodeReviewRequest):
    """Review code for bugs, security issues, and improvements."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    response = agent.review_code(
        code=request.code,
        language=request.language,
        focus=request.focus
    )

    if not response.success:
        raise HTTPException(status_code=500, detail=response.error)

    return {"result": response.result, "usage": response.usage}


@app.post("/code/review/stream")
async def review_code_stream(request: CodeReviewRequest):
    """Review code with real-time status updates via SSE."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    emitter = EventEmitter()

    async def event_generator():
        set_emitter(emitter)

        task = asyncio.create_task(
            asyncio.to_thread(
                agent.review_code,
                code=request.code,
                language=request.language,
                focus=request.focus
            )
        )

        while not task.done():
            try:
                event = await asyncio.wait_for(emitter.get_event(), timeout=0.1)
                yield f"event: {event.type.value}\ndata: {json.dumps(event.to_dict())}\n\n"
            except asyncio.TimeoutError:
                continue

        while not emitter._queue.empty():
            try:
                event = emitter._queue.get_nowait()
                yield f"event: {event.type.value}\ndata: {json.dumps(event.to_dict())}\n\n"
            except asyncio.QueueEmpty:
                break

        try:
            response = task.result()
            yield f"event: done\ndata: {json.dumps({'type': 'done', 'result': response.result, 'usage': response.usage or {}, 'capability_used': response.capability_used.value if response.capability_used else None, 'success': response.success, 'error': response.error})}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"

        set_emitter(None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/usage")
async def get_usage():
    """Get API usage statistics."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return agent.get_usage_stats()


@app.get("/history")
async def get_history():
    """Get conversation history."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    history = agent.get_conversation_history()
    return [
        {
            "role": msg.role,
            "content": msg.content[:200] + "..." if len(msg.content) > 200 else msg.content,
            "timestamp": msg.timestamp.isoformat(),
            "metadata": msg.metadata
        }
        for msg in history
    ]


@app.delete("/history")
async def clear_history():
    """Clear conversation history."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    agent.clear_history()
    return {"status": "cleared"}


# RAG Endpoints
class IndexRequest(BaseModel):
    """Request for indexing a codebase."""
    directory: str
    extensions: Optional[list[str]] = None


@app.post("/rag/index")
async def index_codebase(request: IndexRequest):
    """Index a codebase directory for RAG retrieval."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        # Run blocking indexing operation in a thread pool to avoid blocking async loop
        chunk_count = await asyncio.to_thread(
            agent.index_codebase,
            request.directory,
            request.extensions
        )
        return {
            "status": "indexed",
            "chunks_indexed": chunk_count,
            "directory": request.directory
        }
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rag/stats")
async def get_rag_stats():
    """Get RAG system statistics."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    if agent.retriever:
        return agent.retriever.get_stats()
    return {"status": "RAG not available"}


class SearchRequest(BaseModel):
    """Request for semantic code search."""
    query: str
    n_results: int = 5
    language: Optional[str] = None


@app.post("/rag/search")
async def search_code(request: SearchRequest):
    """Search indexed codebase for relevant code."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    if not agent.retriever:
        raise HTTPException(status_code=503, detail="RAG not available")

    try:
        filter_dict = {"language": request.language} if request.language else None
        result = agent.retriever.retrieve(
            query=request.query,
            n_results=request.n_results,
            filter_dict=filter_dict
        )

        return {
            "query": result.query,
            "total_results": len(result.results),
            "results": [
                {
                    "file_path": r.file_path,
                    "name": r.name,
                    "chunk_type": r.chunk_type,
                    "score": r.score,
                    "content_preview": r.content[:300] + "..." if len(r.content) > 300 else r.content
                }
                for r in result.results
            ],
            "context": result.context[:1000] + "..." if len(result.context) > 1000 else result.context
        }
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Run the application."""
    logger.info(f"Starting server on {config.app.host}:{config.app.api_port}")
    uvicorn.run(
        "src.main:app",
        host=config.app.host,
        port=config.app.api_port,
        reload=config.app.debug
    )


if __name__ == "__main__":
    main()
