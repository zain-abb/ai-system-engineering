"""ChromaDB vector store for code embeddings."""

# Fix threading conflicts - must be set before importing ANY other modules
import os
os.environ["NUMEXPR_MAX_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# Disable ChromaDB telemetry to avoid gRPC mutex issues
os.environ["ANONYMIZED_TELEMETRY"] = "false"
os.environ["CHROMA_TELEMETRY"] = "false"

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings

from src.config import config
from src.rag.indexer import CodeChunk, ChunkType

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of embedding operation."""
    chunk_id: str
    success: bool
    error: Optional[str] = None


@dataclass
class SearchResult:
    """Result of a similarity search."""
    chunk_id: str
    content: str
    score: float  # similarity score (higher is better)
    metadata: Dict[str, Any]

    @property
    def file_path(self) -> str:
        return self.metadata.get("file_path", "")

    @property
    def chunk_type(self) -> str:
        return self.metadata.get("chunk_type", "")

    @property
    def name(self) -> str:
        return self.metadata.get("name", "")


class EmbeddingFunction:
    """Wrapper for embedding generation using sentence-transformers with PyTorch backend."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding function.

        Args:
            model_name: Name of the sentence-transformers model
        """
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        """Lazy load the embedding model with PyTorch backend only."""
        if self._model is None:
            try:
                # Configure PyTorch for single-threaded operation
                import torch
                torch.set_num_threads(1)
                torch.set_num_interop_threads(1)

                # Disable ONNX Runtime backend in sentence-transformers
                os.environ["SENTENCE_TRANSFORMERS_BACKEND"] = "torch"

                from sentence_transformers import SentenceTransformer

                # Load model explicitly with PyTorch backend
                self._model = SentenceTransformer(
                    self.model_name,
                    device="cpu",
                    backend="torch"  # Force PyTorch, not ONNX
                )
                logger.info(f"Loaded embedding model: {self.model_name} (PyTorch backend)")
            except TypeError:
                # Older sentence-transformers doesn't have backend parameter
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name, device="cpu")
                logger.info(f"Loaded embedding model: {self.model_name}")
            except ImportError as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise
        return self._model

    def __call__(self, input: List[str]) -> List[List[float]]:
        """Generate embeddings for input texts."""
        embeddings = self.model.encode(
            input,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True
        )
        return embeddings.tolist()


class ChromaVectorStore:
    """Vector store using ChromaDB for code chunk storage and retrieval."""

    def __init__(
        self,
        collection_name: Optional[str] = None,
        persist_directory: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize the vector store.

        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory to persist data (for local mode)
            host: ChromaDB server host (for client mode)
            port: ChromaDB server port (for client mode)
            embedding_model: Sentence transformers model name
        """
        self.collection_name = collection_name or config.chroma.collection_name
        self.embedding_function = EmbeddingFunction(embedding_model)

        # Initialize ChromaDB client
        if host or config.chroma.host != "localhost":
            # Use HTTP client for remote ChromaDB
            actual_host = host or config.chroma.host
            actual_port = port or config.chroma.port
            try:
                self.client = chromadb.HttpClient(
                    host=actual_host,
                    port=actual_port
                )
                logger.info(f"Connected to ChromaDB at {actual_host}:{actual_port}")
            except Exception as e:
                logger.warning(f"Could not connect to ChromaDB server: {e}")
                logger.info("Falling back to in-memory ChromaDB")
                self.client = chromadb.Client()
        else:
            # Use persistent client for local development
            if persist_directory:
                # Ensure directory exists
                os.makedirs(persist_directory, exist_ok=True)
                # Use Settings to disable telemetry and configure for single-threaded use
                settings = Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                    is_persistent=True
                )
                self.client = chromadb.PersistentClient(
                    path=persist_directory,
                    settings=settings
                )
                logger.info(f"Using persistent ChromaDB at {persist_directory}")
            else:
                settings = Settings(anonymized_telemetry=False)
                self.client = chromadb.Client(settings)
                logger.info("Using in-memory ChromaDB")

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Code chunks from indexed codebase"}
        )

        logger.info(f"Vector store initialized with collection: {self.collection_name}")

    def add_chunks(self, chunks: List[CodeChunk]) -> List[EmbeddingResult]:
        """
        Add code chunks to the vector store.

        Args:
            chunks: List of CodeChunk objects to add

        Returns:
            List of EmbeddingResult indicating success/failure
        """
        if not chunks:
            return []

        results = []

        # Prepare data for ChromaDB
        ids = []
        documents = []
        metadatas = []

        for chunk in chunks:
            # Create searchable content (combine signature, docstring, and content)
            searchable_content = self._create_searchable_content(chunk)

            ids.append(chunk.chunk_id)
            documents.append(searchable_content)
            metadatas.append({
                "file_path": chunk.file_path,
                "language": chunk.language,
                "chunk_type": chunk.chunk_type.value,
                "name": chunk.name,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "parent_class": chunk.parent_class or "",
                "signature": chunk.signature or "",
                "has_docstring": chunk.docstring is not None,
                "content": chunk.content,  # Store original content in metadata
            })

        try:
            # Generate embeddings
            embeddings = self.embedding_function(documents)

            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )

            results = [
                EmbeddingResult(chunk_id=chunk_id, success=True)
                for chunk_id in ids
            ]
            logger.info(f"Added {len(chunks)} chunks to vector store")

        except Exception as e:
            logger.error(f"Error adding chunks: {e}")
            results = [
                EmbeddingResult(chunk_id=chunk.chunk_id, success=False, error=str(e))
                for chunk in chunks
            ]

        return results

    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search for similar code chunks.

        Args:
            query: Search query
            n_results: Number of results to return
            filter_dict: Optional filter for metadata fields

        Returns:
            List of SearchResult objects
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_function([query])[0]

            # Build where clause
            where = filter_dict if filter_dict else None

            # Query collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"]
            )

            # Convert to SearchResult objects
            search_results = []
            if results and results['ids'] and results['ids'][0]:
                for i, chunk_id in enumerate(results['ids'][0]):
                    # Convert distance to similarity score (ChromaDB uses L2 distance)
                    distance = results['distances'][0][i] if results['distances'] else 0
                    score = 1 / (1 + distance)  # Convert to similarity

                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}

                    search_results.append(SearchResult(
                        chunk_id=chunk_id,
                        content=metadata.get('content', results['documents'][0][i]),
                        score=score,
                        metadata=metadata
                    ))

            return search_results

        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    def search_by_file(
        self,
        query: str,
        file_path: str,
        n_results: int = 5
    ) -> List[SearchResult]:
        """Search within a specific file."""
        return self.search(
            query=query,
            n_results=n_results,
            filter_dict={"file_path": file_path}
        )

    def search_by_type(
        self,
        query: str,
        chunk_type: ChunkType,
        n_results: int = 5
    ) -> List[SearchResult]:
        """Search for specific chunk types (functions, classes, etc.)."""
        return self.search(
            query=query,
            n_results=n_results,
            filter_dict={"chunk_type": chunk_type.value}
        )

    def search_functions(self, query: str, n_results: int = 5) -> List[SearchResult]:
        """Search for functions matching the query."""
        return self.search(
            query=query,
            n_results=n_results,
            filter_dict={"chunk_type": {"$in": ["function", "method"]}}
        )

    def search_classes(self, query: str, n_results: int = 5) -> List[SearchResult]:
        """Search for classes matching the query."""
        return self.search_by_type(query, ChunkType.CLASS, n_results)

    def get_chunk(self, chunk_id: str) -> Optional[SearchResult]:
        """Get a specific chunk by ID."""
        try:
            result = self.collection.get(
                ids=[chunk_id],
                include=["documents", "metadatas"]
            )

            if result and result['ids']:
                metadata = result['metadatas'][0] if result['metadatas'] else {}
                return SearchResult(
                    chunk_id=chunk_id,
                    content=metadata.get('content', result['documents'][0]),
                    score=1.0,
                    metadata=metadata
                )
            return None

        except Exception as e:
            logger.error(f"Error getting chunk {chunk_id}: {e}")
            return None

    def delete_chunks(self, chunk_ids: List[str]) -> bool:
        """Delete chunks by ID."""
        try:
            self.collection.delete(ids=chunk_ids)
            logger.info(f"Deleted {len(chunk_ids)} chunks")
            return True
        except Exception as e:
            logger.error(f"Error deleting chunks: {e}")
            return False

    def delete_file(self, file_path: str) -> bool:
        """Delete all chunks from a specific file."""
        try:
            self.collection.delete(where={"file_path": file_path})
            logger.info(f"Deleted chunks from file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file chunks: {e}")
            return False

    def clear(self) -> bool:
        """Clear all chunks from the collection."""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name
            )
            logger.info("Cleared vector store")
            return True
        except Exception as e:
            logger.error(f"Error clearing vector store: {e}")
            return False

    def count(self) -> int:
        """Get total number of chunks in the store."""
        return self.collection.count()

    def _create_searchable_content(self, chunk: CodeChunk) -> str:
        """Create searchable content from a chunk."""
        parts = []

        # Add signature if available
        if chunk.signature:
            parts.append(chunk.signature)

        # Add docstring if available
        if chunk.docstring:
            parts.append(chunk.docstring)

        # Add content (limited to avoid too long texts)
        content = chunk.content
        if len(content) > 2000:
            content = content[:2000] + "..."
        parts.append(content)

        return "\n\n".join(parts)
