"""Tests for the robustness evaluator."""

import pytest
from unittest.mock import MagicMock, patch

from src.evaluation.base import (
    EvaluationType,
    EvaluationTask,
    Severity,
)
from src.evaluation.robustness import (
    RobustnessEvaluator,
    PromptVariation,
    evaluate_robustness,
)


class TestRobustnessEvaluatorInit:
    """Tests for RobustnessEvaluator initialization."""

    def test_default_initialization(self):
        """Test default evaluator initialization."""
        evaluator = RobustnessEvaluator()
        assert evaluator.threshold == 0.7
        assert evaluator.consistency_threshold == 0.6
        assert evaluator.generate_fn is None

    def test_custom_initialization(self, mock_generate_fn):
        """Test custom evaluator initialization."""
        evaluator = RobustnessEvaluator(
            threshold=0.8,
            consistency_threshold=0.7,
            generate_fn=mock_generate_fn
        )
        assert evaluator.threshold == 0.8
        assert evaluator.consistency_threshold == 0.7
        assert evaluator.generate_fn is not None

    def test_evaluation_type_property(self):
        """Test evaluation_type property returns ROBUSTNESS."""
        evaluator = RobustnessEvaluator()
        assert evaluator.evaluation_type == EvaluationType.ROBUSTNESS


class TestPromptVariation:
    """Tests for PromptVariation dataclass."""

    def test_prompt_variation_creation(self):
        """Test creating a PromptVariation."""
        variation = PromptVariation(
            name="test_variation",
            transform=lambda x: x.upper(),
            description="Uppercase transform"
        )
        assert variation.name == "test_variation"
        assert variation.description == "Uppercase transform"
        assert variation.transform("hello") == "HELLO"

    def test_builtin_variations_exist(self):
        """Test that builtin variations are defined."""
        assert len(RobustnessEvaluator.VARIATIONS) > 0
        variation_names = [v.name for v in RobustnessEvaluator.VARIATIONS]
        assert "original" in variation_names
        assert "lowercase" in variation_names
        assert "uppercase" in variation_names

    def test_builtin_variation_transforms(self):
        """Test that builtin variation transforms work correctly."""
        text = "Hello World"
        for variation in RobustnessEvaluator.VARIATIONS:
            result = variation.transform(text)
            assert isinstance(result, str)


class TestOutputQualityCheck:
    """Tests for output quality checking."""

    def test_empty_output_detected(self, sample_empty_output):
        """Test that empty output is detected."""
        evaluator = RobustnessEvaluator()
        task = EvaluationTask(
            task_id="test",
            input_text="Write code",
            generated_output=sample_empty_output
        )
        result = evaluator.evaluate(task)

        assert result.details["output_quality"]["score"] == 0.0
        assert any(i.category == "empty_output" for i in result.issues)
        assert any(i.severity == Severity.CRITICAL for i in result.issues)

    def test_whitespace_only_output_detected(self):
        """Test that whitespace-only output is detected."""
        evaluator = RobustnessEvaluator()
        task = EvaluationTask(
            task_id="test",
            input_text="Write code",
            generated_output="   \n\t   "
        )
        result = evaluator.evaluate(task)

        assert result.details["output_quality"]["score"] == 0.0
        assert any(i.category == "empty_output" for i in result.issues)

    def test_short_output_detected(self, sample_short_output):
        """Test that very short output is flagged."""
        evaluator = RobustnessEvaluator()
        task = EvaluationTask(
            task_id="test",
            input_text="Write code",
            generated_output=sample_short_output
        )
        result = evaluator.evaluate(task)

        assert any(i.category == "short_output" for i in result.issues)
        assert any(i.severity == Severity.HIGH for i in result.issues)

    def test_truncated_output_detected(self, sample_truncated_output):
        """Test that truncated output is flagged."""
        evaluator = RobustnessEvaluator()
        task = EvaluationTask(
            task_id="test",
            input_text="Write code",
            generated_output=sample_truncated_output
        )
        result = evaluator.evaluate(task)

        assert any(i.category == "possibly_truncated" for i in result.issues)

    def test_repetitive_output_detected(self, sample_repetitive_output):
        """Test that repetitive output is flagged."""
        evaluator = RobustnessEvaluator()
        task = EvaluationTask(
            task_id="test",
            input_text="Write code",
            generated_output=sample_repetitive_output
        )
        result = evaluator.evaluate(task)

        assert any(i.category == "repetitive_output" for i in result.issues)

    def test_good_output_quality(self, sample_valid_python):
        """Test that good quality output passes."""
        evaluator = RobustnessEvaluator()
        task = EvaluationTask(
            task_id="test",
            input_text="Write code",
            generated_output=sample_valid_python
        )
        result = evaluator.evaluate(task)

        assert result.details["output_quality"]["score"] > 0.5


