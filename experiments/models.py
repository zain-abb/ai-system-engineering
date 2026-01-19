"""
Model configuration for multi-model experiments.

Centralized configuration for Claude models including pricing,
rate limits, and expected performance characteristics.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class ClaudeModel(Enum):
    """Available Claude models for experiments."""
    OPUS_4 = "claude-opus-4-20250514"
    SONNET_4 = "claude-sonnet-4-20250514"
    HAIKU_3_5 = "claude-3-5-haiku-20241022"


# Short names for CLI convenience
MODEL_ALIASES = {
    "opus": ClaudeModel.OPUS_4,
    "sonnet": ClaudeModel.SONNET_4,
    "haiku": ClaudeModel.HAIKU_3_5,
}


@dataclass
class ModelConfig:
    """Configuration for a specific Claude model."""
    model_id: str
    display_name: str
    input_cost: float      # Per 1M tokens
    output_cost: float     # Per 1M tokens
    max_tokens: int = 4096
    rate_limit_rpm: int = 50
    expected_latency_ms: int = 2000

    @property
    def input_cost_per_1k(self) -> float:
        """Cost per 1K input tokens."""
        return self.input_cost / 1000

    @property
    def output_cost_per_1k(self) -> float:
        """Cost per 1K output tokens."""
        return self.output_cost / 1000


# Model configurations with current pricing (per 1M tokens)
MODEL_CONFIGS: Dict[ClaudeModel, ModelConfig] = {
    ClaudeModel.OPUS_4: ModelConfig(
        model_id="claude-opus-4-20250514",
        display_name="Claude Opus 4",
        input_cost=15.00,    # $15.00 per 1M input tokens
        output_cost=75.00,   # $75.00 per 1M output tokens
        max_tokens=4096,
        rate_limit_rpm=30,   # Conservative for expensive model
        expected_latency_ms=4000,
    ),
    ClaudeModel.SONNET_4: ModelConfig(
        model_id="claude-sonnet-4-20250514",
        display_name="Claude Sonnet 4",
        input_cost=3.00,     # $3.00 per 1M input tokens
        output_cost=15.00,   # $15.00 per 1M output tokens
        max_tokens=4096,
        rate_limit_rpm=50,
        expected_latency_ms=2000,
    ),
    ClaudeModel.HAIKU_3_5: ModelConfig(
        model_id="claude-3-5-haiku-20241022",
        display_name="Claude 3.5 Haiku",
        input_cost=0.80,     # $0.80 per 1M input tokens
        output_cost=4.00,    # $4.00 per 1M output tokens
        max_tokens=4096,
        rate_limit_rpm=100,  # Higher rate limit for faster model
        expected_latency_ms=500,
    ),
}


def get_model_config(model: ClaudeModel) -> ModelConfig:
    """
    Get configuration for a specific model.

    Args:
        model: The Claude model enum

    Returns:
        ModelConfig for the specified model
    """
    return MODEL_CONFIGS[model]


def get_model_by_id(model_id: str) -> Optional[ClaudeModel]:
    """
    Get ClaudeModel enum from model ID string.

    Args:
        model_id: The model ID string (e.g., "claude-sonnet-4-20250514")

    Returns:
        ClaudeModel enum or None if not found
    """
    for model, config in MODEL_CONFIGS.items():
        if config.model_id == model_id:
            return model
    return None


def get_model_from_alias(alias: str) -> Optional[ClaudeModel]:
    """
    Get ClaudeModel from short alias.

    Args:
        alias: Short name like "opus", "sonnet", "haiku"

    Returns:
        ClaudeModel enum or None if not found
    """
    return MODEL_ALIASES.get(alias.lower())


def estimate_experiment_cost(
    model: ClaudeModel,
    num_tasks: int,
    samples_per_task: int = 1,
    avg_input_tokens: int = 1500,
    avg_output_tokens: int = 800
) -> Dict[str, float]:
    """
    Estimate API cost for an experiment.

    Args:
        model: The Claude model to use
        num_tasks: Number of tasks to evaluate
        samples_per_task: Number of samples per task (for pass@k)
        avg_input_tokens: Average input tokens per request
        avg_output_tokens: Average output tokens per request

    Returns:
        Dictionary with cost breakdown
    """
    config = get_model_config(model)
    total_requests = num_tasks * samples_per_task

    total_input_tokens = total_requests * avg_input_tokens
    total_output_tokens = total_requests * avg_output_tokens

    input_cost = (total_input_tokens / 1_000_000) * config.input_cost
    output_cost = (total_output_tokens / 1_000_000) * config.output_cost
    total_cost = input_cost + output_cost

    return {
        "model": config.display_name,
        "model_id": config.model_id,
        "num_tasks": num_tasks,
        "samples_per_task": samples_per_task,
        "total_requests": total_requests,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "input_cost_usd": round(input_cost, 4),
        "output_cost_usd": round(output_cost, 4),
        "total_cost_usd": round(total_cost, 4),
        "estimated_time_minutes": round(
            total_requests * config.expected_latency_ms / 60000, 1
        ),
    }


def estimate_multi_model_cost(
    models: list,
    num_tasks: int,
    samples_per_task: int = 1,
    avg_input_tokens: int = 1500,
    avg_output_tokens: int = 800
) -> Dict[str, any]:
    """
    Estimate total cost for multi-model comparison.

    Args:
        models: List of ClaudeModel enums
        num_tasks: Number of tasks to evaluate
        samples_per_task: Number of samples per task
        avg_input_tokens: Average input tokens per request
        avg_output_tokens: Average output tokens per request

    Returns:
        Dictionary with per-model and total costs
    """
    per_model_costs = {}
    total_cost = 0.0
    total_time = 0.0

    for model in models:
        estimate = estimate_experiment_cost(
            model, num_tasks, samples_per_task,
            avg_input_tokens, avg_output_tokens
        )
        per_model_costs[model.value] = estimate
        total_cost += estimate["total_cost_usd"]
        total_time += estimate["estimated_time_minutes"]

    return {
        "per_model": per_model_costs,
        "total_cost_usd": round(total_cost, 4),
        "total_time_minutes": round(total_time, 1),
        "num_models": len(models),
        "num_tasks": num_tasks,
        "samples_per_task": samples_per_task,
    }


def format_cost_estimate(estimate: Dict) -> str:
    """
    Format cost estimate for display.

    Args:
        estimate: Cost estimate dictionary from estimate_experiment_cost

    Returns:
        Formatted string for display
    """
    lines = [
        f"Cost Estimate for {estimate['model']}:",
        f"  Tasks: {estimate['num_tasks']} x {estimate['samples_per_task']} samples = {estimate['total_requests']} requests",
        f"  Input tokens: ~{estimate['total_input_tokens']:,} (${estimate['input_cost_usd']:.4f})",
        f"  Output tokens: ~{estimate['total_output_tokens']:,} (${estimate['output_cost_usd']:.4f})",
        f"  Total cost: ${estimate['total_cost_usd']:.4f}",
        f"  Estimated time: ~{estimate['estimated_time_minutes']:.1f} minutes",
    ]
    return "\n".join(lines)


def format_multi_model_estimate(estimate: Dict) -> str:
    """
    Format multi-model cost estimate for display.

    Args:
        estimate: Cost estimate from estimate_multi_model_cost

    Returns:
        Formatted string for display
    """
    lines = [
        "=" * 60,
        "Multi-Model Experiment Cost Estimate",
        "=" * 60,
        f"Tasks: {estimate['num_tasks']} x {estimate['samples_per_task']} samples",
        f"Models: {estimate['num_models']}",
        "",
        "Per-Model Breakdown:",
        "-" * 40,
    ]

    for model_id, cost_info in estimate["per_model"].items():
        lines.extend([
            f"  {cost_info['model']}:",
            f"    Cost: ${cost_info['total_cost_usd']:.4f}",
            f"    Time: ~{cost_info['estimated_time_minutes']:.1f} min",
        ])

    lines.extend([
        "",
        "-" * 40,
        f"TOTAL COST: ${estimate['total_cost_usd']:.4f}",
        f"TOTAL TIME: ~{estimate['total_time_minutes']:.1f} minutes",
        "=" * 60,
    ])

    return "\n".join(lines)
