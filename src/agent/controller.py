"""Main agent controller for SE-Agent."""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime

from src.services.claude_client import ClaudeClient
from src.config import PROJECT_ROOT

# Persistence directory
DATA_DIR = PROJECT_ROOT / "data" / "persistence"
HISTORY_FILE = DATA_DIR / "conversation_history.json"
from src.agent.router import IntentRouter, IntentClassification
from src.capabilities.base import (
    CapabilityType,
    CapabilityRequest,
    CapabilityResponse,
)
from src.capabilities import (
    CodeGenerationCapability,
    TestGenerationCapability,
    CodeReviewCapability,
    RequirementsCapability,
    DocumentationCapability,
)
from src.streaming.emitter import (
    emit_start,
    emit_complete,
    emit_progress,
    ProcessingStep,
)

logger = logging.getLogger(__name__)

# Lazy import RAG to avoid circular imports and optional dependency
_retriever = None

# RAG persistence directory
RAG_PERSIST_DIR = str(DATA_DIR / "chroma_db")

def _get_retriever():
    """Lazy load the retriever."""
    global _retriever
    if _retriever is None:
        try:
            from src.rag import create_retriever
            _retriever = create_retriever(persist_directory=RAG_PERSIST_DIR)
        except ImportError as e:
            logger.warning(f"RAG module not available: {e}")
            _retriever = False  # Mark as unavailable
    return _retriever if _retriever else None


@dataclass
class ConversationMessage:
    """A single message in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Response from the agent."""
    success: bool
    result: str
    capability_used: Optional[CapabilityType] = None
    intent_classification: Optional[IntentClassification] = None
    usage: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    context_used: Optional[str] = None  # RAG context that was used
    context_sources: Optional[List[str]] = None  # Source files for context


