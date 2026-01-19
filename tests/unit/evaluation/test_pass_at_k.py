"""Tests for the pass@k evaluator."""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from src.evaluation.pass_at_k import (
    SampleResult,
    PassAtKResult,
    PassAtKEvaluator,
    aggregate_pass_at_k_results,
    compute_pass_at_k_simple,
)
from src.evaluation.base import EvaluationTask


class TestSampleResult:
    """Tests for SampleResult dataclass."""

    def test_sample_result_creation(self):
        """Test creating a SampleResult."""
        result = SampleResult(
            sample_id=0,
            code="def add(a, b): return a + b",
            passed=True,
            correctness_score=0.95,
            temperature=0.7,
            generation_time=1.5
        )
        assert result.sample_id == 0
        assert result.passed is True
        assert result.correctness_score == 0.95
        assert result.temperature == 0.7

    def test_sample_result_default_values(self):
        """Test SampleResult default values."""
        result = SampleResult(
            sample_id=1,
            code="x = 1",
            passed=False,
            correctness_score=0.0
        )
        assert result.execution_results == {}
        assert result.temperature == 0.7
        assert result.generation_time == 0.0


class TestPassAtKResult:
    """Tests for PassAtKResult dataclass."""

    def test_pass_at_k_result_creation(self):
        """Test creating a PassAtKResult."""
        samples = [
            SampleResult(sample_id=0, code="x=1", passed=True, correctness_score=1.0),
            SampleResult(sample_id=1, code="x=2", passed=False, correctness_score=0.5),
        ]
        result = PassAtKResult(
            task_id="test_task",
            num_samples=2,
            num_correct=1,
            pass_at_k={1: 0.5, 5: 0.5},
            samples=samples,
            average_score=0.75
        )
        assert result.task_id == "test_task"
        assert result.num_samples == 2
        assert result.num_correct == 1
        assert result.pass_rate == 0.5

    def test_pass_rate_calculation(self):
        """Test pass_rate property calculation."""
        result = PassAtKResult(
            task_id="test",
            num_samples=10,
            num_correct=7,
            pass_at_k={1: 0.7}
        )
        assert result.pass_rate == 0.7

    def test_pass_rate_zero_samples(self):
        """Test pass_rate with zero samples."""
        result = PassAtKResult(
            task_id="test",
            num_samples=0,
            num_correct=0,
            pass_at_k={}
        )
        assert result.pass_rate == 0.0

    def test_to_dict(self):
        """Test to_dict serialization."""
        sample = SampleResult(
            sample_id=0,
            code="def foo(): pass",
            passed=True,
            correctness_score=0.9,
            temperature=0.5
        )
        result = PassAtKResult(
            task_id="test",
            num_samples=1,
            num_correct=1,
            pass_at_k={1: 1.0},
            samples=[sample],
            best_sample=sample,
            average_score=0.9
        )

        d = result.to_dict()
        assert d["task_id"] == "test"
        assert d["num_samples"] == 1
        assert d["pass_rate"] == 1.0
        assert d["best_sample"]["passed"] is True
        assert len(d["samples_summary"]) == 1


class TestPassAtKEvaluator:
    """Tests for PassAtKEvaluator class."""

    def test_default_initialization(self):
        """Test default evaluator initialization."""
        evaluator = PassAtKEvaluator()
        assert evaluator.num_samples == 10
        assert evaluator.k_values == [1, 5, 10]
        assert evaluator.temperatures == [0.2, 0.4, 0.6, 0.8]
        assert evaluator.max_concurrent == 3
        assert evaluator.client is None

    def test_custom_initialization(self):
        """Test custom evaluator initialization."""
        mock_client = MagicMock()
        evaluator = PassAtKEvaluator(
            client=mock_client,
            num_samples=5,
            k_values=[1, 3],
            temperatures=[0.5, 0.9],
            max_concurrent=2,
            correctness_threshold=0.8
        )
        assert evaluator.num_samples == 5
        assert evaluator.k_values == [1, 3]
        assert evaluator.temperatures == [0.5, 0.9]
        assert evaluator.max_concurrent == 2
        assert evaluator.client is mock_client


