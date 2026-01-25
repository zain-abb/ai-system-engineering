"""Shared fixtures for evaluation tests."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.evaluation.base import (
    EvaluationType,
    Severity,
    Issue,
    EvaluationResult,
    EvaluationTask,
    AggregatedResults,
)


# ============================================================================
# Sample Code Fixtures
# ============================================================================

@pytest.fixture
def sample_valid_python():
    """Valid Python code for testing."""
    return '''
def add(a, b):
    """Add two numbers."""
    return a + b

def multiply(a, b):
    """Multiply two numbers."""
    return a * b

result = add(2, 3)
print(result)
'''


@pytest.fixture
def sample_valid_function():
    """Simple valid function."""
    return '''
def greet(name):
    return f"Hello, {name}!"
'''


@pytest.fixture
def sample_invalid_python():
    """Python code with syntax errors."""
    return '''
def broken_function(
    return "missing parenthesis"
'''


@pytest.fixture
def sample_syntax_error_code():
    """Code with clear syntax error."""
    return '''
if True
    print("missing colon")
'''


@pytest.fixture
def sample_runtime_error_code():
    """Code that will raise a runtime error."""
    return '''
x = 1 / 0
'''


@pytest.fixture
def sample_infinite_loop_code():
    """Code with an infinite loop (for timeout testing)."""
    return '''
while True:
    pass
'''


@pytest.fixture
def sample_vulnerable_sql_injection():
    """Code with SQL injection vulnerability."""
    return '''
import sqlite3

def get_user(username):
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
    return cursor.fetchone()
'''


@pytest.fixture
def sample_vulnerable_command_injection():
    """Code with command injection vulnerability."""
    return '''
import os
import subprocess

def run_command(user_input):
    os.system(f"echo {user_input}")
    subprocess.run(user_input, shell=True)
'''


@pytest.fixture
def sample_vulnerable_hardcoded_secrets():
    """Code with hardcoded secrets."""
    return '''
API_KEY = "sk-1234567890abcdef1234567890abcdef"
password = "super_secret_password123"
secret = "my_secret_token"
'''


@pytest.fixture
def sample_vulnerable_eval():
    """Code with eval usage."""
    return '''
def dynamic_execute(code_string):
    result = eval(code_string)
    return result
'''


@pytest.fixture
def sample_vulnerable_pickle():
    """Code with insecure pickle deserialization."""
    return '''
import pickle

def load_data(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)
'''


@pytest.fixture
def sample_safe_code():
    """Code without security issues."""
    return '''
import json
from typing import Dict, Any

def process_data(data: Dict[str, Any]) -> str:
    """Process data safely."""
    if not data:
        return ""
    return json.dumps(data, indent=2)
'''


@pytest.fixture
def sample_hallucinated_imports():
    """Code with hallucinated/fake imports."""
    return '''
from utils.helpers import process_data
from common.utils import validate_input
from my_module import special_function
import fake_package
'''


@pytest.fixture
def sample_valid_imports():
    """Code with valid standard library imports."""
    return '''
import os
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict
'''


@pytest.fixture
def sample_hallucinated_apis():
    """Code with hallucinated API calls."""
    return '''
import requests

def fetch_data(url):
    response = requests.get(url)
    data = response.auto_parse_json()  # Fake method
    return data.smart_transform()  # Fake method
'''


@pytest.fixture
def sample_code_with_edge_case_handling():
    """Code that handles edge cases properly."""
    return '''
def safe_divide(a, b):
    if not b or b == 0:
        return None
    try:
        return a / b
    except Exception as e:
        raise ValueError(f"Division error: {e}")
'''


@pytest.fixture
def sample_empty_output():
    """Empty output."""
    return ""


@pytest.fixture
def sample_short_output():
    """Very short output."""
    return "x = 1"


@pytest.fixture
def sample_repetitive_output():
    """Output with repetitive patterns."""
    return '''
def process():
    print("hello world")
    print("hello world")
    print("hello world")
    print("hello world")
    print("hello world")
    the same pattern the same pattern the same pattern
    the same pattern the same pattern the same pattern
'''


@pytest.fixture
def sample_truncated_output():
    """Output that appears truncated."""
    return '''
def incomplete_function():
    x = 1
    y = 2
    # More code...
    [truncated]
'''


# ============================================================================
# Task Fixtures
# ============================================================================

@pytest.fixture
def sample_evaluation_task(sample_valid_python):
    """Sample EvaluationTask for testing."""
    return EvaluationTask(
        task_id="test_task_001",
        input_text="Write a function to add two numbers",
        generated_output=sample_valid_python,
        reference_output="def add(a, b): return a + b",
        language="python",
        metadata={"test_cases": []}
    )


@pytest.fixture
def sample_task_with_tests():
    """Task with test cases."""
    code = '''
def add(a, b):
    return a + b
'''
    return EvaluationTask(
        task_id="test_task_with_tests",
        input_text="Write add function",
        generated_output=code,
        language="python",
        metadata={
            "test_cases": [
                {"name": "test_positive", "code": "print(add(2, 3))", "expected": "5"},
                {"name": "test_negative", "code": "print(add(-1, 1))", "expected": "0"},
            ]
        }
    )


@pytest.fixture
def sample_task_failing_tests():
    """Task with failing test cases."""
    code = '''
def add(a, b):
    return a - b  # Bug: subtracts instead of adds
'''
    return EvaluationTask(
        task_id="test_task_failing",
        input_text="Write add function",
        generated_output=code,
        language="python",
        metadata={
            "test_cases": [
                {"name": "test_add", "code": "print(add(2, 3))", "expected": "5"},
            ]
        }
    )


@pytest.fixture
def sample_task_non_python():
    """Task with non-Python code."""
    return EvaluationTask(
        task_id="test_task_js",
        input_text="Write a JavaScript function",
        generated_output="function add(a, b) { return a + b; }",
        language="javascript",
        metadata={}
    )


# ============================================================================
# Issue and Result Fixtures
# ============================================================================

@pytest.fixture
def sample_critical_issue():
    """Sample critical issue."""
    return Issue(
        severity=Severity.CRITICAL,
        category="security",
        description="SQL injection vulnerability found",
        location="line 10",
        suggestion="Use parameterized queries"
    )


@pytest.fixture
def sample_high_issue():
    """Sample high severity issue."""
    return Issue(
        severity=Severity.HIGH,
        category="error",
        description="Runtime error possible",
        location="line 5"
    )


@pytest.fixture
def sample_medium_issue():
    """Sample medium severity issue."""
    return Issue(
        severity=Severity.MEDIUM,
        category="warning",
        description="Potential null pointer"
    )


@pytest.fixture
def sample_low_issue():
    """Sample low severity issue."""
    return Issue(
        severity=Severity.LOW,
        category="style",
        description="Consider using f-strings"
    )


@pytest.fixture
def sample_evaluation_result(sample_critical_issue, sample_high_issue):
    """Sample evaluation result with issues."""
    return EvaluationResult(
        evaluation_type=EvaluationType.SAFETY,
        score=0.5,
        passed=False,
        issues=[sample_critical_issue, sample_high_issue],
        details={"check": "security_scan"},
        timestamp=datetime(2024, 1, 1, 12, 0, 0)
    )


@pytest.fixture
def sample_passing_result():
    """Sample passing evaluation result."""
    return EvaluationResult(
        evaluation_type=EvaluationType.CORRECTNESS,
        score=0.95,
        passed=True,
        issues=[],
        details={"syntax": {"valid": True}}
    )


@pytest.fixture
def sample_aggregated_results(sample_passing_result, sample_evaluation_result):
    """Sample aggregated results."""
    return AggregatedResults(
        total_tasks=10,
        passed_count=7,
        failed_count=3,
        average_score=0.75,
        results_by_type={
            EvaluationType.CORRECTNESS: [sample_passing_result],
            EvaluationType.SAFETY: [sample_evaluation_result],
        },
        summary={"test_summary": True}
    )


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_claude_client():
    """Mocked ClaudeClient for testing."""
    mock = MagicMock()
    mock.generate.return_value = "Generated response from Claude"
    mock.get_usage_stats.return_value = {
        "total_requests": 10,
        "total_cost": 0.05
    }
    return mock


@pytest.fixture
def mock_generate_fn():
    """Mock generate function for robustness testing."""
    def _generate(prompt):
        return f"Generated output for: {prompt[:50]}"
    return _generate


@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response."""
    return {
        "id": "msg_123",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "def add(a, b):\n    return a + b"
            }
        ],
        "model": "claude-3-opus-20240229",
        "usage": {
            "input_tokens": 10,
            "output_tokens": 20
        }
    }


@pytest.fixture
def mock_bandit_output():
    """Mock bandit JSON output."""
    return {
        "results": [
            {
                "issue_severity": "HIGH",
                "issue_confidence": "HIGH",
                "issue_text": "Possible SQL injection",
                "test_id": "B608",
                "line_number": 5,
                "more_info": "https://bandit.readthedocs.io"
            }
        ],
        "metrics": {
            "_totals": {
                "SEVERITY.HIGH": 1,
                "CONFIDENCE.HIGH": 1
            }
        }
    }


@pytest.fixture
def mock_bandit_not_found():
    """Context manager to simulate bandit not being installed."""
    with patch('subprocess.run', side_effect=FileNotFoundError("bandit not found")):
        yield
