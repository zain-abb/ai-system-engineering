"""Test generation capability for SE-Agent."""

import re
from typing import Optional

from src.capabilities.base import (
    BaseCapability,
    CapabilityType,
    CapabilityRequest,
    CapabilityResponse,
)
from src.agent.prompts.test_generation import (
    TEST_GEN_SYSTEM,
    format_test_gen_prompt,
)
from src.services.claude_client import ClaudeClient


class TestGenerationCapability(BaseCapability):
    """Capability for generating test cases for code."""

    def __init__(self, client: Optional[ClaudeClient] = None):
        super().__init__(client)

    @property
    def capability_type(self) -> CapabilityType:
        return CapabilityType.TEST_GENERATION

    @property
    def system_prompt(self) -> str:
        return TEST_GEN_SYSTEM

    def format_prompt(self, request: CapabilityRequest) -> str:
        """Format the test generation prompt."""
        return format_test_gen_prompt(
            code=request.input_text,
            language=request.language,
            framework=request.options.get("framework", "pytest"),
            context=request.context,
            requirements=request.options.get("requirements", "Generate comprehensive tests")
        )

    def post_process(self, result: str, request: CapabilityRequest) -> str:
        """Extract test code from markdown code blocks if present."""
        result = result.strip()

        # Try to extract code from markdown code blocks
        code_block_pattern = r"```(?:\w+)?\n(.*?)```"
        matches = re.findall(code_block_pattern, result, re.DOTALL)

        if matches:
            # Combine all code blocks (tests might be split)
            return "\n\n".join(match.strip() for match in matches)

        return result

    def generate(
        self,
        code: str,
        language: str = "python",
        framework: str = "pytest",
        context: Optional[str] = None,
        requirements: Optional[str] = None
    ) -> CapabilityResponse:
        """
        Convenience method for test generation.

        Args:
            code: The code to generate tests for
            language: Programming language (default: python)
            framework: Testing framework (default: pytest)
            context: Optional additional context
            requirements: Specific test requirements

        Returns:
            CapabilityResponse with generated tests
        """
        options = {"framework": framework}
        if requirements:
            options["requirements"] = requirements

        request = CapabilityRequest(
            input_text=code,
            language=language,
            context=context,
            options=options
        )
        return self.execute(request)


def generate_tests(
    code: str,
    language: str = "python",
    framework: str = "pytest",
    context: Optional[str] = None,
    client: Optional[ClaudeClient] = None
) -> str:
    """
    Quick function for test generation.

    Args:
        code: Code to generate tests for
        language: Programming language
        framework: Testing framework
        context: Optional context
        client: Optional Claude client

    Returns:
        Generated test code string

    Raises:
        RuntimeError: If generation fails
    """
    capability = TestGenerationCapability(client)
    response = capability.generate(code, language, framework, context)

    if not response.success:
        raise RuntimeError(f"Test generation failed: {response.error}")

    return response.result