class TestPassAtKComputation:
    """Tests for pass@k probability computation."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        return PassAtKEvaluator()

    def test_compute_pass_at_k_all_correct(self, evaluator):
        """Test pass@k when all samples are correct."""
        # n=10, c=10, k=1 -> pass@1 = 1.0
        result = evaluator.compute_pass_at_k(n=10, c=10, k=1)
        assert result == 1.0

    def test_compute_pass_at_k_none_correct(self, evaluator):
        """Test pass@k when no samples are correct."""
        # n=10, c=0, k=1 -> pass@1 = 0.0
        result = evaluator.compute_pass_at_k(n=10, c=0, k=1)
        assert result == 0.0

    def test_compute_pass_at_k_half_correct(self, evaluator):
        """Test pass@k when half samples are correct."""
        # n=10, c=5, k=1 -> pass@1 = 0.5
        result = evaluator.compute_pass_at_k(n=10, c=5, k=1)
        assert result == 0.5

    def test_compute_pass_at_k_k_greater_than_n_minus_c(self, evaluator):
        """Test pass@k when k > n-c (guaranteed success)."""
        # n=10, c=8, k=5 -> must find at least one correct
        result = evaluator.compute_pass_at_k(n=10, c=8, k=5)
        assert result == 1.0

    def test_compute_pass_at_k_typical_values(self, evaluator):
        """Test pass@k with typical experiment values."""
        # n=10, c=3, k=1 -> pass@1 = 0.3
        pass_at_1 = evaluator.compute_pass_at_k(n=10, c=3, k=1)
        assert pass_at_1 == pytest.approx(0.3)

        # pass@5 should be higher than pass@1
        pass_at_5 = evaluator.compute_pass_at_k(n=10, c=3, k=5)
        assert pass_at_5 > pass_at_1

        # pass@10 should be even higher
        pass_at_10 = evaluator.compute_pass_at_k(n=10, c=3, k=10)
        assert pass_at_10 >= pass_at_5

    def test_compute_pass_at_k_k_equals_n(self, evaluator):
        """Test pass@k when k equals n."""
        # If we sample all n, and at least one is correct, pass@n = 1.0
        result = evaluator.compute_pass_at_k(n=10, c=3, k=10)
        assert result == 1.0

    def test_compute_pass_at_k_invalid_k(self, evaluator):
        """Test pass@k with k > n raises error."""
        with pytest.raises(ValueError):
            evaluator.compute_pass_at_k(n=5, c=2, k=10)

    def test_compute_pass_at_k_mathematical_correctness(self, evaluator):
        """Test pass@k matches expected mathematical formula."""
        # pass@k = 1 - C(n-c, k) / C(n, k)
        # For n=6, c=2, k=3:
        # C(4, 3) / C(6, 3) = 4 / 20 = 0.2
        # pass@3 = 1 - 0.2 = 0.8
        result = evaluator.compute_pass_at_k(n=6, c=2, k=3)
        assert abs(result - 0.8) < 0.001

    def test_compute_pass_at_k_simple_function(self):
        """Test standalone compute_pass_at_k_simple function."""
        result = compute_pass_at_k_simple(num_samples=10, num_correct=5, k=1)
        assert result == 0.5


class TestCodeExtraction:
    """Tests for code extraction from responses."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        return PassAtKEvaluator()

    def test_extract_code_with_python_block(self, evaluator):
        """Test extracting code from Python code block."""
        response = '''Here is the function:

```python
def add(a, b):
    return a + b
```

This function adds two numbers.'''

        code = evaluator._extract_code(response)
        assert "def add(a, b):" in code
        assert "return a + b" in code

    def test_extract_code_with_generic_block(self, evaluator):
        """Test extracting code from generic code block."""
        response = '''```
def multiply(a, b):
    return a * b
```'''

        code = evaluator._extract_code(response)
        assert "def multiply(a, b):" in code

    def test_extract_code_no_block(self, evaluator):
        """Test extracting code when no code block present."""
        response = "def simple(): pass"
        code = evaluator._extract_code(response)
        assert code == "def simple(): pass"

    def test_extract_code_empty_response(self, evaluator):
        """Test extracting code from empty response."""
        code = evaluator._extract_code("")
        assert code == ""

    def test_extract_code_multiple_blocks(self, evaluator):
        """Test that first code block is extracted."""
        response = '''```python
def first():
    pass
```

```python
def second():
    pass
```'''

        code = evaluator._extract_code(response)
        assert "def first():" in code
        assert "def second():" not in code


