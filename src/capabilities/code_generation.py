"""Code generation capability for SE-Agent."""

import re
from typing import Optional

from src.capabilities.base import (
    BaseCapability,
    CapabilityType,
    CapabilityRequest,
    CapabilityResponse,
)
from src.agent.prompts.code_generation import (
    CODE_GEN_SYSTEM,
    format_code_gen_prompt,
)
from src.services.claude_client import ClaudeClient


class CodeGenerationCapability(BaseCapability):
    """Capability for generating code based on natural language requirements."""

    def __init__(self, client: Optional[ClaudeClient] = None):
        super().__init__(client)

    @property
    def capability_type(self) -> CapabilityType:
        return CapabilityType.CODE_GENERATION

    @property
    def system_prompt(self) -> str:
        return CODE_GEN_SYSTEM

    def format_prompt(self, request: CapabilityRequest) -> str:
        """Format the code generation prompt."""
        return format_code_gen_prompt(
            requirements=request.input_text,
            language=request.language,
            context=request.context,
            instructions=request.options.get("instructions", "")
        )

    def post_process(self, result: str, request: CapabilityRequest) -> str:
        """Extract code from markdown code blocks if present."""
        result = result.strip()

        # Try to extract code from markdown code blocks
        code_block_pattern = r"```(?:\w+)?\n(.*?)```"
        matches = re.findall(code_block_pattern, result, re.DOTALL)

        if matches:
            # Return the largest code block (likely the main implementation)
            return max(matches, key=len).strip()

        return result

    def generate(
        self,
        requirements: str,
        language: str = "python",
        context: Optional[str] = None,
        instructions: Optional[str] = None
    ) -> CapabilityResponse:
        """
        Convenience method for code generation.

        Args:
            requirements: Natural language description of what to generate
            language: Programming language (default: python)
            context: Optional context from codebase
            instructions: Additional instructions

        Returns:
            CapabilityResponse with generated code
        """
        request = CapabilityRequest(
            input_text=requirements,
            language=language,
            context=context,
            options={"instructions": instructions} if instructions else {}
        )
        return self.execute(request)


def generate_code(
    requirements: str,
    language: str = "python",
    context: Optional[str] = None,
    client: Optional[ClaudeClient] = None
) -> str:
    """
    Quick function for code generation.

    Args:
        requirements: What code to generate
        language: Programming language
        context: Optional context
        client: Optional Claude client

    Returns:
        Generated code string

    Raises:
        RuntimeError: If generation fails
    """
    capability = CodeGenerationCapability(client)
    response = capability.generate(requirements, language, context)

    if not response.success:
        raise RuntimeError(f"Code generation failed: {response.error}")

    return response.result
