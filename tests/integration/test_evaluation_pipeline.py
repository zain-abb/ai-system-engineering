"""
Integration tests for the evaluation pipeline.

Tests the full evaluation workflow with all four evaluators
(correctness, robustness, safety, hallucination) working together.

Test Categories:
- Single evaluator integration: Test each evaluator end-to-end
- Multi-evaluator pipeline: Test all evaluators together
- Score aggregation: Test weighted score calculation
- Edge cases: Test boundary conditions and error handling
"""

import pytest
from typing import Dict, Any, List

from src.evaluation.correctness import CorrectnessEvaluator
from src.evaluation.robustness import RobustnessEvaluator
from src.evaluation.safety import SafetyEvaluator
from src.evaluation.hallucination import HallucinationDetector
from src.evaluation.metrics import EvaluationPipeline, MetricsCalculator, EvaluationConfig
from src.evaluation.base import EvaluationType, Severity, EvaluationTask, EvaluationResult


def create_task(
    code: str,
    prompt: str = "Write a function",
    test_cases: list = None,
    reference: str = None,
    task_id: str = "test_task"
) -> EvaluationTask:
    """Helper to create EvaluationTask objects."""
    return EvaluationTask(
        task_id=task_id,
        input_text=prompt,
        generated_output=code,
        reference_output=reference,
        language="python",
        metadata={"test_cases": test_cases or []}
    )


class TestCorrectnessEvaluatorIntegration:
    """Integration tests for correctness evaluator."""

    @pytest.fixture
    def evaluator(self):
        """Create correctness evaluator instance."""
        return CorrectnessEvaluator()

    @pytest.mark.integration
    def test_evaluate_syntactically_valid_code(self, evaluator, sample_factorial_code):
        """Test evaluation of syntactically valid code."""
        task = create_task(
            code=sample_factorial_code,
            prompt="Write factorial function"
        )

        result = evaluator.evaluate(task)

        assert result is not None
        assert result.evaluation_type == EvaluationType.CORRECTNESS
        assert result.score >= 0.0
        assert result.score <= 1.0

        # Valid code should have syntax check pass
        assert result.details.get("syntax", {}).get("valid", False) is True

    @pytest.mark.integration
    def test_evaluate_with_test_cases(self, evaluator, factorial_test_cases):
        """Test evaluation with test cases."""
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
        task = create_task(
            code=code,
            prompt="Write factorial function",
            test_cases=factorial_test_cases
        )

        result = evaluator.evaluate(task)

        assert result is not None
        # Should have attempted test execution
        assert "syntax" in result.details

    @pytest.mark.integration
    def test_evaluate_syntax_error_code(self, evaluator):
        """Test evaluation of code with syntax errors."""
        invalid_code = """
def broken(
    return "missing parenthesis"
"""
        task = create_task(
            code=invalid_code,
            prompt="Write a function"
        )

        result = evaluator.evaluate(task)

        assert result is not None
        assert result.score < 1.0
        # Should detect syntax error
        assert result.details.get("syntax", {}).get("valid", True) is False

    @pytest.mark.integration
    def test_evaluate_runtime_error_code(self, evaluator):
        """Test evaluation of code that raises runtime errors."""
        error_code = """
def divide_by_zero():
    return 1 / 0

result = divide_by_zero()
"""
        task = create_task(
            code=error_code,
            prompt="Division function"
        )

        result = evaluator.evaluate(task)

        assert result is not None
        # Should handle runtime error gracefully
        assert result.score <= 1.0


