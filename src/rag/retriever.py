"""Retrieval engine for semantic code search."""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path

from src.rag.indexer import CodeIndexer, CodeChunk, IndexedFile, ChunkType
from src.rag.vectorstore import ChromaVectorStore, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class RetrievalConfig:
    """Configuration for retrieval."""
    initial_k: int = 20  # Initial number of results to fetch
    final_n: int = 5  # Final number of results to return
    similarity_threshold: float = 0.3  # Minimum similarity score
    max_context_tokens: int = 4000  # Maximum tokens in context
    include_related: bool = True  # Include related chunks (called functions, etc.)


@dataclass
class RetrievalResult:
    """Result of a retrieval operation."""
    query: str
    results: List[SearchResult]
    context: str  # Formatted context string
    total_tokens: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_results(self) -> bool:
        return len(self.results) > 0

    @property
    def file_paths(self) -> List[str]:
        return list(set(r.file_path for r in self.results))


class CodeRetriever:
    """
    Retrieval engine for semantic code search.

    Combines code indexing with vector search for intelligent code retrieval.
    """

    def __init__(
        self,
        vector_store: Optional[ChromaVectorStore] = None,
        indexer: Optional[CodeIndexer] = None,
        config: Optional[RetrievalConfig] = None
    ):
        """
        Initialize the retriever.

        Args:
            vector_store: Optional vector store (creates one if not provided)
            indexer: Optional code indexer (creates one if not provided)
            config: Optional retrieval configuration
        """
        self.vector_store = vector_store or ChromaVectorStore()
        self.indexer = indexer or CodeIndexer()
        self.config = config or RetrievalConfig()
        self._indexed_directories: set = set()

        logger.info("CodeRetriever initialized")

    def index_codebase(
        self,
        directory: str,
        extensions: Optional[List[str]] = None,
        force_reindex: bool = False
    ) -> int:
        """
        Index a codebase directory.

        Args:
            directory: Path to directory to index
            extensions: Optional list of file extensions to include
            force_reindex: Force reindexing even if already indexed

        Returns:
            Number of chunks indexed
        """
        directory = str(Path(directory).resolve())

        if directory in self._indexed_directories and not force_reindex:
            logger.info(f"Directory already indexed: {directory}")
            return 0

        if force_reindex:
            # Clear existing chunks from this directory
            self.vector_store.clear()
            self.indexer.clear_index()

        # Index files
        indexed_files = self.indexer.index_directory(directory, extensions)

        # Add chunks to vector store
        all_chunks = []
        for indexed_file in indexed_files:
            all_chunks.extend(indexed_file.chunks)

        if all_chunks:
            self.vector_store.add_chunks(all_chunks)

        self._indexed_directories.add(directory)

        logger.info(f"Indexed {len(indexed_files)} files with {len(all_chunks)} chunks")
        return len(all_chunks)

    def index_file(self, file_path: str) -> int:
        """
        Index a single file.

        Args:
            file_path: Path to file to index

        Returns:
            Number of chunks indexed
        """
        indexed_file = self.indexer.index_file(file_path)
        if indexed_file and indexed_file.chunks:
            self.vector_store.add_chunks(indexed_file.chunks)
            return len(indexed_file.chunks)
        return 0

    def retrieve(
        self,
        query: str,
        n_results: Optional[int] = None,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> RetrievalResult:
        """
        Retrieve relevant code chunks for a query.

        Args:
            query: Search query
            n_results: Number of results (uses config if not specified)
            filter_dict: Optional metadata filters

        Returns:
            RetrievalResult with relevant code chunks
        """
        n = n_results or self.config.final_n

        # Initial search with more results for re-ranking
        initial_results = self.vector_store.search(
            query=query,
            n_results=self.config.initial_k,
            filter_dict=filter_dict
        )

        # Filter by similarity threshold
        filtered_results = [
            r for r in initial_results
            if r.score >= self.config.similarity_threshold
        ]

        # Re-rank and select top results
        ranked_results = self._rerank_results(query, filtered_results)[:n]

        # Build context string
        context = self._build_context(ranked_results)

        # Estimate tokens
        total_tokens = sum(len(r.content.split()) for r in ranked_results)

        return RetrievalResult(
            query=query,
            results=ranked_results,
            context=context,
            total_tokens=total_tokens,
            metadata={
                "initial_count": len(initial_results),
                "filtered_count": len(filtered_results),
                "final_count": len(ranked_results)
            }
        )

    def retrieve_for_code_generation(
        self,
        requirements: str,
        language: str = "python"
    ) -> RetrievalResult:
        """
        Retrieve context relevant for code generation.

        Args:
            requirements: Code generation requirements
            language: Programming language

        Returns:
            RetrievalResult with relevant context
        """
        # Search for similar implementations and related code
        filter_dict = {"language": language} if language else None

        return self.retrieve(
            query=requirements,
            filter_dict=filter_dict
        )

    def retrieve_for_test_generation(
        self,
        code: str,
        language: str = "python"
    ) -> RetrievalResult:
        """
        Retrieve context relevant for test generation.

        Args:
            code: Code to generate tests for
            language: Programming language

        Returns:
            RetrievalResult with existing tests and similar code
        """
        # Extract function/class names from the code for targeted search
        query = f"test {code[:500]}"  # Use beginning of code as query

        # Look for existing tests
        results = self.vector_store.search(
            query=query,
            n_results=self.config.initial_k,
            filter_dict={"language": language}
        )

        # Prioritize test files
        test_results = [r for r in results if "test" in r.file_path.lower()]
        other_results = [r for r in results if "test" not in r.file_path.lower()]

        # Combine with tests first
        combined = test_results + other_results
        final_results = combined[:self.config.final_n]

        context = self._build_context(final_results)
        total_tokens = sum(len(r.content.split()) for r in final_results)

        return RetrievalResult(
            query=query,
            results=final_results,
            context=context,
            total_tokens=total_tokens
        )

    def retrieve_for_code_review(
        self,
        code: str,
        language: str = "python"
    ) -> RetrievalResult:
        """
        Retrieve context relevant for code review.

        Args:
            code: Code to review
            language: Programming language

        Returns:
            RetrievalResult with similar implementations for comparison
        """
        # Find similar code patterns
        return self.retrieve(
            query=code[:1000],  # Use code snippet as query
            filter_dict={"language": language}
        )

    def retrieve_functions(
        self,
        query: str,
        n_results: int = 5
    ) -> RetrievalResult:
        """Retrieve functions matching the query."""
        results = self.vector_store.search_functions(query, n_results)
        context = self._build_context(results)
        total_tokens = sum(len(r.content.split()) for r in results)

        return RetrievalResult(
            query=query,
            results=results,
            context=context,
            total_tokens=total_tokens
        )

    def retrieve_classes(
        self,
        query: str,
        n_results: int = 5
    ) -> RetrievalResult:
        """Retrieve classes matching the query."""
        results = self.vector_store.search_classes(query, n_results)
        context = self._build_context(results)
        total_tokens = sum(len(r.content.split()) for r in results)

        return RetrievalResult(
            query=query,
            results=results,
            context=context,
            total_tokens=total_tokens
        )

    def _rerank_results(
        self,
        query: str,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Re-rank results based on multiple factors.

        Args:
            query: Original query
            results: Initial search results

        Returns:
            Re-ranked results
        """
        if not results:
            return []

        # Score adjustments
        scored_results = []
        for result in results:
            score = result.score

            # Boost for exact name matches
            query_lower = query.lower()
            if result.name.lower() in query_lower or query_lower in result.name.lower():
                score *= 1.3

            # Boost for functions/methods (usually more useful)
            if result.chunk_type in ["function", "method"]:
                score *= 1.1

            # Boost for chunks with docstrings
            if result.metadata.get("has_docstring"):
                score *= 1.1

            # Slight penalty for very long chunks (might be less focused)
            content_length = len(result.content)
            if content_length > 2000:
                score *= 0.9

            scored_results.append((result, score))

        # Sort by adjusted score
        scored_results.sort(key=lambda x: x[1], reverse=True)

        return [r for r, _ in scored_results]

    def _build_context(self, results: List[SearchResult]) -> str:
        """
        Build a context string from search results.

        Args:
            results: Search results to include

        Returns:
            Formatted context string
        """
        if not results:
            return ""

        context_parts = []
        total_tokens = 0

        for result in results:
            # Check token limit
            chunk_tokens = len(result.content.split())
            if total_tokens + chunk_tokens > self.config.max_context_tokens:
                break

            # Format chunk with metadata
            header = f"# File: {result.file_path}"
            if result.name:
                header += f" | {result.chunk_type}: {result.name}"
            if result.metadata.get("start_line"):
                header += f" (lines {result.metadata['start_line']}-{result.metadata['end_line']})"

            chunk_text = f"{header}\n```{result.metadata.get('language', '')}\n{result.content}\n```"
            context_parts.append(chunk_text)
            total_tokens += chunk_tokens

        return "\n\n".join(context_parts)

    def get_stats(self) -> Dict[str, Any]:
        """Get retriever statistics."""
        return {
            "indexed_directories": list(self._indexed_directories),
            "total_chunks": self.vector_store.count(),
            "config": {
                "initial_k": self.config.initial_k,
                "final_n": self.config.final_n,
                "similarity_threshold": self.config.similarity_threshold,
                "max_context_tokens": self.config.max_context_tokens
            }
        }

    def clear(self) -> None:
        """Clear all indexed data."""
        self.vector_store.clear()
        self.indexer.clear_index()
        self._indexed_directories.clear()
        logger.info("Retriever cleared")


def create_retriever(
    persist_directory: Optional[str] = None,
    **kwargs
) -> CodeRetriever:
    """
    Create a retriever with optional persistence.

    Args:
        persist_directory: Directory to persist vector store
        **kwargs: Additional arguments for RetrievalConfig

    Returns:
        Configured CodeRetriever
    """
    vector_store = ChromaVectorStore(persist_directory=persist_directory)
    config = RetrievalConfig(**kwargs) if kwargs else RetrievalConfig()
    return CodeRetriever(vector_store=vector_store, config=config)
