#!/usr/bin/env python3
"""
CLI entry point for running Pass@K evaluation experiments.

Pass@K measures the probability that at least one of k generated
samples passes all test cases.

Usage:
    python -m experiments.run_pass_at_k
    python -m experiments.run_pass_at_k --num-samples 5 --max-tasks 5
    python -m experiments.run_pass_at_k --k-values 1 5 10 --model claude-3-5-haiku-20241022
"""

import argparse
import asyncio
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.config import ExperimentConfig, PassAtKConfig
from experiments.runner import ExperimentRunner
from experiments.models import (
    estimate_experiment_cost, format_cost_estimate, MODEL_ALIASES
)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Pass@K code generation evaluation experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run pass@k with default settings (10 samples)
    python -m experiments.run_pass_at_k

    # Quick test with fewer samples
    python -m experiments.run_pass_at_k --num-samples 3 --max-tasks 2

    # Use Haiku for cost-effective testing
    python -m experiments.run_pass_at_k --model claude-3-5-haiku-20241022 --num-samples 5

    # Custom k values
    python -m experiments.run_pass_at_k --k-values 1 3 5 10

    # Estimate cost only
    python -m experiments.run_pass_at_k --estimate-only
        """
    )

    parser.add_argument(
        "--dataset", "-d",
        default="data/evaluation/benchmark_dataset.json",
        help="Path to benchmark dataset JSON file"
    )

    parser.add_argument(
        "--output", "-o",
        default="experiments/results",
        help="Output directory for results"
    )

    parser.add_argument(
        "--name", "-n",
        default=None,
        help="Experiment name (auto-generated if not provided)"
    )

    parser.add_argument(
        "--model",
        default="claude-sonnet-4-20250514",
        help="Model to use for code generation"
    )

    parser.add_argument(
        "--num-samples",
        type=int,
        default=10,
        help="Number of samples to generate per task (default: 10)"
    )

    parser.add_argument(
        "--k-values",
        type=int,
        nargs="+",
        default=[1, 5, 10],
        help="K values to compute pass@k for (default: 1 5 10)"
    )

    parser.add_argument(
        "--temperatures",
        type=float,
        nargs="+",
        default=[0.2, 0.4, 0.6, 0.8],
        help="Temperatures for diverse generation (default: 0.2 0.4 0.6 0.8)"
    )

    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=3,
        help="Maximum concurrent API calls (default: 3)"
    )

    parser.add_argument(
        "--max-tasks", "-m",
        type=int,
        default=None,
        help="Maximum number of tasks to run (for testing)"
    )

    parser.add_argument(
        "--categories", "-c",
        nargs="+",
        default=None,
        help="Filter tasks by category"
    )

    parser.add_argument(
        "--difficulties",
        nargs="+",
        default=None,
        help="Filter tasks by difficulty"
    )

    parser.add_argument(
        "--estimate-only",
        action="store_true",
        help="Only show cost estimate, don't run experiment"
    )

    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress verbose output"
    )

    return parser.parse_args()


def count_tasks(dataset_path: str, categories=None, difficulties=None, max_tasks=None) -> int:
    """Count tasks in dataset after applying filters."""
    import json
    with open(dataset_path, 'r') as f:
        data = json.load(f)

    tasks = data.get("tasks", [])

    if categories:
        tasks = [t for t in tasks if t.get("category") in categories]

    if difficulties:
        tasks = [t for t in tasks if t.get("difficulty") in difficulties]

    if max_tasks:
        tasks = tasks[:max_tasks]

    return len(tasks)


def main():
    """Main entry point."""
    args = parse_args()

    # Check dataset exists
    if not os.path.exists(args.dataset):
        print(f"Error: Dataset not found: {args.dataset}")
        sys.exit(1)

    # Count tasks
    num_tasks = count_tasks(
        args.dataset,
        args.categories,
        args.difficulties,
        args.max_tasks
    )

    if num_tasks == 0:
        print("Error: No tasks match the specified filters")
        sys.exit(1)

    # Show cost estimate
    model_enum = None
    for alias, model in MODEL_ALIASES.items():
        if model.value == args.model or alias == args.model.lower():
            model_enum = model
            break

    if model_enum:
        estimate = estimate_experiment_cost(
            model_enum,
            num_tasks,
            samples_per_task=args.num_samples
        )
        print("\n" + format_cost_estimate(estimate))
        print()
    else:
        print(f"Note: Cost estimation not available for model {args.model}")

    if args.estimate_only:
        print("Estimate only mode - not running experiment")
        sys.exit(0)

    # Check API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Please set it with: export ANTHROPIC_API_KEY=your_key")
        sys.exit(1)

    # Create pass@k config
    pass_at_k_config = PassAtKConfig(
        num_samples=args.num_samples,
        k_values=args.k_values,
        temperatures=args.temperatures,
        max_concurrent=args.max_concurrent,
    )

    # Create experiment config
    experiment_name = args.name or f"pass_at_k_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    config = ExperimentConfig(
        dataset_path=args.dataset,
        output_dir=args.output,
        experiment_name=experiment_name,
        model=args.model,
        save_checkpoints=True,
        verbose=not args.quiet,
        max_tasks=args.max_tasks,
        categories=args.categories,
        difficulties=args.difficulties,
        pass_at_k_config=pass_at_k_config,
    )

    # Run experiment
    try:
        runner = ExperimentRunner(config)
        asyncio.run(runner.run_pass_at_k_experiment())

        # Print output location
        if not args.quiet:
            print("\nExperiment complete!")
            print(f"Results saved to: {config.get_output_path()}")
            print("\nTo analyze results:")
            print(f"  python -m experiments.analyze {config.get_output_path()}/pass_at_k_results.json")

    except KeyboardInterrupt:
        print("\n\nExperiment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError running experiment: {e}")
        raise


if __name__ == "__main__":
    main()
