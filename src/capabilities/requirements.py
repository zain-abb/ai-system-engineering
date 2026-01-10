"""Requirements analysis capability for SE-Agent."""

from typing import Optional
from enum import Enum

from src.capabilities.base import (
    BaseCapability,
    CapabilityType,
    CapabilityRequest,
    CapabilityResponse,
)
from src.agent.prompts.requirements import (
    REQUIREMENTS_SYSTEM,
    format_requirements_prompt,
)
from src.services.claude_client import ClaudeClient


class RequirementsTaskType(Enum):
    """Types of requirements analysis tasks."""
    ANALYZE = "analyze"
    GENERATE = "generate"
    REFINE = "refine"
    USER_STORIES = "user_stories"


class RequirementsCapability(BaseCapability):
    """Capability for analyzing and generating software requirements."""

    def __init__(self, client: Optional[ClaudeClient] = None):
        super().__init__(client)

    @property
    def capability_type(self) -> CapabilityType:
        return CapabilityType.REQUIREMENTS

    @property
    def system_prompt(self) -> str:
        return REQUIREMENTS_SYSTEM

    def format_prompt(self, request: CapabilityRequest) -> str:
        """Format the requirements analysis prompt."""
        task_type = request.options.get(
            "task_type",
            "Analyze the following requirements and identify gaps, ambiguities, and suggest improvements"
        )
        instructions = request.options.get(
            "instructions",
            "Focus on clarity, completeness, and testability"
        )

        return format_requirements_prompt(
            input_text=request.input_text,
            task_type=task_type,
            context=request.context,
            instructions=instructions
        )

    def analyze(
        self,
        requirements: str,
        context: Optional[str] = None
    ) -> CapabilityResponse:
        """
        Analyze existing requirements for gaps and ambiguities.

        Args:
            requirements: The requirements text to analyze
            context: Optional project context

        Returns:
            CapabilityResponse with analysis results
        """
        request = CapabilityRequest(
            input_text=requirements,
            context=context,
            options={
                "task_type": "Analyze the following requirements and identify gaps, "
                            "ambiguities, missing edge cases, and potential issues. "
                            "Provide specific recommendations for improvement.",
                "instructions": "Focus on clarity, completeness, testability, and feasibility"
            }
        )
        return self.execute(request)

    def generate(
        self,
        description: str,
        context: Optional[str] = None
    ) -> CapabilityResponse:
        """
        Generate detailed requirements from a high-level description.

        Args:
            description: High-level description of the feature/system
            context: Optional project context

        Returns:
            CapabilityResponse with generated requirements
        """
        request = CapabilityRequest(
            input_text=description,
            context=context,
            options={
                "task_type": "Generate detailed functional and non-functional requirements "
                            "based on the following description. Include acceptance criteria "
                            "for each requirement.",
                "instructions": "Use standard requirement format with ID, title, description, "
                               "acceptance criteria, and priority"
            }
        )
        return self.execute(request)

    def generate_user_stories(
        self,
        description: str,
        context: Optional[str] = None
    ) -> CapabilityResponse:
        """
        Generate user stories from a description.

        Args:
            description: Description of the feature/functionality
            context: Optional project context

        Returns:
            CapabilityResponse with user stories
        """
        request = CapabilityRequest(
            input_text=description,
            context=context,
            options={
                "task_type": "Generate user stories based on the following description. "
                            "Use the format: As a [user type], I want [goal] so that [benefit].",
                "instructions": "Include acceptance criteria for each user story and "
                               "estimate story points (1, 2, 3, 5, 8, 13)"
            }
        )
        return self.execute(request)

    def refine(
        self,
        requirements: str,
        feedback: str,
        context: Optional[str] = None
    ) -> CapabilityResponse:
        """
        Refine requirements based on feedback.

        Args:
            requirements: The original requirements
            feedback: Feedback to incorporate
            context: Optional project context

        Returns:
            CapabilityResponse with refined requirements
        """
        combined_input = f"""## Original Requirements
{requirements}

## Feedback to Incorporate
{feedback}"""

        request = CapabilityRequest(
            input_text=combined_input,
            context=context,
            options={
                "task_type": "Refine the following requirements based on the provided feedback. "
                            "Incorporate the feedback while maintaining requirement quality.",
                "instructions": "Show what changed and why. Maintain traceability."
            }
        )
        return self.execute(request)


def analyze_requirements(
    requirements: str,
    context: Optional[str] = None,
    client: Optional[ClaudeClient] = None
) -> str:
    """
    Quick function for requirements analysis.

    Args:
        requirements: Requirements to analyze
        context: Optional context
        client: Optional Claude client

    Returns:
        Analysis results string

    Raises:
        RuntimeError: If analysis fails
    """
    capability = RequirementsCapability(client)
    response = capability.analyze(requirements, context)

    if not response.success:
        raise RuntimeError(f"Requirements analysis failed: {response.error}")

    return response.result


def generate_requirements(
    description: str,
    context: Optional[str] = None,
    client: Optional[ClaudeClient] = None
) -> str:
    """
    Quick function for requirements generation.

    Args:
        description: High-level description
        context: Optional context
        client: Optional Claude client

    Returns:
        Generated requirements string

    Raises:
        RuntimeError: If generation fails
    """
    capability = RequirementsCapability(client)
    response = capability.generate(description, context)

    if not response.success:
        raise RuntimeError(f"Requirements generation failed: {response.error}")

    return response.result
