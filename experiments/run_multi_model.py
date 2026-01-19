#!/usr/bin/env python3
"""
CLI entry point for running multi-model comparison experiments.

Runs identical benchmarks across Claude Opus 4, Sonnet 4, and Haiku 3.5
with comparative analysis of performance, cost, and quality.

Usage:
    python -m experiments.run_multi_model --estimate-only
    python -m experiments.run_multi_model --models haiku sonnet
    python -m experiments.run_multi_model --models haiku sonnet opus --max-tasks 10
"""

import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.config import ExperimentConfig
from experiments.multi_model_runner import MultiModelExperimentRunner
from experiments.models import (
    MODEL_ALIASES, estimate_multi_model_cost, format_multi_model_estimate
)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run multi-model comparison experiments across Claude models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Show cost estimate only
    python -m experiments.run_multi_model --estimate-only

    # Compare Haiku and Sonnet (cost-effective)
    python -m experiments.run_multi_model --models haiku sonnet

    # Quick test with limited tasks
    python -m experiments.run_multi_model --models haiku --max-tasks 3

    # Full comparison (all models)
    python -m experiments.run_multi_model --models haiku sonnet opus

    # Filter by category
    python -m experiments.run_multi_model --models haiku sonnet --categories algorithms
        """
    )

    parser.add_argument(
        "--dataset", "-d",
        default="data/evaluation/benchmark_dataset.json",
        help="Path to benchmark dataset JSON file"
    )

    parser.add_argument(
        "--output", "-o",
        default="experiments/results/multi_model",
        help="Output directory for results"
    )

    parser.add_argument(
        "--models", "-m",
        nargs="+",
        choices=["haiku", "sonnet", "opus"],
        default=["haiku", "sonnet"],
        help="Models to compare (default: haiku sonnet)"
    )

    parser.add_argument(
        "--max-tasks",
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
        "--temperature", "-t",
        type=float,
        default=0.7,
        help="Temperature for code generation (default: 0.7)"
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

    # Parse models
    models = [MODEL_ALIASES[m] for m in args.models]

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
    estimate = estimate_multi_model_cost(models, num_tasks)
    print("\n" + format_multi_model_estimate(estimate))

    if args.estimate_only:
        print("\nEstimate only mode - not running experiment")
        sys.exit(0)

    # Confirm before running expensive experiments
    total_cost = estimate["total_cost_usd"]
    if total_cost > 1.0:
        print(f"\nWarning: Estimated cost is ${total_cost:.2f}")
        response = input("Continue? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)

    # Check API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Please set it with: export ANTHROPIC_API_KEY=your_key")
        sys.exit(1)

    # Create base config
    base_config = ExperimentConfig(
        dataset_path=args.dataset,
        temperature=args.temperature,
        save_checkpoints=True,
        verbose=not args.quiet,
        max_tasks=args.max_tasks,
        categories=args.categories,
        difficulties=args.difficulties,
    )

    # Create and run multi-model experiment
    try:
        runner = MultiModelExperimentRunner(
            models=models,
            output_dir=args.output,
            base_config=base_config
        )
        runner.run_comparison()

        # Print output location
        if not args.quiet:
            output_path = os.path.join(args.output, runner.experiment_id)
            print("\nExperiment complete!")
            print(f"Results saved to: {output_path}")
            print("\nTo visualize results:")
            print(f"  python -m experiments.visualize_comparison {output_path}/results.json")

    except KeyboardInterrupt:
        print("\n\nExperiment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError running experiment: {e}")
        raise


if __name__ == "__main__":
    main()
