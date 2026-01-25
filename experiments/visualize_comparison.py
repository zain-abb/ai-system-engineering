#!/usr/bin/env python3
"""
Visualization module for multi-model comparison experiments.

Generates comparison charts and plots from multi-model experiment results.

Usage:
    python -m experiments.visualize_comparison experiments/results/multi_model/comparison_*/results.json
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not installed. Run: pip install matplotlib")

try:
    import seaborn as sns
    HAS_SEABORN = True
except (ImportError, AttributeError):
    # AttributeError can occur with incompatible seaborn/matplotlib versions
    HAS_SEABORN = False


# Color scheme for models
MODEL_COLORS = {
    "claude-opus-4-20250514": "#9b59b6",      # Purple
    "claude-sonnet-4-20250514": "#3498db",    # Blue
    "claude-3-5-haiku-20241022": "#2ecc71",   # Green
}

# Display names
MODEL_DISPLAY_NAMES = {
    "claude-opus-4-20250514": "Opus 4",
    "claude-sonnet-4-20250514": "Sonnet 4",
    "claude-3-5-haiku-20241022": "Haiku 3.5",
}


class ComparisonVisualizer:
    """
    Visualizer for multi-model comparison results.

    Generates comparison charts following existing visualize.py patterns.
    """

    def __init__(self, results_path: str, output_dir: Optional[str] = None):
        """
        Initialize visualizer.

        Args:
            results_path: Path to results.json from multi-model experiment
            output_dir: Output directory for plots (default: same as results)
        """
        if not HAS_MATPLOTLIB:
            raise ImportError("matplotlib is required for visualization")

        self.results_path = results_path
        self.data = self._load_results(results_path)

        if output_dir:
            self.output_dir = output_dir
        else:
            self.output_dir = os.path.dirname(results_path)

        os.makedirs(self.output_dir, exist_ok=True)

        # Set style
        if HAS_SEABORN:
            sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['font.size'] = 11

    def _load_results(self, path: str) -> Dict:
        """Load results from JSON file."""
        with open(path, 'r') as f:
            return json.load(f)

    def _get_model_color(self, model_id: str) -> str:
        """Get color for a model."""
        return MODEL_COLORS.get(model_id, "#95a5a6")

    def _get_model_name(self, model_id: str) -> str:
        """Get display name for a model."""
        return MODEL_DISPLAY_NAMES.get(model_id, model_id.split("-")[1].title())

    def plot_model_comparison(self) -> str:
        """
        Create 2x2 subplot figure with comprehensive comparison.

        Returns:
            Path to saved plot
        """
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        model_results = self.data.get("model_results", {})
        models = list(model_results.keys())
        n_models = len(models)

        if n_models == 0:
            print("No model results to visualize")
            return ""

        # Extract data
        names = [self._get_model_name(m) for m in models]
        colors = [self._get_model_color(m) for m in models]
        scores = [model_results[m].get("average_score", 0) for m in models]
        costs = [model_results[m].get("total_cost_usd", 0) for m in models]

        # 1. Overall score comparison (bar chart)
        ax1 = axes[0, 0]
        bars1 = ax1.bar(names, scores, color=colors, alpha=0.8, edgecolor='black')
        ax1.set_ylabel("Average Score")
        ax1.set_title("Overall Score Comparison")
        ax1.set_ylim(0, 1.05)
        ax1.axhline(y=0.7, color='gray', linestyle='--', alpha=0.5, label='Threshold')

        for bar, val in zip(bars1, scores):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                    f'{val:.3f}', ha='center', va='bottom', fontsize=10)

        # 2. Per-evaluator comparison (grouped bars)
        ax2 = axes[0, 1]
        evaluators = ["correctness", "robustness", "safety", "hallucination"]
        evaluator_labels = [e.capitalize() for e in evaluators]
        x = np.arange(len(evaluators))
        width = 0.8 / n_models

        for i, model_id in enumerate(models):
            mr = model_results[model_id]
            eval_scores = [
                mr.get("correctness_score", 0),
                mr.get("robustness_score", 0),
                mr.get("safety_score", 0),
                mr.get("hallucination_score", 0),
            ]
            offset = (i - n_models/2 + 0.5) * width
            ax2.bar(x + offset, eval_scores, width, label=self._get_model_name(model_id),
                   color=self._get_model_color(model_id), alpha=0.8)

        ax2.set_ylabel("Score")
        ax2.set_title("Per-Evaluator Comparison")
        ax2.set_xticks(x)
        ax2.set_xticklabels(evaluator_labels)
        ax2.legend()
        ax2.set_ylim(0, 1.05)

        # 3. Cost vs Performance scatter
        ax3 = axes[1, 0]
        for i, model_id in enumerate(models):
            ax3.scatter(costs[i], scores[i], c=colors[i], s=200,
                       label=names[i], edgecolors='black', linewidths=2)

        ax3.set_xlabel("Cost (USD)")
        ax3.set_ylabel("Average Score")
        ax3.set_title("Cost vs Performance")
        ax3.legend()

        # Add efficiency lines (score per dollar)
        if max(costs) > 0:
            max_cost = max(costs) * 1.2
            for efficiency in [0.5, 1.0, 2.0, 5.0]:
                x_line = np.linspace(0, max_cost, 100)
                y_line = x_line * efficiency
                y_line = np.clip(y_line, 0, 1)
                ax3.plot(x_line, y_line, '--', alpha=0.3, color='gray')

        # 4. Pass rate and latency comparison (grouped bars)
        ax4 = axes[1, 1]
        x = np.arange(2)
        width = 0.8 / n_models

        # Normalize latency for comparison (show as bar heights)
        latencies = [model_results[m].get("average_latency_ms", 0) / 1000 for m in models]  # Convert to seconds
        max_latency = max(latencies) if latencies else 1

        for i, model_id in enumerate(models):
            mr = model_results[model_id]
            values = [
                mr.get("pass_rate", 0) * 100,
                (mr.get("average_latency_ms", 0) / 1000) / max_latency * 100 if max_latency > 0 else 0
            ]
            offset = (i - n_models/2 + 0.5) * width
            ax4.bar(x + offset, values, width, label=self._get_model_name(model_id),
                   color=self._get_model_color(model_id), alpha=0.8)

        ax4.set_ylabel("Value")
        ax4.set_title("Pass Rate & Latency Comparison")
        ax4.set_xticks(x)
        ax4.set_xticklabels(["Pass Rate (%)", f"Latency (rel, max={max_latency:.1f}s)"])
        ax4.legend()

        plt.tight_layout()

        output_path = os.path.join(self.output_dir, "comparison_plots.png")
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        return output_path

    def plot_cost_efficiency_analysis(self) -> str:
        """
        Create cost efficiency analysis plot (score per dollar).

        Returns:
            Path to saved plot
        """
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        model_results = self.data.get("model_results", {})
        models = list(model_results.keys())

        if not models:
            return ""

        names = [self._get_model_name(m) for m in models]
        colors = [self._get_model_color(m) for m in models]
        scores = [model_results[m].get("average_score", 0) for m in models]
        costs = [model_results[m].get("total_cost_usd", 0) for m in models]

        # Cost efficiency (score per dollar)
        efficiencies = [s / c if c > 0 else 0 for s, c in zip(scores, costs)]

        # 1. Cost efficiency bar chart
        ax1 = axes[0]
        bars = ax1.bar(names, efficiencies, color=colors, alpha=0.8, edgecolor='black')
        ax1.set_ylabel("Score per Dollar")
        ax1.set_title("Cost Efficiency (Score / Cost)")

        for bar, val in zip(bars, efficiencies):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                    f'{val:.2f}', ha='center', va='bottom', fontsize=10)

        # 2. Cost breakdown (stacked bar showing what you get for your money)
        ax2 = axes[1]
        x = np.arange(len(models))
        bar_width = 0.6

        # Show cost as bar height, with score indicated by color intensity
        for i, (model_id, name, color, cost, score) in enumerate(zip(models, names, colors, costs, scores)):
            ax2.bar(i, cost, bar_width, color=color, alpha=0.3 + 0.7 * score, edgecolor='black')
            ax2.text(i, cost + 0.01, f'${cost:.4f}\n({score:.3f})', ha='center', va='bottom', fontsize=9)

        ax2.set_ylabel("Cost (USD)")
        ax2.set_title("Cost with Score Intensity")
        ax2.set_xticks(x)
        ax2.set_xticklabels(names)

        plt.tight_layout()

        output_path = os.path.join(self.output_dir, "cost_efficiency.png")
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        return output_path

    def generate_comparison_table(self) -> str:
        """
        Generate markdown table for reports.

        Returns:
            Markdown table string
        """
        model_results = self.data.get("model_results", {})

        if not model_results:
            return "No results to display"

        # Header
        lines = [
            "| Model | Pass Rate | Avg Score | Correctness | Robustness | Safety | Halluc. | Cost | Efficiency |",
            "|-------|-----------|-----------|-------------|------------|--------|---------|------|------------|"
        ]

        # Rows
        for model_id, mr in model_results.items():
            name = self._get_model_name(model_id)
            pass_rate = mr.get("pass_rate", 0) * 100
            avg_score = mr.get("average_score", 0)
            correctness = mr.get("correctness_score", 0)
            robustness = mr.get("robustness_score", 0)
            safety = mr.get("safety_score", 0)
            hallucination = mr.get("hallucination_score", 0)
            cost = mr.get("total_cost_usd", 0)
            efficiency = avg_score / cost if cost > 0 else 0

            lines.append(
                f"| {name} | {pass_rate:.1f}% | {avg_score:.3f} | {correctness:.3f} | "
                f"{robustness:.3f} | {safety:.3f} | {hallucination:.3f} | "
                f"${cost:.4f} | {efficiency:.2f} |"
            )

        table = "\n".join(lines)

        # Save to file
        table_path = os.path.join(self.output_dir, "comparison_table.md")
        with open(table_path, 'w') as f:
            f.write("# Multi-Model Comparison Results\n\n")
            f.write(table)
            f.write("\n\n")
            f.write("**Best by Score:** " + self.data.get("best_model_by_score", "N/A") + "\n")
            f.write("**Best by Cost Efficiency:** " + self.data.get("best_model_by_cost_efficiency", "N/A") + "\n")

        return table

    def generate_all_plots(self) -> List[str]:
        """
        Generate all visualization plots.

        Returns:
            List of paths to generated plots
        """
        plots = []

        print("Generating comparison visualizations...")

        print("  - Model comparison (2x2 subplot)...")
        plot = self.plot_model_comparison()
        if plot:
            plots.append(plot)

        print("  - Cost efficiency analysis...")
        plot = self.plot_cost_efficiency_analysis()
        if plot:
            plots.append(plot)

        print("  - Comparison table (markdown)...")
        self.generate_comparison_table()

        print(f"\nAll outputs saved to: {self.output_dir}")

        return plots


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate visualizations from multi-model comparison results"
    )
    parser.add_argument(
        "results_file",
        help="Path to results.json from multi-model experiment"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output directory for plots"
    )

    args = parser.parse_args()

    if not HAS_MATPLOTLIB:
        print("Error: matplotlib is required for visualization")
        print("Install with: pip install matplotlib seaborn")
        sys.exit(1)

    if not os.path.exists(args.results_file):
        print(f"Error: Results file not found: {args.results_file}")
        sys.exit(1)

    visualizer = ComparisonVisualizer(args.results_file, args.output)
    plots = visualizer.generate_all_plots()

    print(f"\nGenerated {len(plots)} plots:")
    for plot in plots:
        print(f"  - {os.path.basename(plot)}")


if __name__ == "__main__":
    main()
