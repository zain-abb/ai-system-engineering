"""Tests for evaluation base classes."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.evaluation.base import (
    EvaluationType,
    Severity,
    Issue,
    EvaluationResult,
    EvaluationTask,
    AggregatedResults,
    BaseEvaluator,
)


class TestEvaluationType:
    """Tests for EvaluationType enum."""

    def test_evaluation_type_values(self):
        """Test that all evaluation types have correct string values."""
        assert EvaluationType.CORRECTNESS.value == "correctness"
        assert EvaluationType.ROBUSTNESS.value == "robustness"
        assert EvaluationType.SAFETY.value == "safety"
        assert EvaluationType.HALLUCINATION.value == "hallucination"

    def test_evaluation_type_count(self):
        """Test that there are exactly 4 evaluation types."""
        assert len(EvaluationType) == 4


class TestSeverity:
    """Tests for Severity enum."""

    def test_severity_values(self):
        """Test that all severity levels have correct string values."""
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"
        assert Severity.INFO.value == "info"

    def test_severity_count(self):
        """Test that there are exactly 5 severity levels."""
        assert len(Severity) == 5


class TestIssue:
    """Tests for Issue dataclass."""

    def test_issue_creation_minimal(self):
        """Test creating an issue with minimal required fields."""
        issue = Issue(
            severity=Severity.HIGH,
            category="test_category",
            description="Test description"
        )
        assert issue.severity == Severity.HIGH
        assert issue.category == "test_category"
        assert issue.description == "Test description"
        assert issue.location is None
        assert issue.suggestion is None

    def test_issue_creation_full(self):
        """Test creating an issue with all fields."""
        issue = Issue(
            severity=Severity.CRITICAL,
            category="security",
            description="SQL injection found",
            location="line 10",
            suggestion="Use parameterized queries"
        )
        assert issue.severity == Severity.CRITICAL
        assert issue.category == "security"
        assert issue.description == "SQL injection found"
        assert issue.location == "line 10"
        assert issue.suggestion == "Use parameterized queries"

    def test_issue_to_dict(self, sample_critical_issue):
        """Test Issue.to_dict() serialization."""
        result = sample_critical_issue.to_dict()

        assert isinstance(result, dict)
        assert result["severity"] == "critical"
        assert result["category"] == "security"
        assert result["description"] == "SQL injection vulnerability found"
        assert result["location"] == "line 10"
        assert result["suggestion"] == "Use parameterized queries"

    def test_issue_to_dict_with_none_values(self):
        """Test Issue.to_dict() with optional fields as None."""
        issue = Issue(
            severity=Severity.LOW,
            category="style",
            description="Consider refactoring"
        )
        result = issue.to_dict()

        assert result["severity"] == "low"
        assert result["location"] is None
        assert result["suggestion"] is None


class TestEvaluationResult:
    """Tests for EvaluationResult dataclass."""

    def test_evaluation_result_creation(self, sample_critical_issue):
        """Test creating an evaluation result."""
        result = EvaluationResult(
            evaluation_type=EvaluationType.SAFETY,
            score=0.8,
            passed=True,
            issues=[sample_critical_issue],
            details={"check": "done"}
        )
        assert result.evaluation_type == EvaluationType.SAFETY
        assert result.score == 0.8
        assert result.passed is True
        assert len(result.issues) == 1
        assert result.details["check"] == "done"

    def test_evaluation_result_default_values(self):
        """Test evaluation result default values."""
        result = EvaluationResult(
            evaluation_type=EvaluationType.CORRECTNESS,
            score=0.5,
            passed=False
        )
        assert result.issues == []
        assert result.details == {}
        assert isinstance(result.timestamp, datetime)

    def test_critical_count_property(self, sample_critical_issue, sample_high_issue, sample_medium_issue):
        """Test critical_count property."""
        critical2 = Issue(severity=Severity.CRITICAL, category="test", description="test")
        result = EvaluationResult(
            evaluation_type=EvaluationType.SAFETY,
            score=0.3,
            passed=False,
            issues=[sample_critical_issue, critical2, sample_high_issue, sample_medium_issue]
        )
        assert result.critical_count == 2

    def test_high_count_property(self, sample_critical_issue, sample_high_issue):
        """Test high_count property."""
        high2 = Issue(severity=Severity.HIGH, category="test", description="test")
        result = EvaluationResult(
            evaluation_type=EvaluationType.SAFETY,
            score=0.5,
            passed=False,
            issues=[sample_critical_issue, sample_high_issue, high2]
        )
        assert result.high_count == 2

    def test_issue_count_property(self, sample_critical_issue, sample_high_issue, sample_medium_issue):
        """Test issue_count property."""
        result = EvaluationResult(
            evaluation_type=EvaluationType.SAFETY,
            score=0.5,
            passed=False,
            issues=[sample_critical_issue, sample_high_issue, sample_medium_issue]
        )
        assert result.issue_count == 3

    def test_issue_count_empty(self):
        """Test issue_count with no issues."""
        result = EvaluationResult(
            evaluation_type=EvaluationType.CORRECTNESS,
            score=1.0,
            passed=True,
            issues=[]
        )
        assert result.issue_count == 0

    def test_to_dict_basic(self, sample_evaluation_result):
        """Test EvaluationResult.to_dict() serialization."""
        result = sample_evaluation_result.to_dict()

        assert isinstance(result, dict)
        assert result["evaluation_type"] == "safety"
        assert result["score"] == 0.5
        assert result["passed"] is False
        assert result["issue_count"] == 2
        assert result["critical_count"] == 1
        assert result["high_count"] == 1
        assert isinstance(result["issues"], list)
        assert len(result["issues"]) == 2
        assert isinstance(result["timestamp"], str)

    def test_to_dict_nested_issues(self, sample_critical_issue, sample_high_issue):
        """Test to_dict() properly serializes nested Issue objects."""
        # Put Issue objects in details dict
        result = EvaluationResult(
            evaluation_type=EvaluationType.SAFETY,
            score=0.5,
            passed=False,
            issues=[sample_critical_issue],
            details={
                "nested_issue": sample_high_issue,
                "issue_list": [sample_critical_issue, sample_high_issue]
            }
        )

        serialized = result.to_dict()

        # Check nested Issue is serialized
        assert isinstance(serialized["details"]["nested_issue"], dict)
        assert serialized["details"]["nested_issue"]["severity"] == "high"

        # Check list of Issues is serialized
        assert isinstance(serialized["details"]["issue_list"], list)
        assert len(serialized["details"]["issue_list"]) == 2
        assert serialized["details"]["issue_list"][0]["severity"] == "critical"

    def test_serialize_details_with_severity_enum(self):
        """Test _serialize_details handles Severity enum."""
        result = EvaluationResult(
            evaluation_type=EvaluationType.SAFETY,
            score=0.5,
            passed=False,
            details={"max_severity": Severity.CRITICAL}
        )

        serialized = result.to_dict()
        assert serialized["details"]["max_severity"] == "critical"

    def test_serialize_details_with_datetime(self):
        """Test _serialize_details handles datetime objects."""
        test_time = datetime(2024, 6, 15, 10, 30, 0)
        result = EvaluationResult(
            evaluation_type=EvaluationType.CORRECTNESS,
            score=1.0,
            passed=True,
            details={"check_time": test_time}
        )

        serialized = result.to_dict()
        assert serialized["details"]["check_time"] == "2024-06-15T10:30:00"


class TestEvaluationTask:
    """Tests for EvaluationTask dataclass."""

    def test_task_creation_minimal(self):
        """Test creating a task with minimal required fields."""
        task = EvaluationTask(
            task_id="task_001",
            input_text="Write a function",
            generated_output="def foo(): pass"
        )
        assert task.task_id == "task_001"
        assert task.input_text == "Write a function"
        assert task.generated_output == "def foo(): pass"
        assert task.reference_output is None
        assert task.language == "python"  # default
        assert task.metadata == {}  # default

    def test_task_creation_full(self):
        """Test creating a task with all fields."""
        task = EvaluationTask(
            task_id="task_002",
            input_text="Write add function",
            generated_output="def add(a, b): return a + b",
            reference_output="def add(x, y): return x + y",
            language="python",
            metadata={"source": "test", "difficulty": "easy"}
        )
        assert task.task_id == "task_002"
        assert task.reference_output == "def add(x, y): return x + y"
        assert task.language == "python"
        assert task.metadata["source"] == "test"
        assert task.metadata["difficulty"] == "easy"

    def test_task_default_language(self):
        """Test that default language is python."""
        task = EvaluationTask(
            task_id="test",
            input_text="test",
            generated_output="test"
        )
        assert task.language == "python"


class TestAggregatedResults:
    """Tests for AggregatedResults dataclass."""

    def test_aggregated_results_creation(self, sample_aggregated_results):
        """Test creating aggregated results."""
        assert sample_aggregated_results.total_tasks == 10
        assert sample_aggregated_results.passed_count == 7
        assert sample_aggregated_results.failed_count == 3
        assert sample_aggregated_results.average_score == 0.75

    def test_pass_rate_normal(self, sample_aggregated_results):
        """Test pass_rate calculation."""
        assert sample_aggregated_results.pass_rate == 0.7

    def test_pass_rate_zero_tasks(self):
        """Test pass_rate with zero tasks returns 0.0."""
        results = AggregatedResults(
            total_tasks=0,
            passed_count=0,
            failed_count=0,
            average_score=0.0,
            results_by_type={}
        )
        assert results.pass_rate == 0.0

    def test_pass_rate_all_passed(self):
        """Test pass_rate when all tasks pass."""
        results = AggregatedResults(
            total_tasks=5,
            passed_count=5,
            failed_count=0,
            average_score=0.95,
            results_by_type={}
        )
        assert results.pass_rate == 1.0

    def test_pass_rate_none_passed(self):
        """Test pass_rate when no tasks pass."""
        results = AggregatedResults(
            total_tasks=5,
            passed_count=0,
            failed_count=5,
            average_score=0.3,
            results_by_type={}
        )
        assert results.pass_rate == 0.0

    def test_to_dict(self, sample_aggregated_results):
        """Test AggregatedResults.to_dict() serialization."""
        result = sample_aggregated_results.to_dict()

        assert isinstance(result, dict)
        assert result["total_tasks"] == 10
        assert result["passed_count"] == 7
        assert result["failed_count"] == 3
        assert result["pass_rate"] == 0.7
        assert result["average_score"] == 0.75
        assert result["summary"] == {"test_summary": True}
        assert "results_by_type" in result

    def test_to_dict_results_by_type_serialization(self, sample_passing_result):
        """Test that results_by_type is properly serialized."""
        results = AggregatedResults(
            total_tasks=1,
            passed_count=1,
            failed_count=0,
            average_score=0.95,
            results_by_type={
                EvaluationType.CORRECTNESS: [sample_passing_result]
            }
        )

        serialized = results.to_dict()

        assert "correctness" in serialized["results_by_type"]
        assert isinstance(serialized["results_by_type"]["correctness"], list)
        assert len(serialized["results_by_type"]["correctness"]) == 1
        assert serialized["results_by_type"]["correctness"][0]["score"] == 0.95


class TestBaseEvaluator:
    """Tests for BaseEvaluator abstract class."""

    def test_base_evaluator_is_abstract(self):
        """Test that BaseEvaluator cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseEvaluator()

    def test_concrete_evaluator_creation(self):
        """Test creating a concrete evaluator implementation."""
        class ConcreteEvaluator(BaseEvaluator):
            @property
            def evaluation_type(self):
                return EvaluationType.CORRECTNESS

            def evaluate(self, task):
                return self._create_result(score=1.0)

        evaluator = ConcreteEvaluator(threshold=0.8)
        assert evaluator.threshold == 0.8

    def test_default_threshold(self):
        """Test default threshold is 0.7."""
        class ConcreteEvaluator(BaseEvaluator):
            @property
            def evaluation_type(self):
                return EvaluationType.CORRECTNESS

            def evaluate(self, task):
                return self._create_result(score=1.0)

        evaluator = ConcreteEvaluator()
        assert evaluator.threshold == 0.7

    def test_create_result_helper(self):
        """Test _create_result helper method."""
        class ConcreteEvaluator(BaseEvaluator):
            @property
            def evaluation_type(self):
                return EvaluationType.SAFETY

            def evaluate(self, task):
                return self._create_result(
                    score=0.8,
                    issues=[Issue(Severity.LOW, "test", "test issue")],
                    details={"tested": True}
                )

        evaluator = ConcreteEvaluator(threshold=0.7)
        task = EvaluationTask(task_id="1", input_text="", generated_output="")
        result = evaluator.evaluate(task)

        assert result.evaluation_type == EvaluationType.SAFETY
        assert result.score == 0.8
        assert result.passed is True  # 0.8 >= 0.7
        assert len(result.issues) == 1
        assert result.details["tested"] is True

    def test_create_result_passed_false_when_below_threshold(self):
        """Test _create_result sets passed=False when score < threshold."""
        class ConcreteEvaluator(BaseEvaluator):
            @property
            def evaluation_type(self):
                return EvaluationType.CORRECTNESS

            def evaluate(self, task):
                return self._create_result(score=0.5)

        evaluator = ConcreteEvaluator(threshold=0.7)
        task = EvaluationTask(task_id="1", input_text="", generated_output="")
        result = evaluator.evaluate(task)

        assert result.passed is False

    def test_evaluate_batch_success(self, sample_evaluation_task):
        """Test evaluate_batch with successful evaluations."""
        class ConcreteEvaluator(BaseEvaluator):
            @property
            def evaluation_type(self):
                return EvaluationType.CORRECTNESS

            def evaluate(self, task):
                return self._create_result(score=0.9)

        evaluator = ConcreteEvaluator()
        tasks = [sample_evaluation_task, sample_evaluation_task]
        results = evaluator.evaluate_batch(tasks)

        assert len(results) == 2
        assert all(r.score == 0.9 for r in results)
        assert all(r.passed for r in results)

    def test_evaluate_batch_handles_exceptions(self, sample_evaluation_task):
        """Test evaluate_batch handles exceptions gracefully."""
        class FailingEvaluator(BaseEvaluator):
            @property
            def evaluation_type(self):
                return EvaluationType.CORRECTNESS

            def evaluate(self, task):
                raise ValueError("Test error")

        evaluator = FailingEvaluator()
        results = evaluator.evaluate_batch([sample_evaluation_task])

        assert len(results) == 1
        result = results[0]
        assert result.score == 0.0
        assert result.passed is False
        assert len(result.issues) == 1
        assert result.issues[0].severity == Severity.CRITICAL
        assert result.issues[0].category == "evaluation_error"
        assert "Test error" in result.issues[0].description

    def test_evaluate_batch_empty_list(self):
        """Test evaluate_batch with empty task list."""
        class ConcreteEvaluator(BaseEvaluator):
            @property
            def evaluation_type(self):
                return EvaluationType.CORRECTNESS

            def evaluate(self, task):
                return self._create_result(score=1.0)

        evaluator = ConcreteEvaluator()
        results = evaluator.evaluate_batch([])

        assert results == []

    def test_evaluator_has_logger(self):
        """Test that evaluator has a logger attribute."""
        class ConcreteEvaluator(BaseEvaluator):
            @property
            def evaluation_type(self):
                return EvaluationType.CORRECTNESS

            def evaluate(self, task):
                return self._create_result(score=1.0)

        evaluator = ConcreteEvaluator()
        assert hasattr(evaluator, 'logger')
        assert evaluator.logger.name == "ConcreteEvaluator"
