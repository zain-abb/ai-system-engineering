"""
Pass@k evaluation for code generation.

Pass@k measures the probability that at least one of k generated
samples passes all test cases, providing a more robust metric
than single-sample evaluation.

Formula:
    pass@k = 1 - C(n-c, k) / C(n, k)

Where:
    n = total samples generated
    c = number of correct samples
    k = number of samples considered
"""

import asyncio
import time
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

from src.evaluation.base import (
    EvaluationTask,
    EvaluationResult,
    EvaluationType,
)
from src.evaluation.correctness import CorrectnessEvaluator

logger = logging.getLogger(__name__)


@dataclass
class SampleResult:
    """Result for a single generated sample."""
    sample_id: int
    code: str
    passed: bool
    correctness_score: float
    execution_results: Dict[str, Any] = field(default_factory=dict)
    temperature: float = 0.7
    generation_time: float = 0.0


@dataclass
class PassAtKResult:
    """Results for pass@k evaluation of a single task."""
    task_id: str
    num_samples: int
    num_correct: int
    pass_at_k: Dict[int, float]  # k -> pass@k score
    samples: List[SampleResult] = field(default_factory=list)
    best_sample: Optional[SampleResult] = None
    average_score: float = 0.0

    @property
    def pass_rate(self) -> float:
        """Simple pass rate (pass@1 approximation)."""
        return self.num_correct / self.num_samples if self.num_samples > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "task_id": self.task_id,
            "num_samples": self.num_samples,
            "num_correct": self.num_correct,
            "pass_at_k": self.pass_at_k,
            "pass_rate": self.pass_rate,
            "average_score": self.average_score,
            "best_sample": {
                "sample_id": self.best_sample.sample_id,
                "code": self.best_sample.code[:200] + "..." if len(self.best_sample.code) > 200 else self.best_sample.code,
                "passed": self.best_sample.passed,
                "correctness_score": self.best_sample.correctness_score,
            } if self.best_sample else None,
            "samples_summary": [
                {
                    "sample_id": s.sample_id,
                    "passed": s.passed,
                    "score": s.correctness_score,
                    "temperature": s.temperature,
                }
                for s in self.samples
            ]
        }


