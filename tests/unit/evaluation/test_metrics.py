"""Tests for the metrics and evaluation pipeline."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.evaluation.base import (
    EvaluationType,
    EvaluationTask,
    EvaluationResult,
    Severity,
    Issue,
)
from src.evaluation.metrics import (
    EvaluationConfig,
    TaskEvaluationResult,
    EvaluationReport,
    EvaluationPipeline,
    MetricsCalculator,
    quick_evaluate,
    generate_evaluation_report,
)


class TestEvaluationConfig:
    """Tests for EvaluationConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = EvaluationConfig()
        assert config.run_correctness is True
        assert config.run_robustness is True
        assert config.run_safety is True
        assert config.run_hallucination is True
        assert config.correctness_threshold == 0.7
        assert config.robustness_threshold == 0.6
        assert config.safety_threshold == 0.7
        assert config.hallucination_threshold == 0.7

    def test_custom_config(self):
        """Test custom configuration values."""
        config = EvaluationConfig(
            run_correctness=False,
            run_robustness=False,
            correctness_threshold=0.8,
            safety_threshold=0.9
        )
        assert config.run_correctness is False
        assert config.run_robustness is False
        assert config.correctness_threshold == 0.8
        assert config.safety_threshold == 0.9

    def test_default_weights(self):
        """Test default weights sum to reasonable value."""
        config = EvaluationConfig()
        total_weight = sum(config.weights.values())
        assert total_weight == 1.0

    def test_weight_keys(self):
        """Test that all evaluation types have weights."""
        config = EvaluationConfig()
        assert "correctness" in config.weights
        assert "robustness" in config.weights
        assert "safety" in config.weights
        assert "hallucination" in config.weights


class TestTaskEvaluationResult:
    """Tests for TaskEvaluationResult dataclass."""

    def test_task_result_creation(self, sample_passing_result):
        """Test creating a task evaluation result."""
        result = TaskEvaluationResult(
            task_id="task_001",
            input_text="Write a function",
            generated_output="def foo(): pass",
            results={EvaluationType.CORRECTNESS: sample_passing_result},
            overall_score=0.95,
            overall_passed=True
        )
        assert result.task_id == "task_001"
        assert result.overall_score == 0.95
        assert result.overall_passed is True
        assert isinstance(result.timestamp, datetime)

    def test_task_result_to_dict(self, sample_passing_result):
        """Test TaskEvaluationResult.to_dict() serialization."""
        result = TaskEvaluationResult(
            task_id="task_001",
            input_text="Short prompt",
            generated_output="def foo(): pass",
            results={EvaluationType.CORRECTNESS: sample_passing_result},
            overall_score=0.95,
            overall_passed=True,
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )

        serialized = result.to_dict()

        assert serialized["task_id"] == "task_001"
        assert serialized["overall_score"] == 0.95
        assert serialized["overall_passed"] is True
        assert "correctness" in serialized["results"]
        assert serialized["timestamp"] == "2024-01-01T12:00:00"

    def test_task_result_truncates_long_text(self, sample_passing_result):
        """Test that long text is truncated in to_dict."""
        long_text = "x" * 300
        result = TaskEvaluationResult(
            task_id="task_001",
            input_text=long_text,
            generated_output=long_text * 2,
            results={EvaluationType.CORRECTNESS: sample_passing_result},
            overall_score=0.95,
            overall_passed=True
        )

        serialized = result.to_dict()

        assert len(serialized["input_text"]) < len(long_text)
        assert serialized["input_text"].endswith("...")
        assert len(serialized["generated_output"]) < len(long_text * 2)


