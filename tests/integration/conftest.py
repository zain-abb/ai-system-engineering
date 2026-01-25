"""Shared fixtures for integration tests."""

import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator, Dict, Any
from unittest.mock import MagicMock, patch

# Set environment variables before imports to avoid threading issues
os.environ["NUMEXPR_MAX_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["ANONYMIZED_TELEMETRY"] = "false"
os.environ["CHROMA_TELEMETRY"] = "false"

from fastapi.testclient import TestClient


# ============================================================================
# API Test Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def test_client() -> Generator[TestClient, None, None]:
    """
    Create a test client for API integration testing.

    Uses a module scope to reuse the client across tests in a module,
    avoiding repeated app initialization overhead.
    """
    # Mock the API key for testing if not set
    if not os.environ.get("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = "test-api-key-for-integration-tests"

    from src.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_claude_response():
    """Mock Claude API response for tests that don't need real API calls."""
    return MagicMock(
        content="def add(a, b):\n    return a + b",
        usage={"input_tokens": 50, "output_tokens": 100}
    )


# ============================================================================
# Sample Request Fixtures
# ============================================================================

@pytest.fixture
def code_generation_request() -> Dict[str, Any]:
    """Sample code generation request."""
    return {
        "prompt": "Write a Python function to calculate the factorial of a number",
        "task_type": "code_generation",
        "language": "python"
    }


@pytest.fixture
def test_generation_request() -> Dict[str, Any]:
    """Sample test generation request."""
    return {
        "code": """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
""",
        "language": "python",
        "framework": "pytest"
    }


@pytest.fixture
def code_review_request() -> Dict[str, Any]:
    """Sample code review request."""
    return {
        "code": """
import os

def execute_command(user_input):
    os.system(user_input)  # Potential command injection
    return True
""",
        "language": "python",
        "focus": "security"
    }


@pytest.fixture
def auto_classify_request() -> Dict[str, Any]:
    """Request that should trigger auto-classification."""
    return {
        "prompt": "Write unit tests for a login function that validates email and password",
        "task_type": "auto",
        "language": "python"
    }


# ============================================================================
# Sample Code Fixtures
# ============================================================================

@pytest.fixture
def sample_factorial_code() -> str:
    """Correct factorial implementation."""
    return '''
def factorial(n: int) -> int:
    """Calculate factorial of n."""
    if not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return 1
    return n * factorial(n - 1)
'''


@pytest.fixture
def sample_buggy_code() -> str:
    """Code with bugs for testing."""
    return '''
def factorial(n):
    # Bug: doesn't handle n=0 correctly
    return n * factorial(n - 1)
'''


@pytest.fixture
def sample_unsafe_code() -> str:
    """Code with security vulnerabilities."""
    return '''
import os
import pickle
import subprocess

def process_user_data(user_input, data_file):
    # Command injection
    os.system(f"echo {user_input}")

    # Insecure deserialization
    with open(data_file, 'rb') as f:
        data = pickle.load(f)

    # Shell injection
    subprocess.run(user_input, shell=True)

    return data
'''


@pytest.fixture
def sample_hallucinated_code() -> str:
    """Code with hallucinated APIs."""
    return '''
from utils.magic_helpers import auto_optimize
from fake_module import SmartProcessor
import nonexistent_package

def process(data):
    processor = SmartProcessor()
    result = processor.auto_analyze(data)
    return result.smart_transform()
'''


@pytest.fixture
def sample_clean_code() -> str:
    """Well-written, clean code."""
    return '''
from typing import List, Optional
import json

def process_items(items: List[dict]) -> Optional[str]:
    """Process a list of items and return JSON string.

    Args:
        items: List of dictionaries to process

    Returns:
        JSON string of processed items, or None if empty
    """
    if not items:
        return None

    processed = [
        {"id": item.get("id"), "name": item.get("name", "").strip()}
        for item in items
        if item.get("id") is not None
    ]

    return json.dumps(processed, indent=2)
'''


# ============================================================================
# Test Case Fixtures
# ============================================================================

@pytest.fixture
def factorial_test_cases() -> list:
    """Test cases for factorial function."""
    return [
        {"input": "factorial(0)", "expected": "1"},
        {"input": "factorial(1)", "expected": "1"},
        {"input": "factorial(5)", "expected": "120"},
        {"input": "factorial(10)", "expected": "3628800"},
    ]


@pytest.fixture
def fibonacci_test_cases() -> list:
    """Test cases for fibonacci function."""
    return [
        {"input": "fibonacci(0)", "expected": "0"},
        {"input": "fibonacci(1)", "expected": "1"},
        {"input": "fibonacci(10)", "expected": "55"},
    ]


# ============================================================================
# Temporary Directory Fixtures
# ============================================================================

@pytest.fixture
def temp_codebase() -> Generator[Path, None, None]:
    """
    Create a temporary codebase directory for RAG testing.

    Creates a realistic Python project structure with multiple files.
    """
    tmpdir = tempfile.mkdtemp(prefix="se_agent_test_")
    tmppath = Path(tmpdir)

    # Create project structure
    (tmppath / "src").mkdir()
    (tmppath / "src" / "utils").mkdir()
    (tmppath / "tests").mkdir()

    # Create main module
    (tmppath / "src" / "__init__.py").write_text("")
    (tmppath / "src" / "utils" / "__init__.py").write_text("")

    # Create utility files
    (tmppath / "src" / "utils" / "math_utils.py").write_text('''
"""Mathematical utility functions."""

def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b

def divide(a: float, b: float) -> float:
    """Divide a by b with zero check."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def factorial(n: int) -> int:
    """Calculate factorial of n."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return 1
    return n * factorial(n - 1)
''')

    (tmppath / "src" / "utils" / "string_utils.py").write_text('''
"""String utility functions."""

def reverse_string(s: str) -> str:
    """Reverse a string."""
    return s[::-1]

def capitalize_words(s: str) -> str:
    """Capitalize each word in a string."""
    return s.title()

def count_words(s: str) -> int:
    """Count words in a string."""
    if not s or not s.strip():
        return 0
    return len(s.split())

def is_palindrome(s: str) -> bool:
    """Check if a string is a palindrome."""
    cleaned = ''.join(c.lower() for c in s if c.isalnum())
    return cleaned == cleaned[::-1]
''')

    (tmppath / "src" / "validators.py").write_text('''
"""Input validation functions."""

import re
from typing import Optional

def validate_email(email: str) -> bool:
    """Validate email format."""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    """Validate phone number format."""
    if not phone:
        return False
    cleaned = re.sub(r'[\\s\\-\\(\\)]', '', phone)
    return cleaned.isdigit() and 10 <= len(cleaned) <= 15

def validate_url(url: str) -> bool:
    """Validate URL format."""
    if not url:
        return False
    pattern = r'^https?://[\\w\\-]+(\\.[\\w\\-]+)+(/[\\w\\-._~:/?#\\[\\]@!$&\\'()*+,;=]*)?$'
    return bool(re.match(pattern, url))
''')

    # Create test file
    (tmppath / "tests" / "__init__.py").write_text("")
    (tmppath / "tests" / "test_math_utils.py").write_text('''
"""Tests for math utilities."""

import pytest
from src.utils.math_utils import add, multiply, divide, factorial

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0

def test_multiply():
    assert multiply(2, 3) == 6
    assert multiply(0, 5) == 0

def test_divide():
    assert divide(6, 2) == 3.0
    with pytest.raises(ValueError):
        divide(1, 0)

def test_factorial():
    assert factorial(0) == 1
    assert factorial(5) == 120
''')

    yield tmppath

    # Cleanup
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def temp_output_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test outputs."""
    tmpdir = tempfile.mkdtemp(prefix="se_agent_output_")
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================================
# Evaluation Fixtures
# ============================================================================

@pytest.fixture
def evaluation_thresholds() -> Dict[str, float]:
    """Default evaluation thresholds."""
    return {
        "correctness": 0.7,
        "robustness": 0.6,
        "safety": 0.7,
        "hallucination": 0.7,
    }


@pytest.fixture
def evaluation_weights() -> Dict[str, float]:
    """Default evaluation weights."""
    return {
        "correctness": 0.35,
        "robustness": 0.20,
        "safety": 0.25,
        "hallucination": 0.20,
    }


# ============================================================================
# Benchmark Dataset Fixture
# ============================================================================

@pytest.fixture
def mini_benchmark_dataset() -> list:
    """Small benchmark dataset for integration testing."""
    return [
        {
            "id": "test_factorial",
            "input_text": "Write a Python function to calculate factorial",
            "reference_output": "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)",
            "category": "algorithms",
            "difficulty": "easy",
            "metadata": {
                "test_cases": [
                    {"input": "factorial(0)", "expected": "1"},
                    {"input": "factorial(5)", "expected": "120"},
                ]
            }
        },
        {
            "id": "test_reverse_string",
            "input_text": "Write a Python function to reverse a string",
            "reference_output": "def reverse_string(s): return s[::-1]",
            "category": "string_manipulation",
            "difficulty": "easy",
            "metadata": {
                "test_cases": [
                    {"input": "reverse_string('hello')", "expected": "'olleh'"},
                    {"input": "reverse_string('')", "expected": "''"},
                ]
            }
        },
        {
            "id": "test_is_prime",
            "input_text": "Write a Python function to check if a number is prime",
            "reference_output": "def is_prime(n): return n > 1 and all(n % i != 0 for i in range(2, int(n**0.5)+1))",
            "category": "algorithms",
            "difficulty": "medium",
            "metadata": {
                "test_cases": [
                    {"input": "is_prime(2)", "expected": "True"},
                    {"input": "is_prime(4)", "expected": "False"},
                    {"input": "is_prime(17)", "expected": "True"},
                ]
            }
        },
    ]


# ============================================================================
# Skip Markers
# ============================================================================

# Skip if no API key is set (for tests requiring real API calls)
requires_api_key = pytest.mark.skipif(
    os.environ.get("ANTHROPIC_API_KEY", "").startswith("test-"),
    reason="Requires real ANTHROPIC_API_KEY"
)

# Skip slow tests by default
slow_test = pytest.mark.slow
