"""Metrics aggregation and evaluation pipeline."""

import json
import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.evaluation.base import (
    BaseEvaluator,
    EvaluationType,
    EvaluationTask,
    EvaluationResult,
    AggregatedResults,
    Issue,
    Severity,
)
from src.evaluation.correctness import CorrectnessEvaluator
from src.evaluation.robustness import RobustnessEvaluator
from src.evaluation.safety import SafetyEvaluator
from src.evaluation.hallucination import HallucinationDetector

logger = logging.getLogger(__name__)


@dataclass
class EvaluationConfig:
    """Configuration for the evaluation pipeline."""
    run_correctness: bool = True
    run_robustness: bool = True
    run_safety: bool = True
    run_hallucination: bool = True

    correctness_threshold: float = 0.7
    robustness_threshold: float = 0.6
    safety_threshold: float = 0.7
    hallucination_threshold: float = 0.7

    # Weights for overall score calculation
    weights: Dict[str, float] = field(default_factory=lambda: {
        "correctness": 0.35,
        "robustness": 0.20,
        "safety": 0.25,
        "hallucination": 0.20,
    })


@dataclass
class TaskEvaluationResult:
    """Complete evaluation result for a single task."""
    task_id: str
    input_text: str
    generated_output: str
    results: Dict[EvaluationType, EvaluationResult]
    overall_score: float
    overall_passed: bool
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "input_text": self.input_text[:200] + "..." if len(self.input_text) > 200 else self.input_text,
            "generated_output": self.generated_output[:500] + "..." if len(self.generated_output) > 500 else self.generated_output,
            "results": {k.value: v.to_dict() for k, v in self.results.items()},
            "overall_score": self.overall_score,
            "overall_passed": self.overall_passed,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class EvaluationReport:
    """Complete evaluation report for multiple tasks."""
    config: EvaluationConfig
    task_results: List[TaskEvaluationResult]
    summary: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "task_count": len(self.task_results),
            "tasks": [t.to_dict() for t in self.task_results],
            "timestamp": self.timestamp.isoformat()
        }

    def save(self, path: str) -> None:
        """Save report to JSON file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> 'EvaluationReport':
        """Load report from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)
        # Note: This is a simplified load, full reconstruction would need more work
        return data


