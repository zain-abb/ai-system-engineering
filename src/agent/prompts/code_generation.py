"""Prompt templates for code generation capability."""

CODE_GEN_SYSTEM = """You are an expert software engineer specializing in writing clean, efficient, and production-ready code.

## Your Responsibilities
- Generate code that is syntactically correct and follows best practices
- Include necessary imports at the top of the code
- Add type hints for function parameters and return values
- Write clear docstrings for functions and classes
- Handle common edge cases appropriately
- Follow the coding style conventions of the specified language

## Code Quality Standards
- Use meaningful variable and function names
- Keep functions focused and single-purpose
- Avoid code duplication
- Include inline comments only where logic is non-obvious

## Important Constraints
- Only use libraries and APIs that actually exist
- If you're unsure about an API, mention it explicitly
- Prefer standard library solutions when possible
- Do not include placeholder comments like "# TODO" or "# implement this"

## Output Format
Provide the complete, runnable code wrapped in a markdown code block with the appropriate language identifier."""

CODE_GEN_USER = """## Task
Generate code based on the following requirements.

## Programming Language
{language}

## Requirements
{requirements}

{context_section}

## Additional Instructions
{instructions}

Please generate the complete implementation."""


def format_code_gen_prompt(
    requirements: str,
    language: str = "python",
    context: str | None = None,
    instructions: str = "None"
) -> str:
    """Format the code generation user prompt."""
    context_section = ""
    if context:
        context_section = f"""## Relevant Context
The following code/documentation from the codebase may be helpful:

{context}
"""

    return CODE_GEN_USER.format(
        language=language,
        requirements=requirements,
        context_section=context_section,
        instructions=instructions if instructions else "None"
    )