class TestSampleEvaluation:
    """Tests for sample evaluation functionality."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        return PassAtKEvaluator(correctness_threshold=0.7)

    def test_evaluate_sample_valid_code(self, evaluator):
        """Test evaluating a valid code sample."""
        sample = SampleResult(
            sample_id=0,
            code="def add(a, b): return a + b",
            passed=False,
            correctness_score=0.0
        )
        test_cases = [
            {"name": "test_add", "code": "print(add(2, 3))", "expected": "5"}
        ]

        result = evaluator.evaluate_sample(sample, test_cases)

        assert result.correctness_score > 0
        assert "details" in result.execution_results

    def test_evaluate_sample_invalid_code(self, evaluator):
        """Test evaluating an invalid code sample."""
        sample = SampleResult(
            sample_id=0,
            code="def broken(",
            passed=False,
            correctness_score=0.0
        )

        result = evaluator.evaluate_sample(sample, [])

        assert result.passed is False
        assert result.correctness_score < 1.0

    def test_evaluate_sample_empty_code(self, evaluator):
        """Test evaluating an empty code sample."""
        sample = SampleResult(
            sample_id=0,
            code="",
            passed=False,
            correctness_score=0.0
        )

        result = evaluator.evaluate_sample(sample, [])

        # Empty code should be returned as-is
        assert result.code == ""
        assert result.passed is False

    def test_evaluate_samples_batch(self, evaluator):
        """Test evaluating multiple samples."""
        samples = [
            SampleResult(sample_id=0, code="def f(): return 1", passed=False, correctness_score=0.0),
            SampleResult(sample_id=1, code="def g(): return 2", passed=False, correctness_score=0.0),
            SampleResult(sample_id=2, code="def broken(", passed=False, correctness_score=0.0),
        ]

        results = evaluator.evaluate_samples(samples, [])

        assert len(results) == 3
        # First two should have some score
        assert results[0].correctness_score > 0
        assert results[1].correctness_score > 0
        # Third has syntax error
        assert results[2].correctness_score < results[0].correctness_score


class TestEvaluateCodeSamples:
    """Tests for evaluating pre-generated code samples."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator with specific k values."""
        return PassAtKEvaluator(k_values=[1, 3, 5])

    def test_evaluate_code_samples_all_valid(self, evaluator):
        """Test evaluating all valid code samples."""
        code_samples = [
            "def add(a, b): return a + b",
            "def add(x, y): return x + y",
            "def add(a, b):\n    return a + b",
        ]
        test_cases = [
            {"name": "test", "code": "print(add(2, 3))", "expected": "5"}
        ]

        result = evaluator.evaluate_code_samples(code_samples, test_cases)

        assert result.task_id == "code_evaluation"
        assert result.num_samples == 3
        assert result.num_correct > 0
        assert 1 in result.pass_at_k
        assert result.pass_at_k[1] > 0

    def test_evaluate_code_samples_mixed_validity(self, evaluator):
        """Test evaluating mix of valid and invalid code."""
        code_samples = [
            "def add(a, b): return a + b",  # Valid
            "def broken(",  # Invalid syntax
            "def subtract(a, b): return a - b",  # Valid but wrong
        ]
        test_cases = [
            {"name": "test", "code": "print(add(2, 3))", "expected": "5"}
        ]

        result = evaluator.evaluate_code_samples(code_samples, test_cases)

        assert result.num_samples == 3
        # At least one should be correct
        assert len(result.samples) == 3

    def test_evaluate_code_samples_with_reference(self, evaluator):
        """Test evaluating with reference code for similarity."""
        code_samples = [
            "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)",
        ]
        reference = "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)"

        result = evaluator.evaluate_code_samples(
            code_samples,
            test_cases=[],
            reference_code=reference
        )

        assert result.num_samples == 1
        # Should have some similarity score
        assert result.average_score > 0


class TestAggregation:
    """Tests for aggregating pass@k results."""

    def test_aggregate_empty_results(self):
        """Test aggregation with empty results list."""
        result = aggregate_pass_at_k_results([])

        assert result["num_tasks"] == 0
        assert result["total_samples"] == 0
        assert result["average_pass_rate"] == 0.0

    def test_aggregate_single_result(self):
        """Test aggregation with single result."""
        result = PassAtKResult(
            task_id="task1",
            num_samples=10,
            num_correct=5,
            pass_at_k={1: 0.5, 5: 0.9},
            average_score=0.75
        )

        aggregated = aggregate_pass_at_k_results([result])

        assert aggregated["num_tasks"] == 1
        assert aggregated["total_samples"] == 10
        assert aggregated["total_correct"] == 5
        assert aggregated["average_pass_rate"] == 0.5
        assert 1 in aggregated["pass_at_k"]
        assert aggregated["pass_at_k"][1]["mean"] == 0.5

    def test_aggregate_multiple_results(self):
        """Test aggregation with multiple results."""
        results = [
            PassAtKResult(
                task_id="task1",
                num_samples=10,
                num_correct=8,
                pass_at_k={1: 0.8, 5: 1.0},
                average_score=0.9
            ),
            PassAtKResult(
                task_id="task2",
                num_samples=10,
                num_correct=4,
                pass_at_k={1: 0.4, 5: 0.8},
                average_score=0.6
            ),
        ]

        aggregated = aggregate_pass_at_k_results(results)

        assert aggregated["num_tasks"] == 2
        assert aggregated["total_samples"] == 20
        assert aggregated["total_correct"] == 12
        assert aggregated["average_pass_rate"] == pytest.approx(0.6)  # (0.8 + 0.4) / 2
        assert aggregated["average_score"] == pytest.approx(0.75)  # (0.9 + 0.6) / 2
        assert aggregated["pass_at_k"][1]["mean"] == pytest.approx(0.6)  # (0.8 + 0.4) / 2
        assert aggregated["pass_at_k"][5]["mean"] == pytest.approx(0.9)  # (1.0 + 0.8) / 2

    def test_aggregate_calculates_statistics(self):
        """Test that aggregation includes statistics."""
        results = [
            PassAtKResult(
                task_id=f"task{i}",
                num_samples=10,
                num_correct=i,
                pass_at_k={1: i/10},
                average_score=i/10
            )
            for i in range(1, 6)  # 1, 2, 3, 4, 5
        ]

        aggregated = aggregate_pass_at_k_results(results)

        assert "std" in aggregated["pass_at_k"][1]
        assert "min" in aggregated["pass_at_k"][1]
        assert "max" in aggregated["pass_at_k"][1]
        assert aggregated["pass_at_k"][1]["min"] == 0.1
        assert aggregated["pass_at_k"][1]["max"] == 0.5


