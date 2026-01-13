"""RAG (Retrieval Augmented Generation) module for SE-Agent."""

# Fix threading conflicts - must be set before importing sentence-transformers/chromadb
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

from src.rag.indexer import (
    CodeIndexer,
    CodeChunk,
    ChunkType,
    IndexedFile,
)
from src.rag.vectorstore import (
    ChromaVectorStore,
    SearchResult,
    EmbeddingResult,
)
from src.rag.retriever import (
    CodeRetriever,
    RetrievalConfig,
    RetrievalResult,
    create_retriever,
)

__all__ = [
    # Indexer
    "CodeIndexer",
    "CodeChunk",
    "ChunkType",
    "IndexedFile",
    # Vector Store
    "ChromaVectorStore",
    "SearchResult",
    "EmbeddingResult",
    # Retriever
    "CodeRetriever",
    "RetrievalConfig",
    "RetrievalResult",
    "create_retriever",
]
