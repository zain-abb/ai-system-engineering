#!/usr/bin/env python3
"""
CLI entry point for running SE-Agent evaluation experiments.

Usage:
    python -m experiments.run_experiment --dataset data/evaluation/benchmark_dataset.json
    python -m experiments.run_experiment --max-tasks 5  # Quick test run
    python -m experiments.run_experiment --categories algorithms data_structures
"""

import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.config import ExperimentConfig
from experiments.runner import ExperimentRunner


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run SE-Agent code generation evaluation experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run full experiment
    python -m experiments.run_experiment

    # Quick test with 5 tasks
    python -m experiments.run_experiment --max-tasks 5

    # Filter by category
    python -m experiments.run_experiment --categories algorithms

    # Filter by difficulty
    python -m experiments.run_experiment --difficulties easy medium

    # Custom output directory
    python -m experiments.run_experiment --output experiments/my_results
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
        "--max-tasks", "-m",
        type=int,
        default=None,
        help="Maximum number of tasks to run (for testing)"
    )

    parser.add_argument(
        "--categories", "-c",
        nargs="+",
        default=None,
        help="Filter tasks by category (e.g., algorithms data_structures)"
    )

    parser.add_argument(
        "--difficulties",
        nargs="+",
        default=None,
        help="Filter tasks by difficulty (e.g., easy medium hard)"
    )

    parser.add_argument(
        "--model",
        default="claude-sonnet-4-20250514",
        help="Model to use for code generation"
    )

    parser.add_argument(
        "--temperature", "-t",
        type=float,
        default=0.7,
        help="Temperature for code generation (0.0-1.0)"
    )

    parser.add_argument(
        "--no-checkpoints",
        action="store_true",
        help="Disable checkpoint saving"
    )

    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress verbose output"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Check dataset exists
    if not os.path.exists(args.dataset):
        print(f"Error: Dataset not found: {args.dataset}")
        sys.exit(1)

    # Check API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Please set it with: export ANTHROPIC_API_KEY=your_key")
        sys.exit(1)

    # Create config
    config_kwargs = {
        "dataset_path": args.dataset,
        "output_dir": args.output,
        "model": args.model,
        "temperature": args.temperature,
        "save_checkpoints": not args.no_checkpoints,
        "verbose": not args.quiet,
        "max_tasks": args.max_tasks,
        "categories": args.categories,
        "difficulties": args.difficulties,
    }

    if args.name:
        config_kwargs["experiment_name"] = args.name

    config = ExperimentConfig(**config_kwargs)

    # Run experiment
    try:
        runner = ExperimentRunner(config)
        results = runner.run_experiment()

        # Print output location
        if not args.quiet:
            print(f"\nExperiment complete!")
            print(f"Results saved to: {config.get_output_path()}")
            print(f"\nTo analyze results:")
            print(f"  python -m experiments.analyze {config.get_output_path()}/raw_results.json")
            print(f"\nTo generate visualizations:")
            print(f"  python -m experiments.visualize {config.get_output_path()}/raw_results.json")

    except KeyboardInterrupt:
        print("\n\nExperiment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError running experiment: {e}")
        raise


if __name__ == "__main__":
    main()
