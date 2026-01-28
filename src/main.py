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
from typing import Optional, List
import shutil

import json
import uvicorn
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
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
    model: Optional[str] = None  # Claude model to use


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
    model: Optional[str] = None  # Claude model to use


class TestGenRequest(BaseModel):
    """Request for test generation."""
    code: str
    language: str = "python"
    framework: str = "pytest"
    model: Optional[str] = None  # Claude model to use


class CodeReviewRequest(BaseModel):
    """Request for code review."""
    code: str
    language: str = "python"
    focus: Optional[str] = None
    model: Optional[str] = None  # Claude model to use


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
                options=request.options,
                model=request.model
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
                context=request.context,
                model=request.model
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
                framework=request.framework,
                model=request.model
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
                focus=request.focus,
                model=request.model
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
            "content": msg.content,
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
    """Index a codebase directory for RAG retrieval. Clears existing index first."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        # Clear existing index before reindexing
        if agent.retriever:
            await asyncio.to_thread(agent.retriever.clear)
            logger.info("Cleared existing RAG index before reindexing")

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


@app.delete("/rag/index")
async def clear_rag_index():
    """Clear the RAG index."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    if not agent.retriever:
        raise HTTPException(status_code=503, detail="RAG not available")

    try:
        await asyncio.to_thread(agent.retriever.clear)
        return {"status": "cleared", "message": "RAG index has been cleared"}
    except Exception as e:
        logger.error(f"Failed to clear RAG index: {e}")
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


@app.post("/rag/upload")
async def upload_and_index(
    files: List[UploadFile] = File(...),
    extensions: Optional[str] = Form(None),
    relative_paths: Optional[str] = Form(None)
):
    """Upload files and index them for RAG retrieval.

    Args:
        files: List of files to upload
        extensions: Comma-separated list of file extensions to index (e.g., ".py,.js,.ts")
        relative_paths: JSON array of relative paths corresponding to each file
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    upload_dir = config.upload.upload_directory
    max_file_size = config.upload.max_file_size_mb * 1024 * 1024
    max_total_size = config.upload.max_total_size_mb * 1024 * 1024

    # Parse relative paths if provided
    paths_list: List[str] = []
    if relative_paths:
        try:
            paths_list = json.loads(relative_paths)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid relative_paths JSON")

    # Validate total size
    total_size = 0
    for file in files:
        # Read file size
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)

        if size > max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} exceeds maximum size of {config.upload.max_file_size_mb}MB"
            )
        total_size += size

    if total_size > max_total_size:
        raise HTTPException(
            status_code=400,
            detail=f"Total upload size exceeds maximum of {config.upload.max_total_size_mb}MB"
        )

    try:
        # Clear existing uploads directory contents (not the directory itself, as it may be a volume mount)
        upload_path = os.path.join(upload_dir)
        os.makedirs(upload_path, exist_ok=True)
        for item in os.listdir(upload_path):
            item_path = os.path.join(upload_path, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)

        # Clear existing RAG index
        if agent.retriever:
            await asyncio.to_thread(agent.retriever.clear)
            logger.info("Cleared existing RAG index before upload")

        # Save files with their relative paths
        files_uploaded = 0
        for i, file in enumerate(files):
            # Determine the relative path
            if paths_list and i < len(paths_list):
                rel_path = paths_list[i]
            else:
                rel_path = file.filename or f"file_{i}"

            # Sanitize path to prevent directory traversal
            rel_path = os.path.normpath(rel_path).lstrip(os.sep)
            if rel_path.startswith(".."):
                continue

            # Create full path
            file_path = os.path.join(upload_path, rel_path)

            # Create parent directories
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Write file
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            files_uploaded += 1

        # Parse extensions if provided
        ext_list = None
        if extensions:
            ext_list = [e.strip() for e in extensions.split(",") if e.strip()]

        # Index the uploaded files
        chunk_count = await asyncio.to_thread(
            agent.index_codebase,
            upload_path,
            ext_list
        )

        return {
            "status": "uploaded_and_indexed",
            "files_uploaded": files_uploaded,
            "chunks_indexed": chunk_count,
            "upload_directory": upload_path
        }

    except Exception as e:
        logger.error(f"Upload and index failed: {e}")
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
