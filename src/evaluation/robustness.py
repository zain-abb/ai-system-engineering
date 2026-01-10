"""Robustness evaluator for LLM outputs."""

import re
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass

from src.evaluation.base import (
    BaseEvaluator,
    EvaluationType,
    EvaluationTask,
    EvaluationResult,
    Issue,
    Severity,
)

logger = logging.getLogger(__name__)


@dataclass
class PromptVariation:
    """A variation of a prompt for robustness testing."""
    name: str
    transform: Callable[[str], str]
    description: str


class RobustnessEvaluator(BaseEvaluator):
    """
    Evaluates the robustness of LLM outputs.

    Tests:
    - Consistency across paraphrased prompts
    - Handling of edge cases (empty input, long input, special chars)
    - Response to adversarial inputs
    - Stability of outputs
    """

    # Standard prompt variations
    VARIATIONS: List[PromptVariation] = [
        PromptVariation(
            name="original",
            transform=lambda x: x,
            description="Original prompt"
        ),
        PromptVariation(
            name="lowercase",
            transform=lambda x: x.lower(),
            description="All lowercase"
        ),
        PromptVariation(
            name="uppercase",
            transform=lambda x: x.upper(),
            description="All uppercase"
        ),
        PromptVariation(
            name="extra_whitespace",
            transform=lambda x: "  " + x.replace(" ", "  ") + "  ",
            description="Extra whitespace"
        ),
        PromptVariation(
            name="polite",
            transform=lambda x: f"Please {x.lower()} Thank you!",
            description="Polite phrasing"
        ),
        PromptVariation(
            name="terse",
            transform=lambda x: re.sub(r'\b(please|kindly|could you)\b', '', x, flags=re.I).strip(),
            description="Terse/minimal phrasing"
        ),
    ]

    # Edge case inputs
    EDGE_CASES = {
        "empty": "",
        "whitespace_only": "   \n\t   ",
        "very_short": "x",
        "special_chars": "!@#$%^&*()_+-=[]{}|;':\",./<>?",
        "unicode": "Write a function that handles émojis 🎉 and ñ characters",
        "long_input": "Write a function " * 100,
        "newlines": "Write\na\nfunction\nthat\nhandles\nnewlines",
        "tabs": "Write\ta\tfunction\twith\ttabs",
    }

    def __init__(
        self,
        threshold: float = 0.7,
        consistency_threshold: float = 0.6,
        generate_fn: Optional[Callable[[str], str]] = None
    ):
        """
        Initialize the robustness evaluator.

        Args:
            threshold: Minimum score to pass
            consistency_threshold: Minimum similarity for consistent outputs
            generate_fn: Function to generate outputs for variations
        """
        super().__init__(threshold)
        self.consistency_threshold = consistency_threshold
        self.generate_fn = generate_fn

    @property
    def evaluation_type(self) -> EvaluationType:
        return EvaluationType.ROBUSTNESS

    def evaluate(self, task: EvaluationTask) -> EvaluationResult:
        """Evaluate the robustness of the generated output."""
        issues = []
        details = {}
        scores = []

        output = task.generated_output
        prompt = task.input_text

        # 1. Check for empty/invalid output
        output_quality = self._check_output_quality(output)
        details["output_quality"] = output_quality
        scores.append(output_quality["score"])
        for issue in output_quality.get("issues", []):
            issues.append(issue)

        # 2. Check consistency across variations (if generate_fn provided)
        if self.generate_fn:
            consistency = self._check_consistency(prompt, output)
            details["consistency"] = consistency
            scores.append(consistency["score"])
            if consistency["score"] < self.consistency_threshold:
                issues.append(Issue(
                    severity=Severity.MEDIUM,
                    category="inconsistent_output",
                    description="Output varies significantly across prompt variations",
                    suggestion="Consider improving prompt specificity"
                ))

        # 3. Check edge case handling
        edge_case_results = self._check_edge_cases(output)
        details["edge_cases"] = edge_case_results
        scores.append(edge_case_results["score"])
        for issue in edge_case_results.get("issues", []):
            issues.append(issue)

        # 4. Check for sensitivity to perturbations
        perturbation_results = self._check_perturbation_sensitivity(prompt, output)
        details["perturbation"] = perturbation_results
        scores.append(perturbation_results["score"])

        # Calculate final score
        final_score = sum(scores) / len(scores) if scores else 0.0

        return self._create_result(
            score=final_score,
            issues=issues,
            details=details
        )

    def _check_output_quality(self, output: str) -> Dict[str, Any]:
        """Check basic output quality indicators."""
        issues = []
        score = 1.0

        # Check for empty output
        if not output or not output.strip():
            issues.append(Issue(
                severity=Severity.CRITICAL,
                category="empty_output",
                description="Output is empty or whitespace only"
            ))
            return {"score": 0.0, "issues": issues}

        # Check for very short output
        if len(output.strip()) < 10:
            issues.append(Issue(
                severity=Severity.HIGH,
                category="short_output",
                description=f"Output is very short ({len(output)} chars)"
            ))
            score -= 0.3

        # Check for repetitive patterns
        repetition_score = self._check_repetition(output)
        if repetition_score > 0.5:
            issues.append(Issue(
                severity=Severity.MEDIUM,
                category="repetitive_output",
                description="Output contains repetitive patterns"
            ))
            score -= 0.2

        # Check for truncation indicators
        truncation_indicators = ["...", "[truncated]", "[continued]", "etc."]
        if any(ind in output.lower() for ind in truncation_indicators):
            issues.append(Issue(
                severity=Severity.LOW,
                category="possibly_truncated",
                description="Output may be truncated"
            ))
            score -= 0.1

        return {"score": max(0.0, score), "issues": issues}

    def _check_consistency(self, prompt: str, original_output: str) -> Dict[str, Any]:
        """Check consistency across prompt variations."""
        if not self.generate_fn:
            return {"score": 1.0, "skipped": True}

        similarities = []
        variation_outputs = {}

        for variation in self.VARIATIONS:
            try:
                varied_prompt = variation.transform(prompt)
                varied_output = self.generate_fn(varied_prompt)
                variation_outputs[variation.name] = varied_output

                # Compute similarity with original
                similarity = self._compute_similarity(original_output, varied_output)
                similarities.append(similarity)

            except Exception as e:
                logger.warning(f"Error testing variation {variation.name}: {e}")

        if not similarities:
            return {"score": 1.0, "no_variations": True}

        avg_similarity = sum(similarities) / len(similarities)
        min_similarity = min(similarities)

        return {
            "score": avg_similarity,
            "average_similarity": avg_similarity,
            "min_similarity": min_similarity,
            "variation_count": len(similarities)
        }

    def _check_edge_cases(self, output: str) -> Dict[str, Any]:
        """Check output for edge case handling indicators."""
        issues = []
        checks_passed = 0
        total_checks = 0

        # Check if output handles null/None
        total_checks += 1
        if "none" in output.lower() or "null" in output.lower() or "if not" in output.lower():
            checks_passed += 1
        else:
            issues.append(Issue(
                severity=Severity.LOW,
                category="no_null_handling",
                description="Output may not handle null/None values"
            ))

        # Check if output handles empty input
        total_checks += 1
        empty_indicators = ["empty", "len(", "if not ", "[]", "''", '""']
        if any(ind in output for ind in empty_indicators):
            checks_passed += 1
        else:
            issues.append(Issue(
                severity=Severity.LOW,
                category="no_empty_handling",
                description="Output may not handle empty inputs"
            ))

        # Check for error handling
        total_checks += 1
        error_indicators = ["try:", "except", "raise", "error", "Error"]
        if any(ind in output for ind in error_indicators):
            checks_passed += 1
        else:
            issues.append(Issue(
                severity=Severity.INFO,
                category="no_error_handling",
                description="Output may lack error handling"
            ))

        score = checks_passed / total_checks if total_checks > 0 else 0.0

        return {
            "score": score,
            "checks_passed": checks_passed,
            "total_checks": total_checks,
            "issues": issues
        }

    def _check_perturbation_sensitivity(
        self,
        prompt: str,
        output: str
    ) -> Dict[str, Any]:
        """Check sensitivity to small perturbations in the prompt."""
        # Simple perturbations
        perturbations = [
            prompt + " ",  # trailing space
            " " + prompt,  # leading space
            prompt.replace(".", ""),  # remove periods
            prompt + ".",  # add period
        ]

        if not self.generate_fn:
            return {"score": 1.0, "skipped": True}

        similarities = []
        for perturbed in perturbations:
            try:
                perturbed_output = self.generate_fn(perturbed)
                similarity = self._compute_similarity(output, perturbed_output)
                similarities.append(similarity)
            except Exception as e:
                logger.warning(f"Perturbation test error: {e}")

        if not similarities:
            return {"score": 1.0, "no_tests": True}

        avg_stability = sum(similarities) / len(similarities)

        return {
            "score": avg_stability,
            "average_stability": avg_stability,
            "perturbation_count": len(similarities)
        }

    def _check_repetition(self, text: str) -> float:
        """Check for repetitive patterns in text."""
        words = text.lower().split()
        if len(words) < 10:
            return 0.0

        # Check for repeated sequences
        seen = set()
        repeated = 0

        for i in range(len(words) - 2):
            trigram = tuple(words[i:i+3])
            if trigram in seen:
                repeated += 1
            seen.add(trigram)

        return repeated / len(words)

    def _compute_similarity(self, text1: str, text2: str) -> float:
        """Compute similarity between two texts."""
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        return len(intersection) / len(union)

    def test_with_edge_cases(
        self,
        generate_fn: Callable[[str], str]
    ) -> Dict[str, Any]:
        """Test the generator with edge case inputs."""
        results = {}

        for case_name, case_input in self.EDGE_CASES.items():
            try:
                output = generate_fn(case_input)
                results[case_name] = {
                    "input": case_input[:50],
                    "output_length": len(output) if output else 0,
                    "has_output": bool(output and output.strip()),
                    "error": None
                }
            except Exception as e:
                results[case_name] = {
                    "input": case_input[:50],
                    "error": str(e)
                }

        return results


def evaluate_robustness(
    output: str,
    prompt: str = "",
    generate_fn: Optional[Callable[[str], str]] = None
) -> EvaluationResult:
    """
    Quick function to evaluate output robustness.

    Args:
        output: Generated output to evaluate
        prompt: Original prompt (for consistency testing)
        generate_fn: Function to generate variations

    Returns:
        EvaluationResult
    """
    evaluator = RobustnessEvaluator(generate_fn=generate_fn)
    task = EvaluationTask(
        task_id="quick_eval",
        input_text=prompt,
        generated_output=output
    )
    return evaluator.evaluate(task)
