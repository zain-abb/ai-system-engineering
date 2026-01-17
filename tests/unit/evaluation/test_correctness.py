"""Tests for the correctness evaluator."""

import pytest
from unittest.mock import patch, MagicMock
import subprocess

from src.evaluation.base import (
    EvaluationType,
    EvaluationTask,
    Severity,
)
from src.evaluation.correctness import (
    CorrectnessEvaluator,
    evaluate_correctness,
)


class TestCorrectnessEvaluatorInit:
    """Tests for CorrectnessEvaluator initialization."""

    def test_default_initialization(self):
        """Test default evaluator initialization."""
        evaluator = CorrectnessEvaluator()
        assert evaluator.threshold == 0.7
        assert evaluator.timeout == 10
        assert evaluator.allow_execution is True

    def test_custom_initialization(self):
        """Test custom evaluator initialization."""
        evaluator = CorrectnessEvaluator(
            threshold=0.8,
            timeout=30,
            allow_execution=False
        )
        assert evaluator.threshold == 0.8
        assert evaluator.timeout == 30
        assert evaluator.allow_execution is False

    def test_evaluation_type_property(self):
        """Test evaluation_type property returns CORRECTNESS."""
        evaluator = CorrectnessEvaluator()
        assert evaluator.evaluation_type == EvaluationType.CORRECTNESS


class TestSyntaxValidation:
    """Tests for syntax validation functionality."""

    def test_valid_python_syntax(self, sample_valid_python):
        """Test that valid Python code passes syntax check."""
        evaluator = CorrectnessEvaluator(allow_execution=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_valid_python
        )
        result = evaluator.evaluate(task)

        assert result.details["syntax"]["valid"] is True
        assert result.score > 0

    def test_invalid_python_syntax(self, sample_invalid_python):
        """Test that invalid Python code fails syntax check."""
        evaluator = CorrectnessEvaluator(allow_execution=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_invalid_python
        )
        result = evaluator.evaluate(task)

        assert result.details["syntax"]["valid"] is False
        assert "error" in result.details["syntax"]
        assert any(i.category == "syntax_error" for i in result.issues)

    def test_syntax_error_with_line_number(self, sample_syntax_error_code):
        """Test that syntax errors include line number."""
        evaluator = CorrectnessEvaluator(allow_execution=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_syntax_error_code
        )
        result = evaluator.evaluate(task)

        assert result.details["syntax"]["valid"] is False
        assert "line" in result.details["syntax"]
        # Check the issue has location information
        syntax_issue = next(i for i in result.issues if i.category == "syntax_error")
        assert syntax_issue.severity == Severity.CRITICAL
        assert "line" in syntax_issue.location

    def test_empty_code_syntax(self):
        """Test syntax check with empty code."""
        evaluator = CorrectnessEvaluator(allow_execution=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=""
        )
        result = evaluator.evaluate(task)

        # Empty string is valid Python syntax
        assert result.details["syntax"]["valid"] is True

    def test_whitespace_only_code_syntax(self):
        """Test syntax check with whitespace-only code."""
        evaluator = CorrectnessEvaluator(allow_execution=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output="   \n\t   \n"
        )
        result = evaluator.evaluate(task)

        # Whitespace is valid Python syntax
        assert result.details["syntax"]["valid"] is True

    def test_non_python_language_syntax(self, sample_task_non_python):
        """Test syntax check for non-Python code."""
        evaluator = CorrectnessEvaluator(allow_execution=False)
        result = evaluator.evaluate(sample_task_non_python)

        # Non-Python code should pass basic check (not empty)
        assert result.details["syntax"]["valid"] is True
        assert result.details["syntax"]["language"] == "javascript"


