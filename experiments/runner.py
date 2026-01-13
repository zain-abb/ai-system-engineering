"""Experiment runner for SE-Agent evaluation."""

import json
import logging
import os
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field, is_dataclass, asdict
from enum import Enum

from experiments.config import ExperimentConfig

# Import services first to avoid circular imports
from src.services.claude_client import ClaudeClient
from src.evaluation.base import EvaluationTask, Issue, Severity
from src.evaluation.metrics import EvaluationPipeline, EvaluationReport, TaskEvaluationResult

# Import prompts directly to avoid circular import through __init__.py
from src.agent.prompts.code_generation import CODE_GEN_SYSTEM, format_code_gen_prompt


class ExperimentJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for experiment results."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        if is_dataclass(obj) and not isinstance(obj, type):
            return asdict(obj)
        return super().default(obj)

logger = logging.getLogger(__name__)


@dataclass
class ExperimentResults:
    """Container for experiment results."""
    config: ExperimentConfig
    task_results: List[Dict[str, Any]] = field(default_factory=list)
    evaluation_report: Optional[EvaluationReport] = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    api_cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary for serialization."""
        return {
            "config": self.config.to_dict(),
            "git_commit": ExperimentConfig.get_git_commit(),
            "environment": ExperimentConfig.get_environment_info(),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "api_cost": self.api_cost,
            "task_count": len(self.task_results),
            "tasks": self.task_results,
        }


class ExperimentRunner:
    """
    Main experiment runner for evaluating LLM code generation.

    This class orchestrates:
    1. Loading benchmark dataset
    2. Generating code using Claude API
    3. Running evaluation pipeline on generated code
    4. Saving results with checkpoints
    """

    def __init__(self, config: ExperimentConfig):
        """
        Initialize the experiment runner.

        Args:
            config: Experiment configuration
        """
        self.config = config
        self.client = ClaudeClient()
        self.pipeline = EvaluationPipeline(config.eval_config)
        self.results = ExperimentResults(config=config)

    def load_dataset(self, path: Optional[str] = None) -> List[Dict]:
        """
        Load and validate the benchmark dataset.

        Args:
            path: Path to dataset JSON file (uses config if not provided)

        Returns:
            List of task dictionaries
        """
        dataset_path = path or self.config.dataset_path

        with open(dataset_path, 'r') as f:
            data = json.load(f)

        tasks = data.get("tasks", [])
        logger.info(f"Loaded {len(tasks)} tasks from {dataset_path}")

        # Apply filters
        if self.config.categories:
            tasks = [t for t in tasks if t.get("category") in self.config.categories]
            logger.info(f"Filtered to {len(tasks)} tasks by category")

        if self.config.difficulties:
            tasks = [t for t in tasks if t.get("difficulty") in self.config.difficulties]
            logger.info(f"Filtered to {len(tasks)} tasks by difficulty")

        if self.config.max_tasks:
            tasks = tasks[:self.config.max_tasks]
            logger.info(f"Limited to {len(tasks)} tasks")

        return tasks

    def generate_code_for_task(self, task: Dict) -> str:
        """
        Generate code for a single benchmark task.

        Args:
            task: Task dictionary from dataset

        Returns:
            Generated code string
        """
        import re

        # Format the prompt
        user_prompt = format_code_gen_prompt(
            requirements=task["input_text"],
            language=task.get("language", "python"),
            context=None,
            instructions=""
        )

        try:
            # Generate using Claude client directly
            response = self.client.generate(
                prompt=user_prompt,
                system_prompt=CODE_GEN_SYSTEM,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )

            # Extract code from markdown code blocks
            result = response.strip()
            code_block_pattern = r"```(?:\w+)?\n(.*?)```"
            matches = re.findall(code_block_pattern, result, re.DOTALL)

            if matches:
                # Return the largest code block
                return max(matches, key=len).strip()

            return result

        except Exception as e:
            logger.warning(f"Code generation failed for {task['task_id']}: {e}")
            return ""

    def create_evaluation_task(
        self,
        dataset_task: Dict,
        generated_code: str
    ) -> EvaluationTask:
        """
        Create an EvaluationTask from dataset task and generated code.

        Args:
            dataset_task: Original task from dataset
            generated_code: LLM-generated code

        Returns:
            EvaluationTask ready for evaluation
        """
        return EvaluationTask(
            task_id=dataset_task["task_id"],
            input_text=dataset_task["input_text"],
            generated_output=generated_code,
            reference_output=dataset_task.get("reference_output"),
            language=dataset_task.get("language", "python"),
            metadata={
                "test_cases": dataset_task.get("metadata", {}).get("test_cases", []),
                "category": dataset_task.get("category"),
                "difficulty": dataset_task.get("difficulty"),
                "tags": dataset_task.get("metadata", {}).get("tags", []),
            }
        )

    def run_experiment(
        self,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> ExperimentResults:
        """
        Run the full experiment.

        Args:
            progress_callback: Optional callback(current, total, task_id)

        Returns:
            ExperimentResults with all data
        """
        # Create output directory
        output_path = self.config.get_output_path()
        os.makedirs(output_path, exist_ok=True)
        os.makedirs(os.path.join(output_path, "checkpoints"), exist_ok=True)

        # Load dataset
        tasks = self.load_dataset()
        total_tasks = len(tasks)

        if self.config.verbose:
            print(f"\nStarting experiment: {self.config.experiment_name}")
            print(f"Total tasks: {total_tasks}")
            print(f"Output directory: {output_path}\n")

        # Save initial config
        self._save_config(output_path)

        eval_tasks = []
        self.results.start_time = datetime.now()

        # Process each task
        for i, task in enumerate(tasks):
            task_id = task["task_id"]

            if progress_callback:
                progress_callback(i + 1, total_tasks, task_id)
            elif self.config.verbose:
                print(f"[{i+1}/{total_tasks}] Processing: {task_id}")

            # Generate code
            generated_code = self.generate_code_for_task(task)

            # Create evaluation task
            eval_task = self.create_evaluation_task(task, generated_code)
            eval_tasks.append(eval_task)

            # Store task result with generated code
            task_result = {
                "task_id": task_id,
                "category": task.get("category"),
                "difficulty": task.get("difficulty"),
                "input_text": task["input_text"],
                "generated_code": generated_code,
                "reference_code": task.get("reference_output", ""),
            }
            self.results.task_results.append(task_result)

            # Save checkpoint
            if self.config.save_checkpoints and (i + 1) % self.config.checkpoint_interval == 0:
                self._save_checkpoint(output_path, i + 1)

        # Run evaluation pipeline
        if self.config.verbose:
            print("\nRunning evaluation pipeline...")

        def eval_progress(current, total):
            if self.config.verbose:
                print(f"  Evaluating: {current}/{total}", end="\r")

        self.results.evaluation_report = self.pipeline.evaluate_batch(
            eval_tasks,
            progress_callback=eval_progress
        )

        # Merge evaluation results into task results
        for i, task_eval_result in enumerate(self.results.evaluation_report.task_results):
            self.results.task_results[i]["evaluation"] = task_eval_result.to_dict()

        self.results.end_time = datetime.now()
        self.results.api_cost = self.client.get_usage_stats().get("total_cost", 0.0)

        # Save final results
        self._save_results(output_path)

        if self.config.verbose:
            self._print_summary()

        return self.results

    def _save_config(self, output_path: str):
        """Save experiment configuration."""
        config_path = os.path.join(output_path, "config.json")
        config_data = {
            "config": self.config.to_dict(),
            "git_commit": ExperimentConfig.get_git_commit(),
            "environment": ExperimentConfig.get_environment_info(),
            "dataset_hash": self._compute_dataset_hash(),
            "timestamp": datetime.now().isoformat(),
        }
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)

    def _compute_dataset_hash(self) -> str:
        """Compute SHA-256 hash of dataset for reproducibility."""
        try:
            with open(self.config.dataset_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()[:16]
        except Exception:
            return "unknown"

    def _save_checkpoint(self, output_path: str, task_num: int):
        """Save checkpoint of current progress."""
        checkpoint_path = os.path.join(
            output_path,
            "checkpoints",
            f"checkpoint_{task_num}.json"
        )
        checkpoint_data = {
            "tasks_completed": task_num,
            "timestamp": datetime.now().isoformat(),
            "task_results": self.results.task_results,
        }
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2, cls=ExperimentJSONEncoder)

        if self.config.verbose:
            print(f"  Checkpoint saved: {task_num} tasks")

    def _save_results(self, output_path: str):
        """Save final experiment results."""
        # Save raw results
        raw_path = os.path.join(output_path, "raw_results.json")
        with open(raw_path, 'w') as f:
            json.dump(self.results.to_dict(), f, indent=2, cls=ExperimentJSONEncoder)

        # Save evaluation report
        if self.results.evaluation_report:
            report_path = os.path.join(output_path, "evaluation_report.json")
            # Use custom save with encoder
            with open(report_path, 'w') as f:
                json.dump(self.results.evaluation_report.to_dict(), f, indent=2, cls=ExperimentJSONEncoder)

            # Save summary
            summary_path = os.path.join(output_path, "summary.json")
            with open(summary_path, 'w') as f:
                json.dump(self.results.evaluation_report.summary, f, indent=2, cls=ExperimentJSONEncoder)

        if self.config.verbose:
            print(f"\nResults saved to: {output_path}")

    def _print_summary(self):
        """Print experiment summary."""
        if not self.results.evaluation_report:
            return

        summary = self.results.evaluation_report.summary
        duration = (self.results.end_time - self.results.start_time).total_seconds()

        print("\n" + "=" * 60)
        print("EXPERIMENT SUMMARY")
        print("=" * 60)
        print(f"Experiment: {self.config.experiment_name}")
        print(f"Duration: {duration:.1f} seconds")
        print(f"API Cost: ${self.results.api_cost:.4f}")
        print("-" * 60)
        print(f"Total Tasks: {summary['total_tasks']}")
        print(f"Passed: {summary['passed_tasks']} ({summary['pass_rate']*100:.1f}%)")
        print(f"Failed: {summary['failed_tasks']}")
        print(f"Average Score: {summary['average_overall_score']:.3f}")
        print("-" * 60)
        print("Per-Evaluator Results:")

        for eval_type, stats in summary.get("evaluator_stats", {}).items():
            print(f"  {eval_type.upper()}:")
            print(f"    Score: {stats['average_score']:.3f} (min: {stats['min_score']:.3f}, max: {stats['max_score']:.3f})")
            print(f"    Pass Rate: {stats['pass_rate']*100:.1f}%")
            print(f"    Issues: {stats['total_issues']}")

        print("-" * 60)
        if summary.get("top_issue_categories"):
            print("Top Issues:")
            for category, count in list(summary["top_issue_categories"].items())[:5]:
                print(f"  - {category}: {count}")

        print("=" * 60)


def run_quick_experiment(
    dataset_path: str = "data/evaluation/benchmark_dataset.json",
    max_tasks: int = 5,
    output_dir: str = "experiments/results"
) -> ExperimentResults:
    """
    Run a quick experiment with default settings.

    Args:
        dataset_path: Path to dataset
        max_tasks: Maximum number of tasks to run
        output_dir: Output directory

    Returns:
        ExperimentResults
    """
    config = ExperimentConfig(
        dataset_path=dataset_path,
        output_dir=output_dir,
        max_tasks=max_tasks,
        verbose=True
    )
    runner = ExperimentRunner(config)
    return runner.run_experiment()