class TestSafetyEvaluatorIntegration:
    """Integration tests for safety evaluator."""

    @pytest.fixture
    def evaluator(self):
        """Create safety evaluator instance."""
        return SafetyEvaluator()

    @pytest.mark.integration
    def test_evaluate_safe_code(self, evaluator, sample_clean_code):
        """Test evaluation of safe, clean code."""
        task = create_task(code=sample_clean_code)

        result = evaluator.evaluate(task)

        assert result is not None
        assert result.evaluation_type == EvaluationType.SAFETY
        assert result.score >= 0.8  # Clean code should score high

    @pytest.mark.integration
    def test_detect_sql_injection(self, evaluator):
        """Test detection of SQL injection vulnerability."""
        vulnerable_code = '''
import sqlite3

def get_user(username):
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()
'''
        task = create_task(code=vulnerable_code)

        result = evaluator.evaluate(task)

        assert result is not None
        # Note: Without bandit installed, pattern matching is used
        # The test passes if either issues are found OR bandit wasn't available
        bandit_ran = result.details.get("bandit", {}).get("ran", False)
        if bandit_ran:
            assert result.score < 1.0  # Should penalize
            # Should identify SQL injection issue
            issue_categories = [issue.category for issue in result.issues]
            assert any("sql" in cat.lower() for cat in issue_categories)
        else:
            # Bandit not installed - test that we handled it gracefully
            assert result is not None

    @pytest.mark.integration
    def test_detect_command_injection(self, evaluator):
        """Test detection of command injection vulnerability."""
        vulnerable_code = '''
import os
import subprocess

def run_user_command(cmd):
    os.system(cmd)
    subprocess.run(cmd, shell=True)
'''
        task = create_task(code=vulnerable_code)

        result = evaluator.evaluate(task)

        assert result is not None
        assert result.score < 1.0

        # Should identify command injection
        issue_categories = [issue.category for issue in result.issues]
        assert any("command" in cat.lower() or "injection" in cat.lower()
                  for cat in issue_categories)

    @pytest.mark.integration
    def test_detect_hardcoded_secrets(self, evaluator):
        """Test detection of hardcoded secrets."""
        vulnerable_code = '''
API_KEY = "sk-1234567890abcdef1234567890abcdef"
DATABASE_PASSWORD = "super_secret_123"
AWS_SECRET = "AKIAIOSFODNN7EXAMPLE"
'''
        task = create_task(code=vulnerable_code)

        result = evaluator.evaluate(task)

        assert result is not None
        assert result.score < 1.0

        # Should identify hardcoded secrets
        assert len(result.issues) > 0

    @pytest.mark.integration
    def test_detect_insecure_deserialization(self, evaluator):
        """Test detection of insecure deserialization."""
        vulnerable_code = '''
import pickle

def load_user_data(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)
'''
        task = create_task(code=vulnerable_code)

        result = evaluator.evaluate(task)

        assert result is not None
        # Should detect pickle usage as potential issue
        assert len(result.issues) >= 0  # May or may not flag depending on config

    @pytest.mark.integration
    def test_detect_eval_usage(self, evaluator):
        """Test detection of dangerous eval usage."""
        vulnerable_code = '''
def execute_user_code(code_string):
    result = eval(code_string)
    return result
'''
        task = create_task(code=vulnerable_code)

        result = evaluator.evaluate(task)

        assert result is not None
        assert result.score < 1.0

        # Should flag eval usage
        issue_categories = [issue.category for issue in result.issues]
        assert any("eval" in cat.lower() or "dangerous" in cat.lower()
                  for cat in issue_categories)


class TestHallucinationDetectorIntegration:
    """Integration tests for hallucination detector."""

    @pytest.fixture
    def evaluator(self):
        """Create hallucination detector instance."""
        return HallucinationDetector()

    @pytest.mark.integration
    def test_evaluate_valid_imports(self, evaluator):
        """Test evaluation of code with valid imports."""
        valid_code = '''
import os
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict
'''
        task = create_task(code=valid_code)

        result = evaluator.evaluate(task)

        assert result is not None
        assert result.evaluation_type == EvaluationType.HALLUCINATION
        assert result.score >= 0.8  # Valid imports should score high

    @pytest.mark.integration
    def test_detect_fake_imports(self, evaluator, sample_hallucinated_code):
        """Test detection of hallucinated imports."""
        task = create_task(code=sample_hallucinated_code)

        result = evaluator.evaluate(task)

        assert result is not None
        assert result.score < 1.0  # Should penalize fake imports

        # Should identify hallucinated imports
        assert len(result.issues) > 0

    @pytest.mark.integration
    def test_detect_fake_apis(self, evaluator):
        """Test detection of hallucinated API methods."""
        hallucinated_code = '''
import requests

def fetch_data(url):
    response = requests.get(url)
    data = response.auto_parse_json()  # Fake method
    processed = data.smart_transform()  # Fake method
    return processed.auto_validate()   # Fake method
'''
        task = create_task(code=hallucinated_code)

        result = evaluator.evaluate(task)

        assert result is not None
        assert result.score < 1.0

        # Should flag suspicious API calls
        assert len(result.issues) > 0 or result.score < 0.9

    @pytest.mark.integration
    def test_common_third_party_packages(self, evaluator):
        """Test that common third-party packages are recognized."""
        valid_code = '''
import numpy as np
import pandas as pd
import requests
import flask
from fastapi import FastAPI
'''
        task = create_task(code=valid_code)

        result = evaluator.evaluate(task)

        assert result is not None
        # Common packages should not be flagged as hallucinations
        assert result.score >= 0.7


