"""SE-Agent capabilities for software engineering tasks."""

from src.capabilities.base import (
    BaseCapability,
    CapabilityType,
    CapabilityRequest,
    CapabilityResponse,
)
from src.capabilities.code_generation import (
    CodeGenerationCapability,
    generate_code,
)
from src.capabilities.test_generation import (
    TestGenerationCapability,
    generate_tests,
)
from src.capabilities.code_review import (
    CodeReviewCapability,
    review_code,
)
from src.capabilities.requirements import (
    RequirementsCapability,
    analyze_requirements,
    generate_requirements,
)
from src.capabilities.documentation import (
    DocumentationCapability,
    generate_docs,
)

__all__ = [
    # Base classes
    "BaseCapability",
    "CapabilityType",
    "CapabilityRequest",
    "CapabilityResponse",
    # Capabilities
    "CodeGenerationCapability",
    "TestGenerationCapability",
    "CodeReviewCapability",
    "RequirementsCapability",
    "DocumentationCapability",
    # Quick functions
    "generate_code",
    "generate_tests",
    "review_code",
    "analyze_requirements",
    "generate_requirements",
    "generate_docs",
]
