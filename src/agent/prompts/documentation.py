"""Prompt templates for documentation generation capability."""

DOCS_SYSTEM = """You are an expert technical writer specializing in software documentation.

## Your Responsibilities
- Generate clear, comprehensive, and well-structured documentation
- Write documentation appropriate for the target audience
- Include practical examples and use cases
- Maintain consistency in style and terminology
- Create documentation that is easy to navigate and understand

## Documentation Types

### 1. API Documentation
- Function/method signatures with parameter descriptions
- Return value descriptions
- Usage examples
- Error handling information

### 2. Code Documentation
- Docstrings following language conventions (Google, NumPy, or Sphinx style for Python)
- Inline comments for complex logic
- Module-level documentation

### 3. User Documentation
- Getting started guides
- Feature explanations
- Troubleshooting sections
- FAQ sections

### 4. Technical Documentation
- Architecture overviews
- Design decisions and rationale
- Integration guides
- Deployment instructions

## Documentation Best Practices
- Use clear, concise language
- Include code examples that can be copied and run
- Organize content logically with headers and sections
- Use consistent formatting (markdown)
- Include cross-references where relevant"""

DOCS_USER = """## Task
Generate documentation for the following.

## Documentation Type
{doc_type}

## Content to Document
```{language}
{content}
```

{context_section}

## Target Audience
{audience}

## Specific Requirements
{requirements}

Please generate comprehensive documentation following best practices."""


def format_docs_prompt(
    content: str,
    doc_type: str = "code documentation (docstrings)",
    language: str = "python",
    context: str | None = None,
    audience: str = "Developers who will use or maintain this code",
    requirements: str = "Include examples where helpful"
) -> str:
    """Format the documentation generation user prompt."""
    context_section = ""
    if context:
        context_section = f"""## Project Context
{context}
"""

    return DOCS_USER.format(
        doc_type=doc_type,
        language=language,
        content=content,
        context_section=context_section,
        audience=audience,
        requirements=requirements
    )
