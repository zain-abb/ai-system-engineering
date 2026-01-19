"""Evaluation framework for LLM-generated code."""

from src.evaluation.base import (
    EvaluationType,
    Severity,
    Issue,
    EvaluationResult,
    EvaluationTask,
    BaseEvaluator,
    AggregatedResults,
)

from src.evaluation.correctness import (
    CorrectnessEvaluator,
    evaluate_correctness,
)

from src.evaluation.robustness import (
    RobustnessEvaluator,
    PromptVariation,
    evaluate_robustness,
)

from src.evaluation.safety import (
    SafetyEvaluator,
    evaluate_safety,
)

from src.evaluation.hallucination import (
    HallucinationDetector,
    detect_hallucinations,
)

from src.evaluation.metrics import (
    EvaluationConfig,
    EvaluationPipeline,
    EvaluationReport,
    TaskEvaluationResult,
    MetricsCalculator,
    quick_evaluate,
    generate_evaluation_report,
)

from src.evaluation.pass_at_k import (
    SampleResult,
    PassAtKResult,
    PassAtKEvaluator,
    aggregate_pass_at_k_results,
    compute_pass_at_k_simple,
)

__all__ = [
    # Base classes
    "EvaluationType",
    "Severity",
    "Issue",
    "EvaluationResult",
    "EvaluationTask",
    "BaseEvaluator",
    "AggregatedResults",
    # Correctness
    "CorrectnessEvaluator",
    "evaluate_correctness",
    # Robustness
    "RobustnessEvaluator",
    "PromptVariation",
    "evaluate_robustness",
    # Safety
    "SafetyEvaluator",
    "evaluate_safety",
    # Hallucination
    "HallucinationDetector",
    "detect_hallucinations",
    # Metrics
    "EvaluationConfig",
    "EvaluationPipeline",
    "EvaluationReport",
    "TaskEvaluationResult",
    "MetricsCalculator",
    "quick_evaluate",
    "generate_evaluation_report",
    # Pass@k
    "SampleResult",
    "PassAtKResult",
    "PassAtKEvaluator",
    "aggregate_pass_at_k_results",
    "compute_pass_at_k_simple",
]
