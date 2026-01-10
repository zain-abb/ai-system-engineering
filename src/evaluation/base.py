"""Base classes for LLM output evaluation."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class EvaluationType(Enum):
    """Types of evaluation."""
    CORRECTNESS = "correctness"
    ROBUSTNESS = "robustness"
    SAFETY = "safety"
    HALLUCINATION = "hallucination"


class Severity(Enum):
    """Severity levels for issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Issue:
    """An issue found during evaluation."""
    severity: Severity
    category: str
    description: str
    location: Optional[str] = None  # e.g., line number, function name
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "category": self.category,
            "description": self.description,
            "location": self.location,
            "suggestion": self.suggestion
        }


@dataclass
class EvaluationResult:
    """Result of an evaluation."""
    evaluation_type: EvaluationType
    score: float  # 0.0 to 1.0 (1.0 is best)
    passed: bool
    issues: List[Issue] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.HIGH)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_type": self.evaluation_type.value,
            "score": self.score,
            "passed": self.passed,
            "issue_count": self.issue_count,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "issues": [i.to_dict() for i in self.issues],
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class EvaluationTask:
    """A task to evaluate."""
    task_id: str
    input_text: str  # Original input/prompt
    generated_output: str  # LLM-generated output
    reference_output: Optional[str] = None  # Expected/reference output
    language: str = "python"
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseEvaluator(ABC):
    """Abstract base class for evaluators."""

    def __init__(self, threshold: float = 0.7):
        """
        Initialize the evaluator.

        Args:
            threshold: Minimum score to pass (0.0 to 1.0)
        """
        self.threshold = threshold
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def evaluation_type(self) -> EvaluationType:
        """Return the type of evaluation this evaluator performs."""
        pass

    @abstractmethod
    def evaluate(self, task: EvaluationTask) -> EvaluationResult:
        """
        Evaluate a single task.

        Args:
            task: The evaluation task

        Returns:
            EvaluationResult with score, issues, and details
        """
        pass

    def evaluate_batch(self, tasks: List[EvaluationTask]) -> List[EvaluationResult]:
        """
        Evaluate multiple tasks.

        Args:
            tasks: List of evaluation tasks

        Returns:
            List of EvaluationResult objects
        """
        results = []
        for task in tasks:
            try:
                result = self.evaluate(task)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error evaluating task {task.task_id}: {e}")
                results.append(EvaluationResult(
                    evaluation_type=self.evaluation_type,
                    score=0.0,
                    passed=False,
                    issues=[Issue(
                        severity=Severity.CRITICAL,
                        category="evaluation_error",
                        description=str(e)
                    )]
                ))
        return results

    def _create_result(
        self,
        score: float,
        issues: Optional[List[Issue]] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        """Helper to create an evaluation result."""
        return EvaluationResult(
            evaluation_type=self.evaluation_type,
            score=score,
            passed=score >= self.threshold,
            issues=issues or [],
            details=details or {}
        )


@dataclass
class AggregatedResults:
    """Aggregated results from multiple evaluations."""
    total_tasks: int
    passed_count: int
    failed_count: int
    average_score: float
    results_by_type: Dict[EvaluationType, List[EvaluationResult]]
    summary: Dict[str, Any] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.passed_count / self.total_tasks

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tasks": self.total_tasks,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "pass_rate": self.pass_rate,
            "average_score": self.average_score,
            "summary": self.summary,
            "results_by_type": {
                k.value: [r.to_dict() for r in v]
                for k, v in self.results_by_type.items()
            }
        }