class AgentController:
    """
    Main controller for SE-Agent.

    Orchestrates intent classification, capability routing, and response generation.
    """

    def __init__(
        self,
        client: Optional[ClaudeClient] = None,
        use_llm_routing: bool = True,
        use_rag: bool = True,
        max_history: int = 200
    ):
        """
        Initialize the agent controller.

        Args:
            client: Optional Claude client (creates one if not provided)
            use_llm_routing: Whether to use LLM for intent classification
            use_rag: Whether to use RAG for context retrieval
            max_history: Maximum conversation history to maintain
        """
        self.client = client or ClaudeClient()
        self.router = IntentRouter(self.client, use_llm=use_llm_routing)
        self.use_rag = use_rag
        self.max_history = max_history
        self.conversation_history: List[ConversationMessage] = []
        self._retriever = None  # Lazy loaded

        # Ensure persistence directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Load persisted history
        self._load_history()

        # Initialize capabilities
        self.capabilities = {
            CapabilityType.CODE_GENERATION: CodeGenerationCapability(self.client),
            CapabilityType.TEST_GENERATION: TestGenerationCapability(self.client),
            CapabilityType.CODE_REVIEW: CodeReviewCapability(self.client),
            CapabilityType.REQUIREMENTS: RequirementsCapability(self.client),
            CapabilityType.DOCUMENTATION: DocumentationCapability(self.client),
        }

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("AgentController initialized")

    @property
    def retriever(self):
        """Get the retriever (lazy loaded)."""
        if self._retriever is None and self.use_rag:
            self._retriever = _get_retriever()
        return self._retriever

    def index_codebase(self, directory: str, extensions: Optional[List[str]] = None) -> int:
        """
        Index a codebase for RAG retrieval.

        Args:
            directory: Path to codebase directory
            extensions: Optional list of file extensions to include

        Returns:
            Number of chunks indexed
        """
        if not self.retriever:
            self.logger.warning("RAG not available, skipping indexing")
            return 0

        return self.retriever.index_codebase(directory, extensions)

    def _get_rag_context(
        self,
        query: str,
        capability_type: CapabilityType,
        language: str = "python"
    ) -> tuple[Optional[str], Optional[List[str]]]:
        """
        Get RAG context for a query.

        Args:
            query: The user query
            capability_type: Type of capability being used
            language: Programming language

        Returns:
            Tuple of (context_string, source_files)
        """
        if not self.retriever or not self.use_rag:
            return None, None

        try:
            # Use different retrieval strategies based on capability
            if capability_type == CapabilityType.CODE_GENERATION:
                result = self.retriever.retrieve_for_code_generation(query, language)
            elif capability_type == CapabilityType.TEST_GENERATION:
                result = self.retriever.retrieve_for_test_generation(query, language)
            elif capability_type == CapabilityType.CODE_REVIEW:
                result = self.retriever.retrieve_for_code_review(query, language)
            else:
                result = self.retriever.retrieve(query)

            if result.has_results:
                return result.context, result.file_paths

        except Exception as e:
            self.logger.warning(f"RAG retrieval failed: {e}")

        return None, None

    def process(
        self,
        user_input: str,
        context: Optional[str] = None,
        language: str = "python",
        force_capability: Optional[CapabilityType] = None,
        options: Optional[Dict[str, Any]] = None,
        use_rag: Optional[bool] = None,  # Override instance setting
        model: Optional[str] = None  # Claude model to use
    ) -> AgentResponse:
        """
        Process a user request.

        Args:
            user_input: The user's request
            context: Optional context from RAG or previous code
            language: Programming language (default: python)
            force_capability: Force a specific capability (bypass routing)
            options: Additional options for the capability
            use_rag: Override RAG usage for this request
            model: Claude model to use (e.g., claude-3-5-haiku-20241022)

        Returns:
            AgentResponse with the result
        """
        context_used = None
        context_sources = None

        # Add model to options if specified
        if model:
            options = options or {}
            options["generation_params"] = options.get("generation_params", {})
            options["generation_params"]["model"] = model

        try:
            # Add user message to history
            self._add_to_history("user", user_input)

            # Classify intent (or use forced capability)
            emit_start(ProcessingStep.INTENT_CLASSIFICATION, "Analyzing your request...")
            if force_capability:
                intent = IntentClassification(
                    primary_intent=force_capability,
                    confidence=1.0,
                    secondary_intents=[],
                    reasoning="Capability forced by user"
                )
            else:
                intent = self.router.classify(user_input)

            emit_complete(
                ProcessingStep.INTENT_CLASSIFICATION,
                f"Detected: {intent.primary_intent.value}",
                confidence=intent.confidence,
                intent=intent.primary_intent.value
            )

            self.logger.info(
                f"Intent: {intent.primary_intent.value} "
                f"(confidence: {intent.confidence:.2f})"
            )

            # Get the appropriate capability
            capability = self.capabilities.get(intent.primary_intent)
            if not capability:
                return AgentResponse(
                    success=False,
                    result="",
                    error=f"Unknown capability: {intent.primary_intent}"
                )

            # Get RAG context if not provided and RAG is enabled
            should_use_rag = use_rag if use_rag is not None else self.use_rag
            if context is None and should_use_rag:
                emit_start(ProcessingStep.SEMANTIC_SEARCH, "Searching codebase for context...")
                rag_context, rag_sources = self._get_rag_context(
                    user_input, intent.primary_intent, language
                )
                if rag_context:
                    context = rag_context
                    context_used = rag_context
                    context_sources = rag_sources
                    emit_complete(
                        ProcessingStep.SEMANTIC_SEARCH,
                        f"Found {len(rag_sources or [])} relevant files",
                        candidates_found=len(rag_sources or []),
                        files=rag_sources
                    )
                    self.logger.info(f"RAG context retrieved from {len(rag_sources or [])} files")
                else:
                    emit_complete(
                        ProcessingStep.SEMANTIC_SEARCH,
                        "No relevant context found",
                        candidates_found=0
                    )

            # Build the request
            request = CapabilityRequest(
                input_text=user_input,
                language=language,
                context=context,
                options=options or {}
            )

            # Execute the capability
            emit_start(
                ProcessingStep.LLM_GENERATION,
                f"Generating with Claude ({intent.primary_intent.value})..."
            )
            response = capability.execute(request)

            usage = self.client.get_last_request_usage()
            emit_complete(
                ProcessingStep.LLM_GENERATION,
                "Generation complete",
                output_tokens=usage.get("output_tokens") if usage else None,
                input_tokens=usage.get("input_tokens") if usage else None
            )

            # Add assistant response to history
            if response.success:
                self._add_to_history("assistant", response.result, {
                    "capability": intent.primary_intent.value,
                    "used_rag": context_used is not None
                })

            return AgentResponse(
                success=response.success,
                result=response.result,
                capability_used=intent.primary_intent,
                intent_classification=intent,
                usage=usage,
                error=response.error,
                context_used=context_used,
                context_sources=context_sources
            )

        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            from src.streaming.emitter import emit_error
            emit_error(str(e))
            return AgentResponse(
                success=False,
                result="",
                error=str(e)
            )

    def generate_code(
        self,
        requirements: str,
        language: str = "python",
        context: Optional[str] = None,
        model: Optional[str] = None
    ) -> AgentResponse:
        """Convenience method for code generation."""
        return self.process(
            user_input=requirements,
            context=context,
            language=language,
            force_capability=CapabilityType.CODE_GENERATION,
            model=model
        )

    def generate_tests(
        self,
        code: str,
        language: str = "python",
        framework: str = "pytest",
        model: Optional[str] = None
    ) -> AgentResponse:
        """Convenience method for test generation."""
        return self.process(
            user_input=code,
            language=language,
            force_capability=CapabilityType.TEST_GENERATION,
            options={"framework": framework},
            model=model
        )

    def review_code(
        self,
        code: str,
        language: str = "python",
        focus: Optional[str] = None,
        model: Optional[str] = None
    ) -> AgentResponse:
        """Convenience method for code review."""
        return self.process(
            user_input=code,
            language=language,
            force_capability=CapabilityType.CODE_REVIEW,
            options={"focus": focus} if focus else None,
            model=model
        )

    def analyze_requirements(
        self,
        requirements: str,
        context: Optional[str] = None
    ) -> AgentResponse:
        """Convenience method for requirements analysis."""
        return self.process(
            user_input=requirements,
            context=context,
            force_capability=CapabilityType.REQUIREMENTS
        )

    def generate_docs(
        self,
        content: str,
        language: str = "python",
        doc_type: str = "docstrings"
    ) -> AgentResponse:
        """Convenience method for documentation generation."""
        return self.process(
            user_input=content,
            language=language,
            force_capability=CapabilityType.DOCUMENTATION,
            options={"doc_type": doc_type}
        )

    def _add_to_history(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a message to conversation history."""
        message = ConversationMessage(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.conversation_history.append(message)

        # Trim history if needed
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

        # Persist to disk
        self._save_history()

    def get_conversation_history(self) -> List[ConversationMessage]:
        """Get the conversation history."""
        return self.conversation_history.copy()

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.conversation_history.clear()
        self._save_history()

    def _save_history(self) -> None:
        """Save conversation history to disk."""
        try:
            history_data = []
            for msg in self.conversation_history:
                history_data.append({
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata
                })
            with open(HISTORY_FILE, 'w') as f:
                json.dump(history_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save conversation history: {e}")

    def _load_history(self) -> None:
        """Load conversation history from disk."""
        try:
            if HISTORY_FILE.exists():
                with open(HISTORY_FILE, 'r') as f:
                    history_data = json.load(f)
                for item in history_data:
                    msg = ConversationMessage(
                        role=item["role"],
                        content=item["content"],
                        timestamp=datetime.fromisoformat(item["timestamp"]),
                        metadata=item.get("metadata", {})
                    )
                    self.conversation_history.append(msg)
                logger.info(f"Loaded {len(self.conversation_history)} messages from history")
        except Exception as e:
            logger.warning(f"Failed to load conversation history: {e}")

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics."""
        return self.client.get_usage_stats()


# Convenience function
def create_agent(
    use_llm_routing: bool = True,
    use_rag: bool = True
) -> AgentController:
    """Create a new agent controller with default settings."""
    return AgentController(use_llm_routing=use_llm_routing, use_rag=use_rag)
