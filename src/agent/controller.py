"""Main agent controller for SE-Agent."""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

from src.services.claude_client import ClaudeClient
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

logger = logging.getLogger(__name__)

# Lazy import RAG to avoid circular imports and optional dependency
_retriever = None

def _get_retriever():
    """Lazy load the retriever."""
    global _retriever
    if _retriever is None:
        try:
            from src.rag import create_retriever
            _retriever = create_retriever()
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
        max_history: int = 10
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
        use_rag: Optional[bool] = None  # Override instance setting
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

        Returns:
            AgentResponse with the result
        """
        context_used = None
        context_sources = None

        try:
            # Add user message to history
            self._add_to_history("user", user_input)

            # Classify intent (or use forced capability)
            if force_capability:
                intent = IntentClassification(
                    primary_intent=force_capability,
                    confidence=1.0,
                    secondary_intents=[],
                    reasoning="Capability forced by user"
                )
            else:
                intent = self.router.classify(user_input)

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
                rag_context, rag_sources = self._get_rag_context(
                    user_input, intent.primary_intent, language
                )
                if rag_context:
                    context = rag_context
                    context_used = rag_context
                    context_sources = rag_sources
                    self.logger.info(f"RAG context retrieved from {len(rag_sources or [])} files")

            # Build the request
            request = CapabilityRequest(
                input_text=user_input,
                language=language,
                context=context,
                options=options or {}
            )

            # Execute the capability
            response = capability.execute(request)

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
                usage=self.client.get_usage_stats(),
                error=response.error,
                context_used=context_used,
                context_sources=context_sources
            )

        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            return AgentResponse(
                success=False,
                result="",
                error=str(e)
            )

    def generate_code(
        self,
        requirements: str,
        language: str = "python",
        context: Optional[str] = None
    ) -> AgentResponse:
        """Convenience method for code generation."""
        return self.process(
            user_input=requirements,
            context=context,
            language=language,
            force_capability=CapabilityType.CODE_GENERATION
        )

    def generate_tests(
        self,
        code: str,
        language: str = "python",
        framework: str = "pytest"
    ) -> AgentResponse:
        """Convenience method for test generation."""
        return self.process(
            user_input=code,
            language=language,
            force_capability=CapabilityType.TEST_GENERATION,
            options={"framework": framework}
        )

    def review_code(
        self,
        code: str,
        language: str = "python",
        focus: Optional[str] = None
    ) -> AgentResponse:
        """Convenience method for code review."""
        return self.process(
            user_input=code,
            language=language,
            force_capability=CapabilityType.CODE_REVIEW,
            options={"focus": focus} if focus else None
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

    def get_conversation_history(self) -> List[ConversationMessage]:
        """Get the conversation history."""
        return self.conversation_history.copy()

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.conversation_history.clear()

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