class TestEvaluationReport:
    """Tests for EvaluationReport dataclass."""

    def test_report_creation(self, sample_passing_result):
        """Test creating an evaluation report."""
        task_result = TaskEvaluationResult(
            task_id="task_001",
            input_text="test",
            generated_output="test",
            results={EvaluationType.CORRECTNESS: sample_passing_result},
            overall_score=0.95,
            overall_passed=True
        )
        config = EvaluationConfig()
        report = EvaluationReport(
            config=config,
            task_results=[task_result],
            summary={"test": True}
        )

        assert len(report.task_results) == 1
        assert report.summary["test"] is True
        assert isinstance(report.timestamp, datetime)

    def test_report_to_dict(self, sample_passing_result):
        """Test EvaluationReport.to_dict() serialization."""
        task_result = TaskEvaluationResult(
            task_id="task_001",
            input_text="test",
            generated_output="test",
            results={EvaluationType.CORRECTNESS: sample_passing_result},
            overall_score=0.95,
            overall_passed=True
        )
        config = EvaluationConfig()
        report = EvaluationReport(
            config=config,
            task_results=[task_result],
            summary={"pass_rate": 1.0},
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )

        serialized = report.to_dict()

        assert "summary" in serialized
        assert "task_count" in serialized
        assert serialized["task_count"] == 1
        assert "tasks" in serialized
        assert serialized["timestamp"] == "2024-01-01T12:00:00"

    def test_report_save_and_load(self, sample_passing_result):
        """Test saving report to JSON file."""
        task_result = TaskEvaluationResult(
            task_id="task_001",
            input_text="test",
            generated_output="test",
            results={EvaluationType.CORRECTNESS: sample_passing_result},
            overall_score=0.95,
            overall_passed=True
        )
        config = EvaluationConfig()
        report = EvaluationReport(
            config=config,
            task_results=[task_result],
            summary={"pass_rate": 1.0}
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            report.save(temp_path)

            # Verify file was created and is valid JSON
            with open(temp_path, 'r') as f:
                loaded = json.load(f)

            assert "summary" in loaded
            assert "task_count" in loaded
            assert loaded["task_count"] == 1
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestEvaluationPipeline:
    """Tests for EvaluationPipeline class."""

    def test_pipeline_initialization_default(self):
        """Test default pipeline initialization."""
        pipeline = EvaluationPipeline()
        assert len(pipeline.evaluators) == 4  # All 4 evaluators

    def test_pipeline_initialization_custom_config(self):
        """Test pipeline initialization with custom config."""
        config = EvaluationConfig(
            run_correctness=True,
            run_robustness=False,
            run_safety=True,
            run_hallucination=False
        )
        pipeline = EvaluationPipeline(config=config)

        assert EvaluationType.CORRECTNESS in pipeline.evaluators
        assert EvaluationType.ROBUSTNESS not in pipeline.evaluators
        assert EvaluationType.SAFETY in pipeline.evaluators
        assert EvaluationType.HALLUCINATION not in pipeline.evaluators

    def test_pipeline_with_generate_fn(self, mock_generate_fn):
        """Test pipeline with generate function for robustness."""
        pipeline = EvaluationPipeline(generate_fn=mock_generate_fn)
        assert pipeline.generate_fn is not None

    def test_evaluate_task_all_evaluators(self, sample_evaluation_task):
        """Test evaluating a task with all evaluators."""
        pipeline = EvaluationPipeline()
        result = pipeline.evaluate_task(sample_evaluation_task)

        assert isinstance(result, TaskEvaluationResult)
        assert result.task_id == sample_evaluation_task.task_id
        assert len(result.results) == 4
        assert 0 <= result.overall_score <= 1

    def test_evaluate_task_selective_evaluators(self, sample_evaluation_task):
        """Test evaluating with selective evaluators."""
        config = EvaluationConfig(
            run_correctness=True,
            run_robustness=False,
            run_safety=False,
            run_hallucination=False
        )
        pipeline = EvaluationPipeline(config=config)
        result = pipeline.evaluate_task(sample_evaluation_task)

        assert len(result.results) == 1
        assert EvaluationType.CORRECTNESS in result.results

    def test_evaluate_task_handles_evaluator_errors(self, sample_evaluation_task):
        """Test that pipeline handles evaluator errors gracefully."""
        pipeline = EvaluationPipeline()

        # Patch one evaluator to raise an error
        with patch.object(
            pipeline.evaluators[EvaluationType.SAFETY],
            'evaluate',
            side_effect=ValueError("Test error")
        ):
            result = pipeline.evaluate_task(sample_evaluation_task)

            # Should still return result with error captured
            assert EvaluationType.SAFETY in result.results
            safety_result = result.results[EvaluationType.SAFETY]
            assert safety_result.score == 0.0
            assert safety_result.passed is False

    def test_evaluate_batch(self, sample_evaluation_task):
        """Test batch evaluation."""
        pipeline = EvaluationPipeline()
        tasks = [sample_evaluation_task, sample_evaluation_task]

        report = pipeline.evaluate_batch(tasks)

        assert isinstance(report, EvaluationReport)
        assert len(report.task_results) == 2
        assert "summary" in report.__dict__

    def test_evaluate_batch_with_progress_callback(self, sample_evaluation_task):
        """Test batch evaluation with progress callback."""
        pipeline = EvaluationPipeline()
        tasks = [sample_evaluation_task, sample_evaluation_task]
        progress_calls = []

        def progress_callback(current, total):
            progress_calls.append((current, total))

        pipeline.evaluate_batch(tasks, progress_callback=progress_callback)

        assert len(progress_calls) == 2
        assert progress_calls[0] == (1, 2)
        assert progress_calls[1] == (2, 2)

    def test_calculate_overall_score(self, sample_passing_result, sample_evaluation_result):
        """Test overall score calculation."""
        pipeline = EvaluationPipeline()
        results = {
            EvaluationType.CORRECTNESS: sample_passing_result,
            EvaluationType.SAFETY: sample_evaluation_result
        }

        score = pipeline._calculate_overall_score(results)

        assert 0 <= score <= 1

    def test_calculate_overall_score_empty(self):
        """Test overall score with no results."""
        pipeline = EvaluationPipeline()
        score = pipeline._calculate_overall_score({})
        assert score == 0.0

    def test_generate_summary(self, sample_passing_result):
        """Test summary generation."""
        task_result = TaskEvaluationResult(
            task_id="task_001",
            input_text="test",
            generated_output="test",
            results={EvaluationType.CORRECTNESS: sample_passing_result},
            overall_score=0.95,
            overall_passed=True
        )
        pipeline = EvaluationPipeline()
        summary = pipeline._generate_summary([task_result])

        assert "total_tasks" in summary
        assert "passed_tasks" in summary
        assert "failed_tasks" in summary
        assert "pass_rate" in summary
        assert "average_overall_score" in summary
        assert "evaluator_stats" in summary

    def test_generate_summary_empty(self):
        """Test summary generation with no tasks."""
        pipeline = EvaluationPipeline()
        summary = pipeline._generate_summary([])

        assert "error" in summary


class TestMetricsCalculator:
    """Tests for MetricsCalculator class."""

    def test_pass_at_k_all_pass(self):
        """Test pass@k when all results pass."""
        results = [
            EvaluationResult(EvaluationType.CORRECTNESS, 0.9, True),
            EvaluationResult(EvaluationType.CORRECTNESS, 0.8, True),
            EvaluationResult(EvaluationType.CORRECTNESS, 0.85, True),
        ]
        score = MetricsCalculator.calculate_pass_at_k(results, k=1)
        assert score == 1.0

    def test_pass_at_k_none_pass(self):
        """Test pass@k when no results pass."""
        results = [
            EvaluationResult(EvaluationType.CORRECTNESS, 0.3, False),
            EvaluationResult(EvaluationType.CORRECTNESS, 0.2, False),
        ]
        score = MetricsCalculator.calculate_pass_at_k(results, k=1)
        assert score == 0.0

    def test_pass_at_k_partial(self):
        """Test pass@k with partial success."""
        results = [
            EvaluationResult(EvaluationType.CORRECTNESS, 0.9, True),
            EvaluationResult(EvaluationType.CORRECTNESS, 0.3, False),
            EvaluationResult(EvaluationType.CORRECTNESS, 0.3, False),
        ]
        # With k=1 and at least 1 passing, score is 1.0 (probability of picking at least 1 success)
        score = MetricsCalculator.calculate_pass_at_k(results, k=1)
        assert score == 1.0

        # With k=2, we need to check if we'd get at least one success in 2 picks
        score_k2 = MetricsCalculator.calculate_pass_at_k(results, k=2)
        assert 0 < score_k2 <= 1

    def test_pass_at_k_when_k_larger_than_n(self):
        """Test pass@k when k > n."""
        results = [
            EvaluationResult(EvaluationType.CORRECTNESS, 0.9, True),
        ]
        score = MetricsCalculator.calculate_pass_at_k(results, k=5)
        # k should be capped to n
        assert score == 1.0

    def test_issue_density_calculation(self):
        """Test issue density calculation."""
        results = [
            EvaluationResult(
                EvaluationType.SAFETY, 0.5, False,
                issues=[Issue(Severity.HIGH, "test", "issue1"),
                        Issue(Severity.LOW, "test", "issue2")]
            ),
            EvaluationResult(
                EvaluationType.SAFETY, 0.7, True,
                issues=[Issue(Severity.LOW, "test", "issue3")]
            ),
        ]

        density = MetricsCalculator.calculate_issue_density(results, code_lines=30)
        assert density == 3 / 30  # 3 issues / 30 lines

    def test_issue_density_zero_lines(self):
        """Test issue density with zero lines."""
        results = []
        density = MetricsCalculator.calculate_issue_density(results, code_lines=0)
        assert density == 0.0

    def test_severity_score_no_issues(self):
        """Test severity score with no issues."""
        score = MetricsCalculator.severity_score([])
        assert score == 0.0

    def test_severity_score_all_critical(self):
        """Test severity score with all critical issues."""
        issues = [
            Issue(Severity.CRITICAL, "test", "issue1"),
            Issue(Severity.CRITICAL, "test", "issue2"),
        ]
        score = MetricsCalculator.severity_score(issues)
        assert score == 1.0

    def test_severity_score_mixed(self):
        """Test severity score with mixed severities."""
        issues = [
            Issue(Severity.CRITICAL, "test", "issue1"),
            Issue(Severity.LOW, "test", "issue2"),
        ]
        score = MetricsCalculator.severity_score(issues)
        # (1.0 + 0.2) / 2 = 0.6
        assert 0 < score < 1


class TestQuickEvaluate:
    """Tests for quick_evaluate function."""

    def test_quick_evaluate_basic(self, sample_valid_python):
        """Test basic quick_evaluate usage."""
        result = quick_evaluate(sample_valid_python)

        assert isinstance(result, TaskEvaluationResult)
        assert result.task_id == "quick_eval"
        assert len(result.results) == 4

    def test_quick_evaluate_with_prompt(self, sample_valid_python):
        """Test quick_evaluate with prompt."""
        result = quick_evaluate(sample_valid_python, prompt="Write code")

        assert result.input_text == "Write code"

    def test_quick_evaluate_non_python(self):
        """Test quick_evaluate with non-Python code."""
        result = quick_evaluate(
            "const x = 1;",
            language="javascript"
        )

        assert isinstance(result, TaskEvaluationResult)


class TestGenerateEvaluationReport:
    """Tests for generate_evaluation_report function."""

    def test_generate_report_basic(self):
        """Test basic report generation."""
        tasks = [
            {"prompt": "Write a function", "code": "def foo(): pass"},
            {"prompt": "Write a class", "code": "class Foo: pass"},
        ]

        report = generate_evaluation_report(tasks)

        assert isinstance(report, EvaluationReport)
        assert len(report.task_results) == 2

    def test_generate_report_with_output_path(self):
        """Test report generation with file output."""
        tasks = [
            {"prompt": "Write code", "code": "x = 1"},
        ]

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            report = generate_evaluation_report(tasks, output_path=temp_path)

            assert Path(temp_path).exists()
            with open(temp_path, 'r') as f:
                loaded = json.load(f)
            assert "summary" in loaded
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_generate_report_with_reference(self):
        """Test report generation with reference output."""
        tasks = [
            {
                "prompt": "Write add",
                "code": "def add(a, b): return a + b",
                "reference": "def add(x, y): return x + y"
            },
        ]

        report = generate_evaluation_report(tasks)
        assert len(report.task_results) == 1

    def test_generate_report_with_metadata(self):
        """Test report generation with metadata."""
        tasks = [
            {
                "prompt": "Write function",
                "code": "def foo(): pass",
                "metadata": {"difficulty": "easy"}
            },
        ]

        report = generate_evaluation_report(tasks)
        assert len(report.task_results) == 1


class TestOverallPassedLogic:
    """Tests for overall_passed determination."""

    def test_all_pass_overall_passes(self, sample_evaluation_task):
        """Test that all passing results means overall passes."""
        config = EvaluationConfig(
            correctness_threshold=0.0,
            robustness_threshold=0.0,
            safety_threshold=0.0,
            hallucination_threshold=0.0
        )
        pipeline = EvaluationPipeline(config=config)
        result = pipeline.evaluate_task(sample_evaluation_task)

        # With low thresholds, all should pass
        assert result.overall_passed is True

    def test_one_fail_overall_fails(self, sample_invalid_python):
        """Test that one failing result means overall fails."""
        pipeline = EvaluationPipeline()
        task = EvaluationTask(
            task_id="test",
            input_text="Write code",
            generated_output=sample_invalid_python
        )
        result = pipeline.evaluate_task(task)

        # With invalid syntax, correctness should fail
        assert result.overall_passed is False


class TestMissingCoverage:
    """Tests for previously uncovered code paths."""

    def test_report_load(self, sample_passing_result):
        """Test EvaluationReport.load() method (lines 96-99)."""
        task_result = TaskEvaluationResult(
            task_id="task_001",
            input_text="test",
            generated_output="test",
            results={EvaluationType.CORRECTNESS: sample_passing_result},
            overall_score=0.95,
            overall_passed=True
        )
        config = EvaluationConfig()
        report = EvaluationReport(
            config=config,
            task_results=[task_result],
            summary={"pass_rate": 1.0}
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            report.save(temp_path)

            # Test the load method
            loaded = EvaluationReport.load(temp_path)

            # load() returns a dict (simplified implementation)
            assert isinstance(loaded, dict)
            assert "summary" in loaded
            assert loaded["task_count"] == 1
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_calculate_overall_score_zero_weight(self, sample_passing_result):
        """Test overall score calculation with zero total weight (line 241)."""
        pipeline = EvaluationPipeline()
        # Set all weights to 0 to trigger the total_weight == 0 path
        pipeline.config.weights = {
            "correctness": 0,
            "robustness": 0,
            "safety": 0,
            "hallucination": 0,
        }

        # With non-empty results but all weights 0
        results = {
            EvaluationType.CORRECTNESS: sample_passing_result,
        }
        score = pipeline._calculate_overall_score(results)
        # When total_weight is 0, should return 0.0
        assert score == 0.0

    def test_calculate_overall_score_with_missing_weights(self, sample_passing_result):
        """Test overall score when evaluation type not in weights."""
        pipeline = EvaluationPipeline()
        # Manually set weights without one type
        pipeline.config.weights = {"correctness": 0.5}  # Missing others

        results = {
            EvaluationType.CORRECTNESS: sample_passing_result,
            EvaluationType.SAFETY: sample_passing_result,  # Not in weights
        }

        score = pipeline._calculate_overall_score(results)
        # Should use default weight of 0.25 for missing types
        assert 0 < score <= 1
