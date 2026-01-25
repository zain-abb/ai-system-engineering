"""
Multi-model experiment runner for comparative analysis.

Runs identical benchmarks across multiple Claude models and
generates comparative analysis of performance, cost, and quality.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable

from experiments.config import ExperimentConfig
from experiments.runner import ExperimentRunner, ExperimentJSONEncoder
from experiments.models import ClaudeModel, get_model_config, estimate_multi_model_cost

logger = logging.getLogger(__name__)


@dataclass
class ModelExperimentResult:
    """Results from a single model experiment."""
    model: str
    model_display_name: str
    pass_rate: float
    average_score: float
    correctness_score: float
    robustness_score: float
    safety_score: float
    hallucination_score: float
    total_cost_usd: float
    average_latency_ms: float
    task_results: List[Dict[str, Any]] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "model": self.model,
            "model_display_name": self.model_display_name,
            "pass_rate": self.pass_rate,
            "average_score": self.average_score,
            "correctness_score": self.correctness_score,
            "robustness_score": self.robustness_score,
            "safety_score": self.safety_score,
            "hallucination_score": self.hallucination_score,
            "total_cost_usd": self.total_cost_usd,
            "average_latency_ms": self.average_latency_ms,
            "duration_seconds": self.duration_seconds,
            "task_count": len(self.task_results),
        }


@dataclass
class MultiModelComparisonResult:
    """Results from multi-model comparison experiment."""
    experiment_id: str
    timestamp: str
    model_results: Dict[str, ModelExperimentResult] = field(default_factory=dict)
    best_model_by_score: str = ""
    best_model_by_cost_efficiency: str = ""
    score_ranking: List[str] = field(default_factory=list)
    cost_efficiency_ranking: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "experiment_id": self.experiment_id,
            "timestamp": self.timestamp,
            "model_results": {
                k: v.to_dict() for k, v in self.model_results.items()
            },
            "best_model_by_score": self.best_model_by_score,
            "best_model_by_cost_efficiency": self.best_model_by_cost_efficiency,
            "score_ranking": self.score_ranking,
            "cost_efficiency_ranking": self.cost_efficiency_ranking,
            "config": self.config,
        }


class MultiModelExperimentRunner:
    """
    Runner for comparative experiments across multiple Claude models.

    Runs identical benchmarks across each model sequentially and
    generates comparative analysis.
    """

    def __init__(
        self,
        models: List[ClaudeModel],
        output_dir: str = "experiments/results/multi_model",
        base_config: Optional[ExperimentConfig] = None
    ):
        """
        Initialize the multi-model runner.

        Args:
            models: List of ClaudeModel enums to compare
            output_dir: Base output directory
            base_config: Base experiment config (will be modified per model)
        """
        self.models = models
        self.output_dir = output_dir
        self.base_config = base_config or ExperimentConfig()
        self.experiment_id = f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def estimate_total_cost(
        self,
        num_tasks: int,
        samples_per_task: int = 1
    ) -> Dict[str, Any]:
        """
        Estimate total cost for running comparison across all models.

        Args:
            num_tasks: Number of tasks to evaluate
            samples_per_task: Number of samples per task

        Returns:
            Cost estimate dictionary
        """
        return estimate_multi_model_cost(
            self.models,
            num_tasks,
            samples_per_task
        )

    def run_single_model_experiment(
        self,
        model: ClaudeModel,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> ModelExperimentResult:
        """
        Run experiment for a single model.

        Args:
            model: The Claude model to use
            progress_callback: Optional progress callback

        Returns:
            ModelExperimentResult with all metrics
        """
        model_config = get_model_config(model)

        # Create model-specific config
        config = ExperimentConfig(
            dataset_path=self.base_config.dataset_path,
            output_dir=os.path.join(self.output_dir, self.experiment_id),
            experiment_name=f"{model.name.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            model=model_config.model_id,
            temperature=self.base_config.temperature,
            max_tokens=model_config.max_tokens,
            eval_config=self.base_config.eval_config,
            save_checkpoints=self.base_config.save_checkpoints,
            checkpoint_interval=self.base_config.checkpoint_interval,
            verbose=self.base_config.verbose,
            categories=self.base_config.categories,
            difficulties=self.base_config.difficulties,
            max_tasks=self.base_config.max_tasks,
        )

        # Run experiment
        runner = ExperimentRunner(config)
        start_time = datetime.now()
        results = runner.run_experiment(progress_callback=progress_callback)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Extract metrics from evaluation report
        if results.evaluation_report and results.evaluation_report.summary:
            summary = results.evaluation_report.summary
            evaluator_stats = summary.get("evaluator_stats", {})

            return ModelExperimentResult(
                model=model_config.model_id,
                model_display_name=model_config.display_name,
                pass_rate=summary.get("pass_rate", 0.0),
                average_score=summary.get("average_overall_score", 0.0),
                correctness_score=evaluator_stats.get("correctness", {}).get("average_score", 0.0),
                robustness_score=evaluator_stats.get("robustness", {}).get("average_score", 0.0),
                safety_score=evaluator_stats.get("safety", {}).get("average_score", 0.0),
                hallucination_score=evaluator_stats.get("hallucination", {}).get("average_score", 0.0),
                total_cost_usd=results.api_cost,
                average_latency_ms=model_config.expected_latency_ms,
                task_results=results.task_results,
                duration_seconds=duration,
            )
        else:
            # Return empty result if no evaluation report
            return ModelExperimentResult(
                model=model_config.model_id,
                model_display_name=model_config.display_name,
                pass_rate=0.0,
                average_score=0.0,
                correctness_score=0.0,
                robustness_score=0.0,
                safety_score=0.0,
                hallucination_score=0.0,
                total_cost_usd=results.api_cost,
                average_latency_ms=model_config.expected_latency_ms,
                task_results=results.task_results,
                duration_seconds=duration,
            )

    def run_comparison(
        self,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> MultiModelComparisonResult:
        """
        Run comparison experiment across all models.

        Args:
            progress_callback: Optional callback(model_name, current_model_idx, total_models)

        Returns:
            MultiModelComparisonResult with comparative analysis
        """
        # Create output directory
        output_path = os.path.join(self.output_dir, self.experiment_id)
        os.makedirs(output_path, exist_ok=True)

        if self.base_config.verbose:
            print(f"\nStarting multi-model comparison: {self.experiment_id}")
            print(f"Models: {[m.name for m in self.models]}")
            print(f"Output directory: {output_path}\n")

        model_results: Dict[str, ModelExperimentResult] = {}

        # Run experiment for each model sequentially
        for i, model in enumerate(self.models):
            model_config = get_model_config(model)

            if progress_callback:
                progress_callback(model_config.display_name, i + 1, len(self.models))
            elif self.base_config.verbose:
                print(f"\n{'='*60}")
                print(f"Running experiment for {model_config.display_name} ({i+1}/{len(self.models)})")
                print(f"{'='*60}")

            try:
                result = self.run_single_model_experiment(model)
                model_results[model.value] = result

                if self.base_config.verbose:
                    print(f"\n{model_config.display_name} Results:")
                    print(f"  Pass Rate: {result.pass_rate*100:.1f}%")
                    print(f"  Average Score: {result.average_score:.3f}")
                    print(f"  Cost: ${result.total_cost_usd:.4f}")

            except Exception as e:
                logger.error(f"Error running experiment for {model.name}: {e}")
                # Create empty result for failed model
                model_results[model.value] = ModelExperimentResult(
                    model=model_config.model_id,
                    model_display_name=model_config.display_name,
                    pass_rate=0.0,
                    average_score=0.0,
                    correctness_score=0.0,
                    robustness_score=0.0,
                    safety_score=0.0,
                    hallucination_score=0.0,
                    total_cost_usd=0.0,
                    average_latency_ms=0.0,
                    task_results=[],
                    duration_seconds=0.0,
                )

        # Analyze comparison
        analysis = self._analyze_comparison(model_results)

        # Build result
        result = MultiModelComparisonResult(
            experiment_id=self.experiment_id,
            timestamp=datetime.now().isoformat(),
            model_results=model_results,
            best_model_by_score=analysis["best_by_score"],
            best_model_by_cost_efficiency=analysis["best_by_cost_efficiency"],
            score_ranking=analysis["score_ranking"],
            cost_efficiency_ranking=analysis["cost_efficiency_ranking"],
            config=self.base_config.to_dict(),
        )

        # Save results
        self._save_results(output_path, result)

        if self.base_config.verbose:
            self._print_comparison_summary(result)

        return result

    def _analyze_comparison(
        self,
        model_results: Dict[str, ModelExperimentResult]
    ) -> Dict[str, Any]:
        """
        Analyze and rank model results.

        Args:
            model_results: Dictionary of model results

        Returns:
            Analysis with rankings
        """
        # Rank by average score
        score_ranking = sorted(
            model_results.keys(),
            key=lambda m: model_results[m].average_score,
            reverse=True
        )

        # Compute cost efficiency (score per dollar)
        cost_efficiency = {}
        for model_id, result in model_results.items():
            if result.total_cost_usd > 0:
                cost_efficiency[model_id] = result.average_score / result.total_cost_usd
            else:
                cost_efficiency[model_id] = 0.0

        cost_efficiency_ranking = sorted(
            model_results.keys(),
            key=lambda m: cost_efficiency[m],
            reverse=True
        )

        return {
            "best_by_score": score_ranking[0] if score_ranking else "",
            "best_by_cost_efficiency": cost_efficiency_ranking[0] if cost_efficiency_ranking else "",
            "score_ranking": score_ranking,
            "cost_efficiency_ranking": cost_efficiency_ranking,
            "cost_efficiency_scores": cost_efficiency,
        }

    def _save_results(
        self,
        output_path: str,
        result: MultiModelComparisonResult
    ):
        """Save comparison results."""
        # Save full results
        results_path = os.path.join(output_path, "results.json")
        with open(results_path, 'w') as f:
            json.dump(result.to_dict(), f, indent=2, cls=ExperimentJSONEncoder)

        # Save summary
        summary = {
            "experiment_id": result.experiment_id,
            "timestamp": result.timestamp,
            "models_compared": list(result.model_results.keys()),
            "best_model_by_score": result.best_model_by_score,
            "best_model_by_cost_efficiency": result.best_model_by_cost_efficiency,
            "score_ranking": result.score_ranking,
            "cost_efficiency_ranking": result.cost_efficiency_ranking,
            "model_summaries": {
                k: {
                    "display_name": v.model_display_name,
                    "pass_rate": v.pass_rate,
                    "average_score": v.average_score,
                    "total_cost_usd": v.total_cost_usd,
                }
                for k, v in result.model_results.items()
            }
        }
        summary_path = os.path.join(output_path, "summary.json")
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

        # Save config
        config_path = os.path.join(output_path, "config.json")
        config_data = {
            "experiment_id": result.experiment_id,
            "timestamp": result.timestamp,
            "models": [m.value for m in self.models],
            "base_config": self.base_config.to_dict(),
            "git_commit": ExperimentConfig.get_git_commit(),
            "environment": ExperimentConfig.get_environment_info(),
        }
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)

        if self.base_config.verbose:
            print(f"\nResults saved to: {output_path}")

    def _print_comparison_summary(self, result: MultiModelComparisonResult):
        """Print comparison summary."""
        print("\n" + "=" * 70)
        print("MULTI-MODEL COMPARISON SUMMARY")
        print("=" * 70)
        print(f"Experiment ID: {result.experiment_id}")
        print(f"Models Compared: {len(result.model_results)}")
        print("-" * 70)

        # Table header
        print(f"{'Model':<25} {'Pass Rate':>10} {'Avg Score':>10} {'Cost':>10} {'Duration':>12}")
        print("-" * 70)

        # Table rows
        for model_id in result.score_ranking:
            mr = result.model_results[model_id]
            print(f"{mr.model_display_name:<25} "
                  f"{mr.pass_rate*100:>9.1f}% "
                  f"{mr.average_score:>10.3f} "
                  f"${mr.total_cost_usd:>8.4f} "
                  f"{mr.duration_seconds:>10.1f}s")

        print("-" * 70)
        print("\nRankings:")
        print(f"  Best by Score: {result.best_model_by_score}")
        print(f"  Best by Cost Efficiency: {result.best_model_by_cost_efficiency}")

        print("\nScore Ranking:")
        for i, model_id in enumerate(result.score_ranking, 1):
            mr = result.model_results[model_id]
            print(f"  {i}. {mr.model_display_name} ({mr.average_score:.3f})")

        print("\nCost Efficiency Ranking:")
        for i, model_id in enumerate(result.cost_efficiency_ranking, 1):
            mr = result.model_results[model_id]
            efficiency = mr.average_score / mr.total_cost_usd if mr.total_cost_usd > 0 else 0
            print(f"  {i}. {mr.model_display_name} ({efficiency:.2f} score/$)")

        total_cost = sum(mr.total_cost_usd for mr in result.model_results.values())
        total_duration = sum(mr.duration_seconds for mr in result.model_results.values())
        print("-" * 70)
        print(f"Total Cost: ${total_cost:.4f}")
        print(f"Total Duration: {total_duration:.1f}s ({total_duration/60:.1f} min)")
        print("=" * 70)