class TestCodeExecution:
    """Tests for code execution functionality."""

    def test_successful_execution(self, sample_valid_python):
        """Test successful code execution."""
        evaluator = CorrectnessEvaluator(allow_execution=True)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_valid_python
        )
        result = evaluator.evaluate(task)

        assert "execution" in result.details
        assert result.details["execution"]["success"] is True

    def test_execution_with_runtime_error(self, sample_runtime_error_code):
        """Test execution with runtime error."""
        evaluator = CorrectnessEvaluator(allow_execution=True)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_runtime_error_code
        )
        result = evaluator.evaluate(task)

        assert "execution" in result.details
        assert result.details["execution"]["success"] is False
        assert "error" in result.details["execution"]
        # Should have an execution_error issue
        assert any(i.category == "execution_error" for i in result.issues)

    def test_execution_timeout(self, sample_infinite_loop_code):
        """Test execution timeout handling."""
        evaluator = CorrectnessEvaluator(allow_execution=True, timeout=1)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_infinite_loop_code
        )
        result = evaluator.evaluate(task)

        assert "execution" in result.details
        assert result.details["execution"]["success"] is False
        assert "timeout" in result.details["execution"]["error"].lower()

    def test_execution_disabled(self, sample_valid_python):
        """Test that execution is skipped when disabled."""
        evaluator = CorrectnessEvaluator(allow_execution=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_valid_python
        )
        result = evaluator.evaluate(task)

        # Execution should not be in details when disabled
        assert "execution" not in result.details

    def test_execution_skipped_for_invalid_syntax(self, sample_invalid_python):
        """Test execution is skipped when syntax is invalid."""
        evaluator = CorrectnessEvaluator(allow_execution=True)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_invalid_python
        )
        result = evaluator.evaluate(task)

        # Execution should not run if syntax fails
        assert "execution" not in result.details

    def test_execution_skipped_for_non_python(self, sample_task_non_python):
        """Test execution is skipped for non-Python code."""
        evaluator = CorrectnessEvaluator(allow_execution=True)
        result = evaluator.evaluate(sample_task_non_python)

        # Execution should not run for non-Python
        assert "execution" not in result.details


class TestTestCaseExecution:
    """Tests for test case execution functionality."""

    def test_passing_test_cases(self, sample_task_with_tests):
        """Test with passing test cases."""
        evaluator = CorrectnessEvaluator(allow_execution=True)
        result = evaluator.evaluate(sample_task_with_tests)

        assert "tests" in result.details
        assert result.details["tests"]["pass_rate"] == 1.0
        assert result.details["tests"]["passed"] == 2
        assert result.details["tests"]["failed"] == 0

    def test_failing_test_cases(self, sample_task_failing_tests):
        """Test with failing test cases."""
        evaluator = CorrectnessEvaluator(allow_execution=True)
        result = evaluator.evaluate(sample_task_failing_tests)

        assert "tests" in result.details
        assert result.details["tests"]["pass_rate"] < 1.0
        assert len(result.details["tests"]["failed_tests"]) > 0
        # Should have test_failure issues
        assert any(i.category == "test_failure" for i in result.issues)

    def test_no_test_cases(self, sample_valid_function):
        """Test with no test cases provided."""
        evaluator = CorrectnessEvaluator(allow_execution=True)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_valid_function,
            metadata={}
        )
        result = evaluator.evaluate(task)

        # Tests section should not be present
        assert "tests" not in result.details

    def test_test_execution_skipped_when_disabled(self, sample_task_with_tests):
        """Test that test cases are skipped when execution is disabled."""
        evaluator = CorrectnessEvaluator(allow_execution=False)
        result = evaluator.evaluate(sample_task_with_tests)

        # Tests should not run when execution is disabled
        assert "tests" not in result.details

    def test_test_with_expected_output_check(self):
        """Test that expected output is properly checked."""
        code = '''
def greet(name):
    return f"Hello, {name}!"
'''
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=code,
            metadata={
                "test_cases": [
                    {"name": "test_greet", "code": "print(greet('World'))", "expected": "Hello, World!"}
                ]
            }
        )
        evaluator = CorrectnessEvaluator(allow_execution=True)
        result = evaluator.evaluate(task)

        assert "tests" in result.details
        assert result.details["tests"]["pass_rate"] == 1.0


class TestSemanticSimilarity:
    """Tests for semantic similarity calculation."""

    def test_similarity_with_reference(self):
        """Test similarity calculation with reference output."""
        code = "def add(a, b): return a + b"
        reference = "def add(x, y): return x + y"

        evaluator = CorrectnessEvaluator(allow_execution=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=code,
            reference_output=reference
        )
        result = evaluator.evaluate(task)

        assert "similarity" in result.details
        assert 0 <= result.details["similarity"] <= 1

    def test_similarity_identical_code(self):
        """Test similarity with identical code."""
        code = "def add(a, b): return a + b"

        evaluator = CorrectnessEvaluator(allow_execution=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=code,
            reference_output=code
        )
        result = evaluator.evaluate(task)

        assert result.details["similarity"] == 1.0

    def test_similarity_completely_different(self):
        """Test similarity with completely different code."""
        code = "xyz abc"
        reference = "123 456"

        evaluator = CorrectnessEvaluator(allow_execution=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=code,
            reference_output=reference
        )
        result = evaluator.evaluate(task)

        assert result.details["similarity"] == 0.0

    def test_similarity_no_reference(self, sample_valid_function):
        """Test that similarity is skipped when no reference is provided."""
        evaluator = CorrectnessEvaluator(allow_execution=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_valid_function
        )
        result = evaluator.evaluate(task)

        assert "similarity" not in result.details

    def test_similarity_empty_code(self):
        """Test similarity with empty code."""
        evaluator = CorrectnessEvaluator(allow_execution=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output="",
            reference_output="def foo(): pass"
        )
        result = evaluator.evaluate(task)

        assert result.details["similarity"] == 0.0

    def test_similarity_empty_reference(self, sample_valid_function):
        """Test similarity with empty reference - skipped since empty is falsy."""
        evaluator = CorrectnessEvaluator(allow_execution=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_valid_function,
            reference_output=""
        )
        result = evaluator.evaluate(task)

        # Empty reference is falsy, so similarity check is skipped
        assert "similarity" not in result.details


