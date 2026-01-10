"""Documentation generation capability for SE-Agent."""

from typing import Optional
from enum import Enum

from src.capabilities.base import (
    BaseCapability,
    CapabilityType,
    CapabilityRequest,
    CapabilityResponse,
)
from src.agent.prompts.documentation import (
    DOCS_SYSTEM,
    format_docs_prompt,
)
from src.services.claude_client import ClaudeClient


class DocType(Enum):
    """Types of documentation that can be generated."""
    DOCSTRINGS = "docstrings"
    API = "api"
    README = "readme"
    TUTORIAL = "tutorial"
    ARCHITECTURE = "architecture"


class DocumentationCapability(BaseCapability):
    """Capability for generating documentation."""

    def __init__(self, client: Optional[ClaudeClient] = None):
        super().__init__(client)

    @property
    def capability_type(self) -> CapabilityType:
        return CapabilityType.DOCUMENTATION

    @property
    def system_prompt(self) -> str:
        return DOCS_SYSTEM

    def format_prompt(self, request: CapabilityRequest) -> str:
        """Format the documentation generation prompt."""
        return format_docs_prompt(
            content=request.input_text,
            doc_type=request.options.get("doc_type", "code documentation (docstrings)"),
            language=request.language,
            context=request.context,
            audience=request.options.get("audience", "Developers who will use or maintain this code"),
            requirements=request.options.get("requirements", "Include examples where helpful")
        )

    def generate_docstrings(
        self,
        code: str,
        language: str = "python",
        style: str = "google"
    ) -> CapabilityResponse:
        """
        Generate docstrings for code.

        Args:
            code: The code to document
            language: Programming language
            style: Docstring style (google, numpy, sphinx)

        Returns:
            CapabilityResponse with documented code
        """
        request = CapabilityRequest(
            input_text=code,
            language=language,
            options={
                "doc_type": f"code documentation using {style} style docstrings",
                "requirements": f"Use {style} docstring format. Include type hints in docstrings. "
                               "Document all public functions, classes, and methods."
            }
        )
        return self.execute(request)

    def generate_api_docs(
        self,
        code: str,
        language: str = "python",
        context: Optional[str] = None
    ) -> CapabilityResponse:
        """
        Generate API documentation for code.

        Args:
            code: The code to document
            language: Programming language
            context: Optional project context

        Returns:
            CapabilityResponse with API documentation
        """
        request = CapabilityRequest(
            input_text=code,
            language=language,
            context=context,
            options={
                "doc_type": "API documentation in markdown format",
                "audience": "Developers integrating with or using this API",
                "requirements": "Include function signatures, parameter descriptions, "
                               "return values, exceptions, and usage examples"
            }
        )
        return self.execute(request)

    def generate_readme(
        self,
        project_info: str,
        context: Optional[str] = None
    ) -> CapabilityResponse:
        """
        Generate a README file for a project.

        Args:
            project_info: Information about the project
            context: Optional additional context (e.g., existing code structure)

        Returns:
            CapabilityResponse with README content
        """
        request = CapabilityRequest(
            input_text=project_info,
            context=context,
            options={
                "doc_type": "README.md file",
                "audience": "Developers and users who want to understand and use this project",
                "requirements": "Include: project title, description, installation instructions, "
                               "usage examples, configuration options, and contribution guidelines"
            }
        )
        return self.execute(request)

    def generate_tutorial(
        self,
        topic: str,
        code_examples: Optional[str] = None,
        context: Optional[str] = None
    ) -> CapabilityResponse:
        """
        Generate a tutorial or guide.

        Args:
            topic: The topic to create a tutorial for
            code_examples: Optional code examples to include
            context: Optional additional context

        Returns:
            CapabilityResponse with tutorial content
        """
        input_text = topic
        if code_examples:
            input_text = f"{topic}\n\n## Code Examples\n{code_examples}"

        request = CapabilityRequest(
            input_text=input_text,
            context=context,
            options={
                "doc_type": "step-by-step tutorial",
                "audience": "Developers learning to use this feature or tool",
                "requirements": "Include introduction, prerequisites, step-by-step instructions, "
                               "code examples, common pitfalls, and next steps"
            }
        )
        return self.execute(request)

    def generate_architecture_doc(
        self,
        system_description: str,
        context: Optional[str] = None
    ) -> CapabilityResponse:
        """
        Generate architecture documentation.

        Args:
            system_description: Description of the system/architecture
            context: Optional additional context (e.g., code structure)

        Returns:
            CapabilityResponse with architecture documentation
        """
        request = CapabilityRequest(
            input_text=system_description,
            context=context,
            options={
                "doc_type": "architecture documentation",
                "audience": "Engineers and architects who need to understand system design",
                "requirements": "Include: overview, components, data flow, design decisions, "
                               "integration points, and deployment considerations"
            }
        )
        return self.execute(request)


def generate_docs(
    content: str,
    doc_type: str = "docstrings",
    language: str = "python",
    client: Optional[ClaudeClient] = None
) -> str:
    """
    Quick function for documentation generation.

    Args:
        content: Content to document
        doc_type: Type of documentation
        language: Programming language
        client: Optional Claude client

    Returns:
        Generated documentation string

    Raises:
        RuntimeError: If generation fails
    """
    capability = DocumentationCapability(client)

    if doc_type == "docstrings":
        response = capability.generate_docstrings(content, language)
    elif doc_type == "api":
        response = capability.generate_api_docs(content, language)
    elif doc_type == "readme":
        response = capability.generate_readme(content)
    else:
        # Generic documentation
        request = CapabilityRequest(
            input_text=content,
            language=language,
            options={"doc_type": doc_type}
        )
        response = capability.execute(request)

    if not response.success:
        raise RuntimeError(f"Documentation generation failed: {response.error}")

    return response.result
