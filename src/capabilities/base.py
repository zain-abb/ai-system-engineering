"""Base class for all SE-Agent capabilities."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from enum import Enum

from src.services.claude_client import ClaudeClient

logger = logging.getLogger(__name__)


class CapabilityType(Enum):
    """Types of capabilities supported by SE-Agent."""
    CODE_GENERATION = "code_generation"
    TEST_GENERATION = "test_generation"
    CODE_REVIEW = "code_review"
    REQUIREMENTS = "requirements"
    DOCUMENTATION = "documentation"


@dataclass
class CapabilityRequest:
    """Request object for capability execution."""
    input_text: str
    language: str = "python"
    context: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CapabilityResponse:
    """Response object from capability execution."""
    success: bool
    result: str
    capability_type: CapabilityType
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @classmethod
    def success_response(
        cls,
        result: str,
        capability_type: CapabilityType,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "CapabilityResponse":
        """Create a successful response."""
        return cls(
            success=True,
            result=result,
            capability_type=capability_type,
            metadata=metadata or {}
        )

    @classmethod
    def error_response(
        cls,
        error: str,
        capability_type: CapabilityType
    ) -> "CapabilityResponse":
        """Create an error response."""
        return cls(
            success=False,
            result="",
            capability_type=capability_type,
            error=error
        )


class BaseCapability(ABC):
    """Abstract base class for all capabilities."""

    def __init__(self, client: Optional[ClaudeClient] = None):
        """Initialize the capability with an optional Claude client."""
        self.client = client or ClaudeClient()
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def capability_type(self) -> CapabilityType:
        """Return the type of this capability."""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this capability."""
        pass

    @abstractmethod
    def format_prompt(self, request: CapabilityRequest) -> str:
        """Format the user prompt for this capability."""
        pass

    def execute(self, request: CapabilityRequest) -> CapabilityResponse:
        """
        Execute the capability with the given request.

        Args:
            request: The capability request containing input and options

        Returns:
            CapabilityResponse with the result or error
        """
        try:
            self.logger.info(f"Executing {self.capability_type.value}")

            # Format the prompt
            user_prompt = self.format_prompt(request)

            # Generate response from Claude
            result = self.client.generate(
                prompt=user_prompt,
                system_prompt=self.system_prompt,
                **request.options.get("generation_params", {})
            )

            if not result:
                return CapabilityResponse.error_response(
                    error="Empty response from LLM",
                    capability_type=self.capability_type
                )

            # Post-process the result
            processed_result = self.post_process(result, request)

            return CapabilityResponse.success_response(
                result=processed_result,
                capability_type=self.capability_type,
                metadata={
                    "language": request.language,
                    "has_context": request.context is not None,
                    "usage": self.client.get_last_request_usage()
                }
            )

        except Exception as e:
            self.logger.error(f"Error in {self.capability_type.value}: {e}")
            return CapabilityResponse.error_response(
                error=str(e),
                capability_type=self.capability_type
            )

    def post_process(self, result: str, request: CapabilityRequest) -> str:
        """
        Post-process the LLM result. Override in subclasses for custom processing.

        Args:
            result: Raw result from the LLM
            request: Original request

        Returns:
            Processed result string
        """
        return result.strip()

    def validate_request(self, request: CapabilityRequest) -> bool:
        """
        Validate the request before execution.

        Args:
            request: The capability request to validate

        Returns:
            True if valid, raises ValueError otherwise
        """
        if not request.input_text or not request.input_text.strip():
            raise ValueError("Input text cannot be empty")
        return True