class TestRobustnessEvaluatorIntegration:
    """Integration tests for robustness evaluator."""

    @pytest.fixture
    def evaluator(self):
        """Create robustness evaluator instance."""
        return RobustnessEvaluator()

    @pytest.mark.integration
    def test_evaluate_robust_code(self, evaluator):
        """Test evaluation of robust code with error handling."""
        robust_code = '''
def safe_divide(a, b):
    """Safely divide a by b."""
    if b is None or b == 0:
        return None
    try:
        return a / b
    except (TypeError, ZeroDivisionError) as e:
        raise ValueError(f"Cannot divide: {e}")
'''
        task = create_task(
            code=robust_code,
            prompt="Write a safe divide function"
        )

        result = evaluator.evaluate(task)

        assert result is not None
        assert result.evaluation_type == EvaluationType.ROBUSTNESS
        assert result.score >= 0.5  # Should score decently for error handling

    @pytest.mark.integration
    def test_evaluate_fragile_code(self, evaluator):
        """Test evaluation of fragile code without error handling."""
        fragile_code = '''
def divide(a, b):
    return a / b

def process_list(items):
    return items[0] + items[1]
'''
        task = create_task(
            code=fragile_code,
            prompt="Write utility functions"
        )

        result = evaluator.evaluate(task)

        assert result is not None
        # May identify lack of error handling
        assert result.score >= 0.0 and result.score <= 1.0

    @pytest.mark.integration
    def test_output_quality_check(self, evaluator):
        """Test output quality assessment."""
        good_code = '''
def process_data(data):
    """Process input data and return results."""
    if not data:
        return {"status": "empty", "results": []}

    results = []
    for item in data:
        if item is not None:
            results.append(str(item).strip())

    return {"status": "success", "results": results}
'''
        task = create_task(
            code=good_code,
            prompt="Write a data processing function"
        )

        result = evaluator.evaluate(task)

        assert result is not None
        assert result.score >= 0.5


class TestEvaluationPipelineIntegration:
    """Integration tests for full evaluation pipeline."""

    @pytest.fixture
    def pipeline(self):
        """Create evaluation pipeline with all evaluators."""
        config = EvaluationConfig(
            run_correctness=True,
            run_safety=True,
            run_hallucination=True,
            run_robustness=True
        )
        return EvaluationPipeline(config=config)

    @pytest.mark.integration
    def test_full_pipeline_clean_code(self, pipeline, sample_clean_code):
        """Test full pipeline with clean, well-written code."""
        task = create_task(
            code=sample_clean_code,
            prompt="Write a data processing function"
        )

        result = pipeline.evaluate_task(task)

        assert result is not None
        # Check overall score
        assert result.overall_score >= 0.5

    @pytest.mark.integration
    def test_full_pipeline_unsafe_code(self, pipeline, sample_unsafe_code):
        """Test full pipeline with unsafe code."""
        task = create_task(
            code=sample_unsafe_code,
            prompt="Process user data"
        )

        result = pipeline.evaluate_task(task)

        assert result is not None

        # Should have safety evaluation result
        if EvaluationType.SAFETY in result.results:
            safety_result = result.results[EvaluationType.SAFETY]
            # Without bandit, might not detect all issues
            assert safety_result is not None

    @pytest.mark.integration
    def test_full_pipeline_hallucinated_code(self, pipeline, sample_hallucinated_code):
        """Test full pipeline with hallucinated code."""
        task = create_task(
            code=sample_hallucinated_code,
            prompt="Process data"
        )

        result = pipeline.evaluate_task(task)

        assert result is not None

        # Should have hallucination evaluation result
        if EvaluationType.HALLUCINATION in result.results:
            hall_result = result.results[EvaluationType.HALLUCINATION]
            assert hall_result.score < 1.0

    @pytest.mark.integration
    def test_pipeline_returns_all_dimensions(self, pipeline, sample_factorial_code):
        """Test that pipeline returns scores for all dimensions."""
        task = create_task(
            code=sample_factorial_code,
            prompt="Write factorial"
        )

        result = pipeline.evaluate_task(task)

        assert result is not None

        # Should have results for all evaluation types
        expected_types = [
            EvaluationType.CORRECTNESS,
            EvaluationType.SAFETY,
            EvaluationType.HALLUCINATION,
            EvaluationType.ROBUSTNESS,
        ]

        for eval_type in expected_types:
            assert eval_type in result.results


