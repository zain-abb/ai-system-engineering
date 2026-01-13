"""Experiment configuration dataclass."""

import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

from src.evaluation.metrics import EvaluationConfig


@dataclass
class ExperimentConfig:
    """Configuration for running evaluation experiments."""

    # Dataset settings
    dataset_path: str = "data/evaluation/benchmark_dataset.json"

    # Output settings
    output_dir: str = "experiments/results"
    experiment_name: str = field(default_factory=lambda: f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

    # Model settings
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.7
    max_tokens: int = 2048

    # Evaluation settings
    eval_config: EvaluationConfig = field(default_factory=EvaluationConfig)

    # Experiment settings
    save_checkpoints: bool = True
    checkpoint_interval: int = 5
    verbose: bool = True

    # Filters (optional)
    categories: Optional[list] = None  # Filter by category
    difficulties: Optional[list] = None  # Filter by difficulty
    max_tasks: Optional[int] = None  # Limit number of tasks

    def get_output_path(self) -> str:
        """Get the full output directory path for this experiment."""
        return os.path.join(self.output_dir, self.experiment_name)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return {
            "dataset_path": self.dataset_path,
            "output_dir": self.output_dir,
            "experiment_name": self.experiment_name,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "save_checkpoints": self.save_checkpoints,
            "checkpoint_interval": self.checkpoint_interval,
            "categories": self.categories,
            "difficulties": self.difficulties,
            "max_tasks": self.max_tasks,
            "eval_config": {
                "correctness_threshold": self.eval_config.correctness_threshold,
                "robustness_threshold": self.eval_config.robustness_threshold,
                "safety_threshold": self.eval_config.safety_threshold,
                "hallucination_threshold": self.eval_config.hallucination_threshold,
                "weights": self.eval_config.weights,
            }
        }

    @staticmethod
    def get_git_commit() -> Optional[str]:
        """Get current git commit hash for reproducibility."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()[:8]
        except Exception:
            pass
        return None

    @staticmethod
    def get_environment_info() -> Dict[str, str]:
        """Get environment information for reproducibility."""
        import sys
        import platform

        info = {
            "python_version": sys.version.split()[0],
            "platform": platform.system(),
            "platform_version": platform.release(),
        }

        try:
            import anthropic
            info["anthropic_version"] = anthropic.__version__
        except ImportError:
            info["anthropic_version"] = "not installed"

        return info