class EvaluationPipeline:
    """
    Main evaluation pipeline that runs all evaluators.

    This is the primary interface for running comprehensive
    evaluations on LLM-generated code.
    """

    def __init__(
        self,
        config: Optional[EvaluationConfig] = None,
        generate_fn: Optional[Callable[[str], str]] = None
    ):
        """
        Initialize the evaluation pipeline.

        Args:
            config: Evaluation configuration
            generate_fn: Optional function to generate outputs for robustness testing
        """
        self.config = config or EvaluationConfig()
        self.generate_fn = generate_fn

        # Initialize evaluators
        self.evaluators: Dict[EvaluationType, BaseEvaluator] = {}

        if self.config.run_correctness:
            self.evaluators[EvaluationType.CORRECTNESS] = CorrectnessEvaluator(
                threshold=self.config.correctness_threshold
            )

        if self.config.run_robustness:
            self.evaluators[EvaluationType.ROBUSTNESS] = RobustnessEvaluator(
                threshold=self.config.robustness_threshold,
                generate_fn=generate_fn
            )

        if self.config.run_safety:
            self.evaluators[EvaluationType.SAFETY] = SafetyEvaluator(
                threshold=self.config.safety_threshold
            )

        if self.config.run_hallucination:
            self.evaluators[EvaluationType.HALLUCINATION] = HallucinationDetector(
                threshold=self.config.hallucination_threshold
            )

    def evaluate_task(self, task: EvaluationTask) -> TaskEvaluationResult:
        """
        Run all evaluations on a single task.

        Args:
            task: The evaluation task

        Returns:
            TaskEvaluationResult with all evaluation results
        """
        results: Dict[EvaluationType, EvaluationResult] = {}

        for eval_type, evaluator in self.evaluators.items():
            try:
                result = evaluator.evaluate(task)
                results[eval_type] = result
            except Exception as e:
                logger.error(f"Error in {eval_type.value} evaluation: {e}")
                results[eval_type] = EvaluationResult(
                    evaluation_type=eval_type,
                    score=0.0,
                    passed=False,
                    issues=[Issue(
                        severity=Severity.CRITICAL,
                        category="evaluation_error",
                        description=str(e)
                    )]
                )

        # Calculate overall score
        overall_score = self._calculate_overall_score(results)
        overall_passed = all(r.passed for r in results.values())

        return TaskEvaluationResult(
            task_id=task.task_id,
            input_text=task.input_text,
            generated_output=task.generated_output,
            results=results,
            overall_score=overall_score,
            overall_passed=overall_passed
        )

    def evaluate_batch(
        self,
        tasks: List[EvaluationTask],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> EvaluationReport:
        """
        Evaluate multiple tasks and generate a report.

        Args:
            tasks: List of evaluation tasks
            progress_callback: Optional callback(current, total) for progress updates

        Returns:
            EvaluationReport with all results and summary
        """
        task_results = []

        for i, task in enumerate(tasks):
            if progress_callback:
                progress_callback(i + 1, len(tasks))

            result = self.evaluate_task(task)
            task_results.append(result)

        # Generate summary
        summary = self._generate_summary(task_results)

        return EvaluationReport(
            config=self.config,
            task_results=task_results,
            summary=summary
        )

    def _calculate_overall_score(
        self,
        results: Dict[EvaluationType, EvaluationResult]
    ) -> float:
        """Calculate weighted overall score."""
        if not results:
            return 0.0

        total_weight = 0.0
        weighted_score = 0.0

        for eval_type, result in results.items():
            weight = self.config.weights.get(eval_type.value, 0.25)
            weighted_score += result.score * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return weighted_score / total_weight

    def _generate_summary(
        self,
        task_results: List[TaskEvaluationResult]
    ) -> Dict[str, Any]:
        """Generate summary statistics from task results."""
        if not task_results:
            return {"error": "No tasks evaluated"}

        # Overall statistics
        total_tasks = len(task_results)
        passed_tasks = sum(1 for t in task_results if t.overall_passed)
        avg_overall_score = sum(t.overall_score for t in task_results) / total_tasks

        # Per-evaluator statistics
        evaluator_stats = {}
        for eval_type in EvaluationType:
            scores = []
            passed = 0
            total_issues = 0
            severity_counts = {s.value: 0 for s in Severity}

            for task_result in task_results:
                if eval_type in task_result.results:
                    result = task_result.results[eval_type]
                    scores.append(result.score)
                    if result.passed:
                        passed += 1
                    total_issues += len(result.issues)
                    for issue in result.issues:
                        severity_counts[issue.severity.value] += 1

            if scores:
                evaluator_stats[eval_type.value] = {
                    "average_score": sum(scores) / len(scores),
                    "min_score": min(scores),
                    "max_score": max(scores),
                    "pass_rate": passed / len(scores),
                    "total_issues": total_issues,
                    "severity_breakdown": severity_counts
                }

        # Most common issues
        all_issues = []
        for task_result in task_results:
            for result in task_result.results.values():
                all_issues.extend(result.issues)

        issue_categories = {}
        for issue in all_issues:
            cat = issue.category
            if cat not in issue_categories:
                issue_categories[cat] = 0
            issue_categories[cat] += 1

        top_issues = sorted(
            issue_categories.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return {
            "total_tasks": total_tasks,
            "passed_tasks": passed_tasks,
            "failed_tasks": total_tasks - passed_tasks,
            "pass_rate": passed_tasks / total_tasks,
            "average_overall_score": avg_overall_score,
            "evaluator_stats": evaluator_stats,
            "top_issue_categories": dict(top_issues),
            "total_issues_found": len(all_issues)
        }


class MetricsCalculator:
    """
    Utility class for calculating evaluation metrics.
    """

    @staticmethod
    def calculate_pass_at_k(
        results: List[EvaluationResult],
        k: int = 1
    ) -> float:
        """
        Calculate pass@k metric.

        Args:
            results: List of evaluation results for the same task
            k: Number of attempts to consider

        Returns:
            Probability of at least one success in k attempts
        """
        n = len(results)
        c = sum(1 for r in results if r.passed)

        if n < k:
            k = n

        if c == 0:
            return 0.0
        if c >= k:
            return 1.0

        # Calculate using the formula: 1 - C(n-c, k) / C(n, k)
        from math import comb
        return 1.0 - comb(n - c, k) / comb(n, k)

    @staticmethod
    def calculate_issue_density(
        results: List[EvaluationResult],
        code_lines: int
    ) -> float:
        """
        Calculate issue density (issues per line of code).

        Args:
            results: Evaluation results
            code_lines: Number of lines of code

        Returns:
            Issues per line of code
        """
        if code_lines == 0:
            return 0.0

        total_issues = sum(len(r.issues) for r in results)
        return total_issues / code_lines

    @staticmethod
    def severity_score(issues: List[Issue]) -> float:
        """
        Calculate a severity-weighted score from issues.

        Args:
            issues: List of issues

        Returns:
            Weighted severity score (0-1, lower is better)
        """
        if not issues:
            return 0.0

        weights = {
            Severity.CRITICAL: 1.0,
            Severity.HIGH: 0.7,
            Severity.MEDIUM: 0.4,
            Severity.LOW: 0.2,
            Severity.INFO: 0.1,
        }

        total_weight = sum(weights.get(i.severity, 0.1) for i in issues)
        max_possible = len(issues) * 1.0  # All critical

        return total_weight / max_possible if max_possible > 0 else 0.0


def quick_evaluate(
    code: str,
    prompt: str = "",
    language: str = "python"
) -> TaskEvaluationResult:
    """
    Quick evaluation of generated code using all evaluators.

    Args:
        code: Generated code to evaluate
        prompt: Original prompt/input
        language: Programming language

    Returns:
        TaskEvaluationResult
    """
    pipeline = EvaluationPipeline()
    task = EvaluationTask(
        task_id="quick_eval",
        input_text=prompt,
        generated_output=code,
        language=language
    )
    return pipeline.evaluate_task(task)


def generate_evaluation_report(
    tasks: List[Dict[str, str]],
    output_path: Optional[str] = None
) -> EvaluationReport:
    """
    Generate a comprehensive evaluation report.

    Args:
        tasks: List of dicts with 'prompt' and 'code' keys
        output_path: Optional path to save the report

    Returns:
        EvaluationReport
    """
    eval_tasks = [
        EvaluationTask(
            task_id=f"task_{i}",
            input_text=t.get("prompt", ""),
            generated_output=t.get("code", ""),
            language=t.get("language", "python"),
            reference_output=t.get("reference"),
            metadata=t.get("metadata", {})
        )
        for i, t in enumerate(tasks)
    ]

    pipeline = EvaluationPipeline()
    report = pipeline.evaluate_batch(eval_tasks)

    if output_path:
        report.save(output_path)

    return report
