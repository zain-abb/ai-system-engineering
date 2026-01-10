"""Code review capability for SE-Agent."""

import re
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

from src.capabilities.base import (
    BaseCapability,
    CapabilityType,
    CapabilityRequest,
    CapabilityResponse,
)
from src.agent.prompts.code_review import (
    CODE_REVIEW_SYSTEM,
    format_code_review_prompt,
)
from src.services.claude_client import ClaudeClient


class IssueSeverity(Enum):
    """Severity levels for code review issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ReviewIssue:
    """A single issue found during code review."""
    severity: IssueSeverity
    category: str  # security, bug, performance, style, etc.
    description: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class CodeReviewResult:
    """Structured result of a code review."""
    summary: str
    issues: List[ReviewIssue] = field(default_factory=list)
    positive_aspects: List[str] = field(default_factory=list)
    raw_review: str = ""

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.CRITICAL)

    @property
    def has_critical_issues(self) -> bool:
        return self.critical_count > 0


class CodeReviewCapability(BaseCapability):
    """Capability for reviewing code for bugs, security issues, and quality."""

    def __init__(self, client: Optional[ClaudeClient] = None):
        super().__init__(client)

    @property
    def capability_type(self) -> CapabilityType:
        return CapabilityType.CODE_REVIEW

    @property
    def system_prompt(self) -> str:
        return CODE_REVIEW_SYSTEM

    def format_prompt(self, request: CapabilityRequest) -> str:
        """Format the code review prompt."""
        return format_code_review_prompt(
            code=request.input_text,
            language=request.language,
            context=request.context,
            focus=request.options.get(
                "focus",
                "General review covering correctness, security, quality, and performance"
            )
        )

    def review(
        self,
        code: str,
        language: str = "python",
        context: Optional[str] = None,
        focus: Optional[str] = None
    ) -> CapabilityResponse:
        """
        Convenience method for code review.

        Args:
            code: The code to review
            language: Programming language (default: python)
            context: Optional project context
            focus: Specific areas to focus on

        Returns:
            CapabilityResponse with review results
        """
        options = {}
        if focus:
            options["focus"] = focus

        request = CapabilityRequest(
            input_text=code,
            language=language,
            context=context,
            options=options
        )
        return self.execute(request)

    def review_for_security(
        self,
        code: str,
        language: str = "python"
    ) -> CapabilityResponse:
        """
        Review code specifically for security vulnerabilities.

        Args:
            code: The code to review
            language: Programming language

        Returns:
            CapabilityResponse with security-focused review
        """
        return self.review(
            code=code,
            language=language,
            focus="Security vulnerabilities including injection attacks, authentication issues, "
                  "data exposure, insecure cryptography, and unsafe deserialization"
        )

    def review_for_performance(
        self,
        code: str,
        language: str = "python"
    ) -> CapabilityResponse:
        """
        Review code specifically for performance issues.

        Args:
            code: The code to review
            language: Programming language

        Returns:
            CapabilityResponse with performance-focused review
        """
        return self.review(
            code=code,
            language=language,
            focus="Performance issues including algorithmic complexity, memory usage, "
                  "unnecessary computations, and inefficient data structures"
        )


def review_code(
    code: str,
    language: str = "python",
    context: Optional[str] = None,
    client: Optional[ClaudeClient] = None
) -> str:
    """
    Quick function for code review.

    Args:
        code: Code to review
        language: Programming language
        context: Optional context
        client: Optional Claude client

    Returns:
        Review results string

    Raises:
        RuntimeError: If review fails
    """
    capability = CodeReviewCapability(client)
    response = capability.review(code, language, context)

    if not response.success:
        raise RuntimeError(f"Code review failed: {response.error}")

    return response.result