class TestAsyncGeneration:
    """Tests for async sample generation."""

    @pytest.fixture
    def mock_client(self):
        """Create mock Claude client."""
        mock = MagicMock()
        mock.generate.return_value = """```python
def add(a, b):
    return a + b
```"""
        return mock

    def test_generate_sample(self, mock_client):
        """Test generating a single sample."""
        evaluator = PassAtKEvaluator(client=mock_client)

        async def run_test():
            return await evaluator.generate_sample(
                prompt="Write an add function",
                temperature=0.5,
                sample_id=0
            )

        sample = asyncio.run(run_test())

        assert sample.sample_id == 0
        assert sample.temperature == 0.5
        assert "def add" in sample.code
        assert sample.generation_time > 0

    def test_generate_sample_without_client(self):
        """Test generating sample without client raises error."""
        evaluator = PassAtKEvaluator()  # No client

        async def run_test():
            return await evaluator.generate_sample("test", 0.5, 0)

        with pytest.raises(ValueError, match="ClaudeClient required"):
            asyncio.run(run_test())

    def test_generate_samples_distributes_temperatures(self, mock_client):
        """Test that samples are distributed across temperatures."""
        evaluator = PassAtKEvaluator(
            client=mock_client,
            num_samples=8,
            temperatures=[0.2, 0.8]
        )

        async def run_test():
            return await evaluator.generate_samples("test prompt")

        samples = asyncio.run(run_test())

        assert len(samples) == 8
        temps = [s.temperature for s in samples]
        # Should have 4 samples at each temperature
        assert temps.count(0.2) == 4
        assert temps.count(0.8) == 4

    def test_generate_sample_handles_error(self, mock_client):
        """Test that generation errors are handled gracefully."""
        mock_client.generate.side_effect = Exception("API Error")
        evaluator = PassAtKEvaluator(client=mock_client)

        async def run_test():
            return await evaluator.generate_sample("test", 0.5, 0)

        sample = asyncio.run(run_test())

        assert sample.code == ""
        assert sample.passed is False
        assert "error" in sample.execution_results


class TestEvaluateTask:
    """Tests for full task evaluation with generation."""

    @pytest.fixture
    def mock_client(self):
        """Create mock Claude client."""
        mock = MagicMock()
        mock.generate.return_value = "```python\ndef factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)\n```"
        return mock

    def test_evaluate_task_full_pipeline(self, mock_client):
        """Test complete task evaluation pipeline."""
        evaluator = PassAtKEvaluator(
            client=mock_client,
            num_samples=4,
            k_values=[1, 2, 4],
            temperatures=[0.5],
            max_concurrent=2
        )

        test_cases = [
            {"name": "test_fact_0", "code": "print(factorial(0))", "expected": "1"},
            {"name": "test_fact_5", "code": "print(factorial(5))", "expected": "120"},
        ]

        async def run_test():
            return await evaluator.evaluate_task(
                task_id="factorial_task",
                prompt="Write a factorial function",
                test_cases=test_cases
            )

        result = asyncio.run(run_test())

        assert result.task_id == "factorial_task"
        assert result.num_samples == 4
        assert 1 in result.pass_at_k
        assert 2 in result.pass_at_k
        assert 4 in result.pass_at_k
        assert len(result.samples) == 4