class TestConsistencyCheck:
    """Tests for consistency checking."""

    def test_consistency_without_generate_fn(self, sample_valid_python):
        """Test that consistency is skipped without generate_fn."""
        evaluator = RobustnessEvaluator(generate_fn=None)
        task = EvaluationTask(
            task_id="test",
            input_text="Write code",
            generated_output=sample_valid_python
        )
        result = evaluator.evaluate(task)

        # Consistency should not be checked
        assert "consistency" not in result.details

    def test_consistency_with_generate_fn(self, sample_valid_python):
        """Test consistency checking with generate_fn."""
        def mock_generate(prompt):
            # Return consistent output
            return sample_valid_python

        evaluator = RobustnessEvaluator(generate_fn=mock_generate)
        task = EvaluationTask(
            task_id="test",
            input_text="Write a function to add numbers",
            generated_output=sample_valid_python
        )
        result = evaluator.evaluate(task)

        assert "consistency" in result.details
        assert "score" in result.details["consistency"]

    def test_consistency_low_score_creates_issue(self, sample_valid_python):
        """Test that low consistency creates an issue."""
        call_count = [0]

        def inconsistent_generate(prompt):
            call_count[0] += 1
            return f"different output {call_count[0]}"

        evaluator = RobustnessEvaluator(
            generate_fn=inconsistent_generate,
            consistency_threshold=0.8
        )
        task = EvaluationTask(
            task_id="test",
            input_text="Write code",
            generated_output=sample_valid_python
        )
        result = evaluator.evaluate(task)

        # Should flag inconsistent output
        if result.details["consistency"]["score"] < 0.8:
            assert any(i.category == "inconsistent_output" for i in result.issues)

    def test_consistency_handles_generate_fn_errors(self, sample_valid_python):
        """Test that generate_fn errors are handled gracefully."""
        def failing_generate(prompt):
            raise ValueError("Generate failed")

        evaluator = RobustnessEvaluator(generate_fn=failing_generate)
        task = EvaluationTask(
            task_id="test",
            input_text="Write code",
            generated_output=sample_valid_python
        )
        result = evaluator.evaluate(task)

        # Should handle errors gracefully
        assert "consistency" in result.details


class TestEdgeCaseHandling:
    """Tests for edge case handling detection."""

    def test_edge_case_handling_detected(self, sample_code_with_edge_case_handling):
        """Test that edge case handling is detected."""
        evaluator = RobustnessEvaluator()
        task = EvaluationTask(
            task_id="test",
            input_text="Write code",
            generated_output=sample_code_with_edge_case_handling
        )
        result = evaluator.evaluate(task)

        assert "edge_cases" in result.details
        assert result.details["edge_cases"]["score"] > 0

    def test_missing_null_handling_flagged(self):
        """Test that missing null handling is flagged."""
        code = """
def process(data):
    return data.upper()
"""
        evaluator = RobustnessEvaluator()
        task = EvaluationTask(
            task_id="test",
            input_text="Write code",
            generated_output=code
        )
        result = evaluator.evaluate(task)

        # Should have issue about null handling
        assert any(i.category == "no_null_handling" for i in result.issues)

    def test_missing_empty_handling_flagged(self):
        """Test that missing empty input handling is flagged."""
        code = """
def process(items):
    return items[0]
"""
        evaluator = RobustnessEvaluator()
        task = EvaluationTask(
            task_id="test",
            input_text="Write code",
            generated_output=code
        )
        result = evaluator.evaluate(task)

        # Should have issue about empty handling
        assert any(i.category == "no_empty_handling" for i in result.issues)


class TestPerturbationSensitivity:
    """Tests for perturbation sensitivity checking."""

    def test_perturbation_without_generate_fn(self, sample_valid_python):
        """Test perturbation is skipped without generate_fn."""
        evaluator = RobustnessEvaluator(generate_fn=None)
        task = EvaluationTask(
            task_id="test",
            input_text="Write code",
            generated_output=sample_valid_python
        )
        result = evaluator.evaluate(task)

        assert result.details["perturbation"]["skipped"] is True

    def test_perturbation_with_stable_output(self, sample_valid_python):
        """Test perturbation with stable outputs."""
        def stable_generate(prompt):
            return sample_valid_python

        evaluator = RobustnessEvaluator(generate_fn=stable_generate)
        task = EvaluationTask(
            task_id="test",
            input_text="Write code",
            generated_output=sample_valid_python
        )
        result = evaluator.evaluate(task)

        assert result.details["perturbation"]["score"] == 1.0


class TestRepetitionScoring:
    """Tests for repetition scoring algorithm."""

    def test_no_repetition(self):
        """Test repetition scoring with no repetition."""
        evaluator = RobustnessEvaluator()
        text = "This is a completely unique sentence with no repeated patterns"
        score = evaluator._check_repetition(text)
        assert score == 0.0

    def test_high_repetition(self):
        """Test repetition scoring with high repetition."""
        evaluator = RobustnessEvaluator()
        text = "hello world hello world hello world hello world " * 5
        score = evaluator._check_repetition(text)
        assert score > 0.3

    def test_short_text_no_repetition(self):
        """Test that short text returns 0 repetition."""
        evaluator = RobustnessEvaluator()
        text = "short"
        score = evaluator._check_repetition(text)
        assert score == 0.0