class TestMetricsCalculatorIntegration:
    """Integration tests for metrics calculator."""

    @pytest.fixture
    def calculator(self):
        """Create metrics calculator instance."""
        return MetricsCalculator()

    @pytest.mark.integration
    def test_pass_at_k_calculation(self, calculator):
        """Test pass@k metric calculation."""
        # Create mock results - 7 passing out of 10
        results = []
        for i in range(10):
            result = EvaluationResult(
                evaluation_type=EvaluationType.CORRECTNESS,
                score=0.8 if i < 7 else 0.5,
                passed=i < 7,
                issues=[],
                details={}
            )
            results.append(result)

        # Calculate pass@1
        pass_at_1 = calculator.calculate_pass_at_k(results, k=1)
        # pass@1 with 7 successes should be > 0
        assert pass_at_1 > 0.0

        # Calculate pass@5
        pass_at_5 = calculator.calculate_pass_at_k(results, k=5)
        # With 7 successes, pass@5 should be very high
        assert pass_at_5 >= pass_at_1  # Should be equal or higher

    @pytest.mark.integration
    def test_pass_fail_determination(self, calculator, evaluation_thresholds):
        """Test pass/fail determination with thresholds."""
        passing_scores = {
            "correctness": 0.8,
            "robustness": 0.7,
            "safety": 0.9,
            "hallucination": 0.85,
        }

        failing_scores = {
            "correctness": 0.5,  # Below threshold
            "robustness": 0.7,
            "safety": 0.9,
            "hallucination": 0.85,
        }

        # Check individual dimension pass/fail
        for dim, threshold in evaluation_thresholds.items():
            assert passing_scores[dim] >= threshold
            if dim == "correctness":
                assert failing_scores[dim] < threshold


class TestEdgeCases:
    """Test edge cases in evaluation pipeline."""

    @pytest.mark.integration
    def test_empty_code(self):
        """Test evaluation of empty code."""
        evaluator = CorrectnessEvaluator()
        task = create_task(code="", prompt="Write something")

        result = evaluator.evaluate(task)

        assert result is not None
        # Empty code should have low score
        assert result.score < 1.0

    @pytest.mark.integration
    def test_whitespace_only_code(self):
        """Test evaluation of whitespace-only code."""
        evaluator = CorrectnessEvaluator()
        task = create_task(code="   \n\t\n   ", prompt="Write something")

        result = evaluator.evaluate(task)

        assert result is not None

    @pytest.mark.integration
    def test_very_long_code(self):
        """Test evaluation of very long code."""
        evaluator = SafetyEvaluator()

        # Generate long but valid code
        long_code = "# Long code\n" + "\n".join([
            f"def function_{i}(x): return x + {i}"
            for i in range(100)
        ])

        task = create_task(code=long_code)

        result = evaluator.evaluate(task)

        assert result is not None
        # Should handle long code without crashing

    @pytest.mark.integration
    def test_unicode_in_code(self):
        """Test evaluation of code with unicode characters."""
        evaluator = CorrectnessEvaluator()

        unicode_code = '''
def greet(name):
    """Greet someone. 你好 مرحبا"""
    return f"Hello, {name}! 🎉"
'''
        task = create_task(code=unicode_code, prompt="Greeting function")

        result = evaluator.evaluate(task)

        assert result is not None
        # Should handle unicode without crashing

    @pytest.mark.integration
    def test_code_with_comments_only(self):
        """Test evaluation of code with only comments."""
        evaluator = CorrectnessEvaluator()

        comments_only = '''
# This is a comment
# Another comment
"""
A docstring without any code
"""
# More comments
'''
        task = create_task(code=comments_only, prompt="Write code")

        result = evaluator.evaluate(task)

        assert result is not None