class TestScoreCalculation:
    """Tests for score calculation."""

    def test_score_syntax_only(self, sample_valid_function):
        """Test score when only syntax is checked."""
        evaluator = CorrectnessEvaluator(allow_execution=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_valid_function
        )
        result = evaluator.evaluate(task)

        # With only syntax passing, score should be 1.0
        assert result.score == 1.0
        assert result.passed is True

    def test_score_with_failed_syntax(self, sample_invalid_python):
        """Test score when syntax fails."""
        evaluator = CorrectnessEvaluator(allow_execution=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_invalid_python
        )
        result = evaluator.evaluate(task)

        assert result.score == 0.0
        assert result.passed is False

    def test_score_averaged_across_checks(self):
        """Test that score is averaged across all checks."""
        code = "def add(a, b): return a + b"
        reference = "def subtract(a, b): return a - b"

        evaluator = CorrectnessEvaluator(allow_execution=True)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=code,
            reference_output=reference
        )
        result = evaluator.evaluate(task)

        # Score should be average of: syntax (1.0), execution (1.0), similarity (<1.0)
        assert 0 < result.score < 1.0


class TestCheckSyntaxOnly:
    """Tests for check_syntax_only method."""

    def test_check_syntax_only_valid(self, sample_valid_python):
        """Test check_syntax_only with valid code."""
        evaluator = CorrectnessEvaluator()
        assert evaluator.check_syntax_only(sample_valid_python) is True

    def test_check_syntax_only_invalid(self, sample_invalid_python):
        """Test check_syntax_only with invalid code."""
        evaluator = CorrectnessEvaluator()
        assert evaluator.check_syntax_only(sample_invalid_python) is False

    def test_check_syntax_only_non_python(self):
        """Test check_syntax_only with non-Python code."""
        evaluator = CorrectnessEvaluator()
        # Non-Python is just checked for non-empty
        assert evaluator.check_syntax_only("function foo() {}", "javascript") is True
        assert evaluator.check_syntax_only("", "javascript") is False


class TestIndentCode:
    """Tests for _indent_code helper method."""

    def test_indent_code_default(self):
        """Test code indentation with default spaces."""
        evaluator = CorrectnessEvaluator()
        code = "line1\nline2\nline3"
        indented = evaluator._indent_code(code)

        lines = indented.split('\n')
        assert all(line.startswith("    ") for line in lines)

    def test_indent_code_custom_spaces(self):
        """Test code indentation with custom spaces."""
        evaluator = CorrectnessEvaluator()
        code = "line1\nline2"
        indented = evaluator._indent_code(code, spaces=2)

        lines = indented.split('\n')
        assert all(line.startswith("  ") for line in lines)