class PassAtKEvaluator:
    """
    Evaluator for computing pass@k metrics.

    Generates multiple code samples for each task and computes
    the probability of at least one passing.
    """

    def __init__(
        self,
        client=None,
        num_samples: int = 10,
        k_values: Optional[List[int]] = None,
        temperatures: Optional[List[float]] = None,
        max_concurrent: int = 3,
        correctness_threshold: float = 0.7
    ):
        """
        Initialize the Pass@k evaluator.

        Args:
            client: ClaudeClient instance for code generation (optional for evaluation-only mode)
            num_samples: Number of samples to generate per task
            k_values: List of k values to compute pass@k for
            temperatures: List of temperatures for diverse generation
            max_concurrent: Maximum concurrent generations
            correctness_threshold: Threshold for considering a sample as correct
        """
        self.client = client
        self.num_samples = num_samples
        self.k_values = k_values or [1, 5, 10]
        self.temperatures = temperatures or [0.2, 0.4, 0.6, 0.8]
        self.max_concurrent = max_concurrent
        self.correctness_evaluator = CorrectnessEvaluator(threshold=correctness_threshold)

    def compute_pass_at_k(self, n: int, c: int, k: int) -> float:
        """
        Compute pass@k using the unbiased estimator.

        Args:
            n: Total number of samples
            c: Number of correct samples
            k: Number of samples to consider

        Returns:
            pass@k probability
        """
        if k > n:
            raise ValueError(f"k ({k}) cannot be greater than n ({n})")

        if c == n:
            # All samples passed
            return 1.0

        if n - c < k:
            # More correct samples than n - k
            return 1.0

        # Use the product formula for numerical stability:
        # pass@k = 1 - prod_{i=0}^{k-1} (n-c-i) / (n-i)
        result = 1.0
        for i in range(k):
            result *= (n - c - i) / (n - i)

        return 1.0 - result

    async def generate_sample(
        self,
        prompt: str,
        temperature: float,
        sample_id: int,
        system_prompt: Optional[str] = None
    ) -> SampleResult:
        """
        Generate a single code sample.

        Args:
            prompt: The code generation prompt
            temperature: Sampling temperature
            sample_id: Identifier for this sample
            system_prompt: Optional system prompt

        Returns:
            SampleResult with generated code
        """
        if self.client is None:
            raise ValueError("ClaudeClient required for code generation")

        start_time = time.time()

        try:
            response = await asyncio.to_thread(
                self.client.generate,
                prompt=prompt,
                system_prompt=system_prompt or "You are an expert Python programmer. Generate clean, correct code.",
                temperature=temperature,
                max_tokens=2048
            )

            code = self._extract_code(response)
            generation_time = time.time() - start_time

            return SampleResult(
                sample_id=sample_id,
                code=code,
                passed=False,  # Will be set during evaluation
                correctness_score=0.0,
                execution_results={},
                temperature=temperature,
                generation_time=generation_time
            )

        except Exception as e:
            logger.error(f"Error generating sample {sample_id}: {e}")
            return SampleResult(
                sample_id=sample_id,
                code="",
                passed=False,
                correctness_score=0.0,
                execution_results={"error": str(e)},
                temperature=temperature,
                generation_time=time.time() - start_time
            )

    async def generate_samples(
        self,
        prompt: str,
        num_samples: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> List[SampleResult]:
        """
        Generate multiple code samples with varying temperatures.

        Args:
            prompt: The code generation prompt
            num_samples: Number of samples (defaults to self.num_samples)
            system_prompt: Optional system prompt

        Returns:
            List of SampleResult objects
        """
        num_samples = num_samples or self.num_samples

        # Distribute samples across temperatures
        samples_per_temp = num_samples // len(self.temperatures)
        remainder = num_samples % len(self.temperatures)

        tasks = []
        sample_id = 0

        for i, temp in enumerate(self.temperatures):
            count = samples_per_temp + (1 if i < remainder else 0)
            for _ in range(count):
                tasks.append(
                    self.generate_sample(prompt, temp, sample_id, system_prompt)
                )
                sample_id += 1

        # Run with concurrency limit
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def bounded_generate(task):
            async with semaphore:
                return await task

        samples = await asyncio.gather(*[bounded_generate(t) for t in tasks])
        return list(samples)

    def evaluate_sample(
        self,
        sample: SampleResult,
        test_cases: List[Dict[str, Any]],
        reference_code: Optional[str] = None,
        language: str = "python"
    ) -> SampleResult:
        """
        Evaluate a single sample for correctness.

        Args:
            sample: The sample to evaluate
            test_cases: Test cases for validation
            reference_code: Optional reference implementation
            language: Programming language

        Returns:
            Updated SampleResult with evaluation results
        """
        if not sample.code:
            return sample

        # Create evaluation task
        task = EvaluationTask(
            task_id=f"sample_{sample.sample_id}",
            input_text="",
            generated_output=sample.code,
            reference_output=reference_code,
            language=language,
            metadata={"test_cases": test_cases}
        )

        # Run correctness evaluation
        result = self.correctness_evaluator.evaluate(task)

        sample.passed = result.passed
        sample.correctness_score = result.score
        sample.execution_results = {
            "details": result.details,
            "issues": [i.to_dict() for i in result.issues] if result.issues else []
        }

        return sample

    def evaluate_samples(
        self,
        samples: List[SampleResult],
        test_cases: List[Dict[str, Any]],
        reference_code: Optional[str] = None,
        language: str = "python"
    ) -> List[SampleResult]:
        """
        Evaluate all samples for correctness.

        Args:
            samples: List of samples to evaluate
            test_cases: Test cases for validation
            reference_code: Optional reference implementation
            language: Programming language

        Returns:
            List of evaluated SampleResults
        """
        evaluated = []
        for sample in samples:
            evaluated.append(
                self.evaluate_sample(sample, test_cases, reference_code, language)
            )
        return evaluated

    def evaluate_code_samples(
        self,
        code_samples: List[str],
        test_cases: List[Dict[str, Any]],
        reference_code: Optional[str] = None,
        language: str = "python"
    ) -> PassAtKResult:
        """
        Evaluate a list of pre-generated code samples (no generation needed).

        This is useful when you already have generated code and just want
        to compute pass@k metrics.

        Args:
            code_samples: List of code strings
            test_cases: Test cases for validation
            reference_code: Optional reference implementation
            language: Programming language

        Returns:
            PassAtKResult with all metrics
        """
        # Create sample objects from code strings
        samples = [
            SampleResult(
                sample_id=i,
                code=code,
                passed=False,
                correctness_score=0.0,
                temperature=0.0  # Unknown for pre-generated
            )
            for i, code in enumerate(code_samples)
        ]

        # Evaluate all samples
        evaluated_samples = self.evaluate_samples(
            samples, test_cases, reference_code, language
        )

        # Compute pass@k
        return self._compute_result(
            task_id="code_evaluation",
            samples=evaluated_samples,
            k_values=self.k_values
        )

    async def evaluate_task(
        self,
        task_id: str,
        prompt: str,
        test_cases: List[Dict[str, Any]],
        reference_code: Optional[str] = None,
        system_prompt: Optional[str] = None,
        language: str = "python"
    ) -> PassAtKResult:
        """
        Evaluate a single task with pass@k metrics.

        This method generates samples and evaluates them.

        Args:
            task_id: Unique identifier for the task
            prompt: The code generation prompt
            test_cases: Test cases to verify correctness
            reference_code: Optional reference implementation
            system_prompt: Optional system prompt for generation
            language: Programming language

        Returns:
            PassAtKResult with all metrics and samples
        """
        # Generate samples
        samples = await self.generate_samples(prompt, system_prompt=system_prompt)

        # Evaluate samples
        evaluated_samples = self.evaluate_samples(
            samples, test_cases, reference_code, language
        )

        # Compute pass@k
        return self._compute_result(
            task_id=task_id,
            samples=evaluated_samples,
            k_values=self.k_values
        )

    def _compute_result(
        self,
        task_id: str,
        samples: List[SampleResult],
        k_values: List[int]
    ) -> PassAtKResult:
        """
        Compute PassAtKResult from evaluated samples.

        Args:
            task_id: Task identifier
            samples: Evaluated samples
            k_values: k values to compute

        Returns:
            PassAtKResult with all metrics
        """
        num_samples = len(samples)
        num_correct = sum(1 for s in samples if s.passed)

        # Compute pass@k for each k value
        pass_at_k = {}
        for k in k_values:
            if k <= num_samples:
                pass_at_k[k] = self.compute_pass_at_k(num_samples, num_correct, k)
            else:
                # If k > n, we can only estimate based on what we have
                pass_at_k[k] = self.compute_pass_at_k(num_samples, num_correct, num_samples)

        # Find best sample
        valid_samples = [s for s in samples if s.code]
        best_sample = max(
            valid_samples,
            key=lambda s: s.correctness_score,
            default=None
        ) if valid_samples else None

        # Calculate average score
        scores = [s.correctness_score for s in samples]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        return PassAtKResult(
            task_id=task_id,
            num_samples=num_samples,
            num_correct=num_correct,
            pass_at_k=pass_at_k,
            samples=samples,
            best_sample=best_sample,
            average_score=avg_score
        )

    def _extract_code(self, response: str) -> str:
        """
        Extract code from markdown response.

        Args:
            response: Raw response text

        Returns:
            Extracted code string
        """
        if not response:
            return ""

        # Try to extract from code blocks
        pattern = r"```(?:python)?\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL)

        if matches:
            return matches[0].strip()

        # Return as-is if no code blocks
        return response.strip()


def aggregate_pass_at_k_results(
    results: List[PassAtKResult]
) -> Dict[str, Any]:
    """
    Aggregate pass@k results across multiple tasks.

    Args:
        results: List of PassAtKResult from multiple tasks

    Returns:
        Dictionary with aggregated metrics
    """
    if not results:
        return {
            "num_tasks": 0,
            "total_samples": 0,
            "total_correct": 0,
            "average_pass_rate": 0.0,
            "average_score": 0.0,
            "pass_at_k": {}
        }

    # Collect all k values
    all_k_values = set()
    for r in results:
        all_k_values.update(r.pass_at_k.keys())
    k_values = sorted(all_k_values)

    aggregated = {
        "num_tasks": len(results),
        "total_samples": sum(r.num_samples for r in results),
        "total_correct": sum(r.num_correct for r in results),
        "average_pass_rate": sum(r.pass_rate for r in results) / len(results),
        "average_score": sum(r.average_score for r in results) / len(results),
        "pass_at_k": {}
    }

    # Aggregate pass@k for each k
    for k in k_values:
        scores = [r.pass_at_k.get(k, 0) for r in results]
        aggregated["pass_at_k"][k] = {
            "mean": sum(scores) / len(scores),
            "std": _compute_std(scores),
            "min": min(scores),
            "max": max(scores)
        }

    return aggregated


def _compute_std(values: List[float]) -> float:
    """Compute standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return variance ** 0.5


def compute_pass_at_k_simple(
    num_samples: int,
    num_correct: int,
    k: int
) -> float:
    """
    Standalone function to compute pass@k.

    Args:
        num_samples: Total number of samples (n)
        num_correct: Number of correct samples (c)
        k: Number of samples to consider

    Returns:
        pass@k probability
    """
    evaluator = PassAtKEvaluator()
    return evaluator.compute_pass_at_k(num_samples, num_correct, k)
