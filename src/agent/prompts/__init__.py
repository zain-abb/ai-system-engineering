"""Prompt templates for SE-Agent capabilities."""

from src.agent.prompts.code_generation import CODE_GEN_SYSTEM, CODE_GEN_USER
from src.agent.prompts.test_generation import TEST_GEN_SYSTEM, TEST_GEN_USER
from src.agent.prompts.code_review import CODE_REVIEW_SYSTEM, CODE_REVIEW_USER
from src.agent.prompts.requirements import REQUIREMENTS_SYSTEM, REQUIREMENTS_USER
from src.agent.prompts.documentation import DOCS_SYSTEM, DOCS_USER

__all__ = [
    "CODE_GEN_SYSTEM", "CODE_GEN_USER",
    "TEST_GEN_SYSTEM", "TEST_GEN_USER",
    "CODE_REVIEW_SYSTEM", "CODE_REVIEW_USER",
    "REQUIREMENTS_SYSTEM", "REQUIREMENTS_USER",
    "DOCS_SYSTEM", "DOCS_USER",
]