class TestEvaluateCorrectnessFunction:
    """Tests for the evaluate_correctness convenience function."""

    def test_evaluate_correctness_basic(self, sample_valid_function):
        """Test basic usage of evaluate_correctness function."""
        result = evaluate_correctness(sample_valid_function)

        assert result.evaluation_type == EvaluationType.CORRECTNESS
        assert result.score > 0

    def test_evaluate_correctness_with_reference(self):
        """Test evaluate_correctness with reference output."""
        code = "def add(a, b): return a + b"
        reference = "def add(x, y): return x + y"

        result = evaluate_correctness(code, reference=reference)

        assert "similarity" in result.details

    def test_evaluate_correctness_with_test_cases(self):
        """Test evaluate_correctness with test cases."""
        code = "def multiply(a, b): return a * b"
        test_cases = [
            {"name": "test1", "code": "print(multiply(2, 3))", "expected": "6"}
        ]

        result = evaluate_correctness(code, test_cases=test_cases)

        assert "tests" in result.details
        assert result.details["tests"]["pass_rate"] == 1.0

    def test_evaluate_correctness_non_python(self):
        """Test evaluate_correctness with non-Python code."""
        result = evaluate_correctness(
            "const add = (a, b) => a + b;",
            language="javascript"
        )

        assert result.evaluation_type == EvaluationType.CORRECTNESS
        # Should pass basic check
        assert result.details["syntax"]["valid"] is True


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_code_with_imports(self):
        """Test code that imports modules."""
        code = '''
import os
import sys
from pathlib import Path

def get_cwd():
    return Path.cwd()
'''
        evaluator = CorrectnessEvaluator(allow_execution=True)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=code
        )
        result = evaluator.evaluate(task)

        assert result.details["syntax"]["valid"] is True
        assert result.details["execution"]["success"] is True

    def test_code_with_class_definition(self):
        """Test code with class definition."""
        code = '''
class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b

calc = Calculator()
print(calc.add(1, 2))
'''
        evaluator = CorrectnessEvaluator(allow_execution=True)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=code
        )
        result = evaluator.evaluate(task)

        assert result.details["syntax"]["valid"] is True
        assert result.details["execution"]["success"] is True

    def test_unicode_in_code(self):
        """Test code with unicode characters."""
        code = '''
def greet(name):
    return f"Hello, {name}! 🎉"

print(greet("World"))
'''
        evaluator = CorrectnessEvaluator(allow_execution=True)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=code
        )
        result = evaluator.evaluate(task)

        assert result.details["syntax"]["valid"] is True


class TestMissingCoverage:
    """Tests for previously uncovered code paths."""

    def test_execution_general_exception(self):
        """Test execution handling of general exceptions (lines 180-181)."""
        evaluator = CorrectnessEvaluator(allow_execution=True)

        # Mock subprocess to raise a general exception
        with patch('subprocess.run', side_effect=OSError("Disk full")):
            task = EvaluationTask(
                task_id="test",
                input_text="",
                generated_output="print('hello')"
            )
            result = evaluator.evaluate(task)

            assert "execution" in result.details
            assert result.details["execution"]["success"] is False
            assert "Disk full" in result.details["execution"]["error"]

    def test_run_tests_non_python_language(self):
        """Test that non-Python tests return error (line 191)."""
        evaluator = CorrectnessEvaluator(allow_execution=True)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output="function add(a, b) { return a + b; }",
            language="javascript",
            metadata={
                "test_cases": [
                    {"name": "test1", "code": "console.log(add(1, 2))", "expected": "3"}
                ]
            }
        )
        result = evaluator.evaluate(task)

        # Non-Python tests should be skipped (tests section won't have results)
        # The syntax check for non-Python just checks if non-empty
        assert result.details["syntax"]["valid"] is True

    def test_test_without_expected_output(self):
        """Test that tests without expected output pass on success (line 233)."""
        code = '''
def greet():
    print("Hello")
'''
        evaluator = CorrectnessEvaluator(allow_execution=True)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=code,
            metadata={
                "test_cases": [
                    {"name": "test_greet", "code": "greet()"}  # No expected output
                ]
            }
        )
        result = evaluator.evaluate(task)

        assert "tests" in result.details
        assert result.details["tests"]["pass_rate"] == 1.0

    def test_test_execution_exception(self):
        """Test that test execution exceptions are caught (lines 240-241)."""
        code = "def foo(): pass"
        evaluator = CorrectnessEvaluator(allow_execution=True, timeout=1)

        # Create a test that will timeout
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=code,
            metadata={
                "test_cases": [
                    {
                        "name": "timeout_test",
                        "code": "import time; time.sleep(10)"  # Will timeout
                    }
                ]
            }
        )
        result = evaluator.evaluate(task)

        assert "tests" in result.details
        assert result.details["tests"]["pass_rate"] < 1.0
        assert len(result.details["tests"]["failed_tests"]) > 0

    def test_test_with_runtime_error(self):
        """Test that tests with runtime errors are marked as failed (lines 235-238)."""
        code = '''
def divide(a, b):
    return a / b
'''
        evaluator = CorrectnessEvaluator(allow_execution=True)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=code,
            metadata={
                "test_cases": [
                    {
                        "name": "test_divide_by_zero",
                        "code": "print(divide(1, 0))"  # Will cause ZeroDivisionError
                    }
                ]
            }
        )
        result = evaluator.evaluate(task)

        assert "tests" in result.details
        assert result.details["tests"]["pass_rate"] < 1.0
        assert len(result.details["tests"]["failed_tests"]) > 0
