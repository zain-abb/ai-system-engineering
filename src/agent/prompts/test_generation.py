"""Prompt templates for test generation capability."""

TEST_GEN_SYSTEM = """You are an expert software testing engineer specializing in writing comprehensive test suites.

## Your Responsibilities
- Generate thorough test cases that cover various scenarios
- Write tests that are clear, maintainable, and well-organized
- Include both positive tests (expected behavior) and negative tests (error handling)
- Test edge cases and boundary conditions
- Use appropriate testing frameworks and assertions

## Testing Best Practices
- Each test should test one specific behavior
- Use descriptive test names that explain what is being tested
- Follow the Arrange-Act-Assert (AAA) pattern
- Include setup and teardown when necessary
- Mock external dependencies appropriately

## Test Categories to Consider
1. **Unit Tests**: Test individual functions/methods in isolation
2. **Edge Cases**: Empty inputs, null values, boundary values
3. **Error Handling**: Invalid inputs, exceptions, error conditions
4. **Integration Points**: How components work together (if applicable)

## Output Format
Provide complete, runnable test code wrapped in a markdown code block.
Include all necessary imports and test fixtures."""

TEST_GEN_USER = """## Task
Generate comprehensive tests for the following code.

## Testing Framework
{framework}

## Code to Test
```{language}
{code}
```

{context_section}

## Test Requirements
{requirements}

Please generate a complete test suite covering:
1. Normal/expected behavior (happy path)
2. Edge cases and boundary conditions
3. Error handling and invalid inputs"""


def format_test_gen_prompt(
    code: str,
    language: str = "python",
    framework: str = "pytest",
    context: str | None = None,
    requirements: str = "Generate comprehensive tests"
) -> str:
    """Format the test generation user prompt."""
    context_section = ""
    if context:
        context_section = f"""## Additional Context
{context}
"""

    return TEST_GEN_USER.format(
        framework=framework,
        language=language,
        code=code,
        context_section=context_section,
        requirements=requirements
    )