class TestSimilarityCalculation:
    """Tests for similarity calculation."""

    def test_identical_texts(self):
        """Test similarity of identical texts."""
        evaluator = RobustnessEvaluator()
        text = "hello world"
        similarity = evaluator._compute_similarity(text, text)
        assert similarity == 1.0

    def test_completely_different_texts(self):
        """Test similarity of completely different texts."""
        evaluator = RobustnessEvaluator()
        similarity = evaluator._compute_similarity("abc", "xyz")
        assert similarity == 0.0

    def test_partially_similar_texts(self):
        """Test similarity of partially similar texts."""
        evaluator = RobustnessEvaluator()
        text1 = "hello world"
        text2 = "hello there"
        similarity = evaluator._compute_similarity(text1, text2)
        assert 0 < similarity < 1

    def test_empty_text_similarity(self):
        """Test similarity with empty text."""
        evaluator = RobustnessEvaluator()
        assert evaluator._compute_similarity("", "hello") == 0.0
        assert evaluator._compute_similarity("hello", "") == 0.0
        assert evaluator._compute_similarity("", "") == 0.0


class TestEdgeCaseTesting:
    """Tests for edge case input testing."""

    def test_edge_cases_defined(self):
        """Test that edge cases are defined."""
        assert len(RobustnessEvaluator.EDGE_CASES) > 0
        assert "empty" in RobustnessEvaluator.EDGE_CASES
        assert "whitespace_only" in RobustnessEvaluator.EDGE_CASES
        assert "special_chars" in RobustnessEvaluator.EDGE_CASES

    def test_test_with_edge_cases(self, mock_generate_fn):
        """Test test_with_edge_cases method."""
        evaluator = RobustnessEvaluator()
        results = evaluator.test_with_edge_cases(mock_generate_fn)

        assert isinstance(results, dict)
        assert "empty" in results
        assert "whitespace_only" in results
        for case_name, case_result in results.items():
            assert "input" in case_result or "error" in case_result

    def test_test_with_edge_cases_handles_errors(self):
        """Test that test_with_edge_cases handles generator errors."""
        def failing_generate(prompt):
            raise ValueError("Generate failed")

        evaluator = RobustnessEvaluator()
        results = evaluator.test_with_edge_cases(failing_generate)

        # Should capture errors
        for case_name, case_result in results.items():
            assert "error" in case_result


class TestEvaluateRobustnessFunction:
    """Tests for the evaluate_robustness convenience function."""

    def test_evaluate_robustness_basic(self, sample_valid_python):
        """Test basic usage of evaluate_robustness function."""
        result = evaluate_robustness(sample_valid_python)

        assert result.evaluation_type == EvaluationType.ROBUSTNESS
        assert result.score >= 0

    def test_evaluate_robustness_with_prompt(self, sample_valid_python):
        """Test evaluate_robustness with prompt."""
        result = evaluate_robustness(
            sample_valid_python,
            prompt="Write a function"
        )

        assert result.evaluation_type == EvaluationType.ROBUSTNESS

    def test_evaluate_robustness_with_generate_fn(self, sample_valid_python, mock_generate_fn):
        """Test evaluate_robustness with generate function."""
        result = evaluate_robustness(
            sample_valid_python,
            prompt="Write code",
            generate_fn=mock_generate_fn
        )

        assert "consistency" in result.details


class TestScoreCalculation:
    """Tests for overall score calculation."""

    def test_score_with_good_output(self, sample_valid_python):
        """Test score calculation with good output."""
        evaluator = RobustnessEvaluator()
        task = EvaluationTask(
            task_id="test",
            input_text="Write code",
            generated_output=sample_valid_python
        )
        result = evaluator.evaluate(task)

        # Good output should have reasonable score
        assert result.score > 0.5

    def test_score_with_empty_output(self, sample_empty_output):
        """Test score calculation with empty output."""
        evaluator = RobustnessEvaluator()
        task = EvaluationTask(
            task_id="test",
            input_text="Write code",
            generated_output=sample_empty_output
        )
        result = evaluator.evaluate(task)

        # Empty output should have low score
        assert result.score < 0.5
        assert result.passed is False

    def test_pass_threshold(self, sample_valid_python):
        """Test that pass/fail is determined by threshold."""
        evaluator = RobustnessEvaluator(threshold=0.5)
        task = EvaluationTask(
            task_id="test",
            input_text="Write code",
            generated_output=sample_valid_python
        )
        result = evaluator.evaluate(task)

        if result.score >= 0.5:
            assert result.passed is True
        else:
            assert result.passed is False


class TestMissingCoverage:
    """Tests for previously uncovered code paths."""

    def test_check_consistency_direct_call_no_generate_fn(self):
        """Test _check_consistency returns skipped when called directly without generate_fn (line 205)."""
        evaluator = RobustnessEvaluator(generate_fn=None)
        # Call the method directly
        result = evaluator._check_consistency("test prompt", "test output")

        assert result["score"] == 1.0
        assert result["skipped"] is True
