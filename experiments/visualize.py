#!/usr/bin/env python3
"""
Visualization module for SE-Agent evaluation experiments.

Generates charts and plots from experiment results.

Usage:
    python -m experiments.visualize experiments/results/exp_*/raw_results.json
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not installed. Run: pip install matplotlib")

try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False


class ResultsVisualizer:
    """
    Visualizer for experiment results.

    Generates various charts and plots for analysis.
    """

    # Color scheme
    COLORS = {
        "correctness": "#2ecc71",  # Green
        "robustness": "#3498db",   # Blue
        "safety": "#e74c3c",       # Red
        "hallucination": "#9b59b6", # Purple
        "pass": "#27ae60",
        "fail": "#c0392b",
    }

    def __init__(self, results_path: str, output_dir: Optional[str] = None):
        """
        Initialize visualizer.

        Args:
            results_path: Path to raw_results.json
            output_dir: Output directory for plots (default: same as results)
        """
        if not HAS_MATPLOTLIB:
            raise ImportError("matplotlib is required for visualization")

        self.results_path = results_path
        self.data = self._load_results(results_path)
        self.tasks = self.data.get("tasks", [])

        if output_dir:
            self.output_dir = output_dir
        else:
            self.output_dir = os.path.join(
                os.path.dirname(results_path),
                "plots"
            )

        os.makedirs(self.output_dir, exist_ok=True)

        # Set style
        if HAS_SEABORN:
            sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (10, 6)
        plt.rcParams['font.size'] = 11

    def _load_results(self, path: str) -> Dict:
        """Load results from JSON file."""
        with open(path, 'r') as f:
            return json.load(f)

    def _extract_scores(self) -> Dict[str, List[float]]:
        """Extract scores by evaluator type."""
        scores = {
            "correctness": [],
            "robustness": [],
            "safety": [],
            "hallucination": [],
            "overall": []
        }

        for task in self.tasks:
            eval_data = task.get("evaluation", {})
            results = eval_data.get("results", {})

            scores["overall"].append(eval_data.get("overall_score", 0))

            for eval_type in ["correctness", "robustness", "safety", "hallucination"]:
                score = results.get(eval_type, {}).get("score", 0)
                scores[eval_type].append(score)

        return scores

    def plot_score_distribution(self) -> str:
        """
        Create box plot of score distributions by evaluator.

        Returns:
            Path to saved plot
        """
        scores = self._extract_scores()

        fig, ax = plt.subplots(figsize=(12, 6))

        evaluators = ["correctness", "robustness", "safety", "hallucination", "overall"]
        data = [scores[e] for e in evaluators]
        colors = [self.COLORS.get(e, "#95a5a6") for e in evaluators]

        bp = ax.boxplot(data, labels=evaluators, patch_artist=True)

        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

        ax.set_ylabel("Score")
        ax.set_title("Score Distribution by Evaluator")
        ax.set_ylim(0, 1.05)
        ax.axhline(y=0.7, color='gray', linestyle='--', alpha=0.5, label='Threshold (0.7)')
        ax.legend()

        plt.tight_layout()

        output_path = os.path.join(self.output_dir, "score_distribution.png")
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        return output_path

    def plot_pass_rates(self) -> str:
        """
        Create bar chart of pass rates by evaluator.

        Returns:
            Path to saved plot
        """
        pass_rates = {}
        evaluators = ["correctness", "robustness", "safety", "hallucination"]

        for eval_type in evaluators:
            passed = 0
            total = 0
            for task in self.tasks:
                results = task.get("evaluation", {}).get("results", {})
                if eval_type in results:
                    total += 1
                    if results[eval_type].get("passed", False):
                        passed += 1
            pass_rates[eval_type] = (passed / total * 100) if total > 0 else 0

        # Overall pass rate
        overall_passed = sum(1 for t in self.tasks if t.get("evaluation", {}).get("overall_passed", False))
        pass_rates["overall"] = (overall_passed / len(self.tasks) * 100) if self.tasks else 0

        fig, ax = plt.subplots(figsize=(10, 6))

        labels = list(pass_rates.keys())
        values = list(pass_rates.values())
        colors = [self.COLORS.get(l, "#95a5a6") for l in labels]

        bars = ax.bar(labels, values, color=colors, alpha=0.8, edgecolor='black')

        # Add value labels
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                   f'{val:.1f}%', ha='center', va='bottom', fontsize=10)

        ax.set_ylabel("Pass Rate (%)")
        ax.set_title("Pass Rates by Evaluator")
        ax.set_ylim(0, 105)
        ax.axhline(y=70, color='gray', linestyle='--', alpha=0.5)

        plt.tight_layout()

        output_path = os.path.join(self.output_dir, "pass_rates.png")
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        return output_path

    def plot_category_performance(self) -> str:
        """
        Create grouped bar chart of performance by category.

        Returns:
            Path to saved plot
        """
        category_scores = {}

        for task in self.tasks:
            category = task.get("category", "unknown")
            if category not in category_scores:
                category_scores[category] = {e: [] for e in ["correctness", "robustness", "safety", "hallucination"]}

            results = task.get("evaluation", {}).get("results", {})
            for eval_type in category_scores[category]:
                score = results.get(eval_type, {}).get("score", 0)
                category_scores[category][eval_type].append(score)

        # Compute averages
        categories = list(category_scores.keys())
        evaluators = ["correctness", "robustness", "safety", "hallucination"]

        fig, ax = plt.subplots(figsize=(14, 6))

        x = np.arange(len(categories))
        width = 0.2

        for i, eval_type in enumerate(evaluators):
            means = [np.mean(category_scores[c][eval_type]) for c in categories]
            offset = (i - 1.5) * width
            bars = ax.bar(x + offset, means, width, label=eval_type.capitalize(),
                         color=self.COLORS[eval_type], alpha=0.8)

        ax.set_ylabel("Average Score")
        ax.set_title("Performance by Category and Evaluator")
        ax.set_xticks(x)
        ax.set_xticklabels(categories, rotation=45, ha='right')
        ax.legend()
        ax.set_ylim(0, 1.05)

        plt.tight_layout()

        output_path = os.path.join(self.output_dir, "category_performance.png")
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        return output_path

    def plot_difficulty_analysis(self) -> str:
        """
        Create bar chart of performance by difficulty level.

        Returns:
            Path to saved plot
        """
        difficulty_scores = {}

        for task in self.tasks:
            difficulty = task.get("difficulty", "unknown")
            if difficulty not in difficulty_scores:
                difficulty_scores[difficulty] = []

            score = task.get("evaluation", {}).get("overall_score", 0)
            difficulty_scores[difficulty].append(score)

        # Order difficulties
        ordered = ["easy", "medium", "hard"]
        difficulties = [d for d in ordered if d in difficulty_scores]

        fig, ax = plt.subplots(figsize=(8, 6))

        means = [np.mean(difficulty_scores[d]) for d in difficulties]
        stds = [np.std(difficulty_scores[d]) for d in difficulties]

        colors = ["#27ae60", "#f39c12", "#e74c3c"][:len(difficulties)]

        bars = ax.bar(difficulties, means, yerr=stds, color=colors, alpha=0.8,
                     capsize=5, edgecolor='black')

        # Add value labels
        for bar, val in zip(bars, means):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                   f'{val:.3f}', ha='center', va='bottom', fontsize=10)

        ax.set_ylabel("Average Overall Score")
        ax.set_title("Performance by Difficulty Level")
        ax.set_ylim(0, 1.1)

        plt.tight_layout()

        output_path = os.path.join(self.output_dir, "difficulty_analysis.png")
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        return output_path

    def plot_issue_breakdown(self) -> str:
        """
        Create stacked bar chart of issues by severity.

        Returns:
            Path to saved plot
        """
        severity_counts = {}
        evaluators = ["correctness", "robustness", "safety", "hallucination"]
        severities = ["critical", "high", "medium", "low", "info"]

        for eval_type in evaluators:
            severity_counts[eval_type] = {s: 0 for s in severities}

        for task in self.tasks:
            results = task.get("evaluation", {}).get("results", {})
            for eval_type in evaluators:
                for issue in results.get(eval_type, {}).get("issues", []):
                    severity = issue.get("severity", "info")
                    if severity in severity_counts[eval_type]:
                        severity_counts[eval_type][severity] += 1

        fig, ax = plt.subplots(figsize=(10, 6))

        x = np.arange(len(evaluators))
        width = 0.6

        severity_colors = {
            "critical": "#c0392b",
            "high": "#e74c3c",
            "medium": "#f39c12",
            "low": "#f1c40f",
            "info": "#3498db"
        }

        bottom = np.zeros(len(evaluators))

        for severity in severities:
            values = [severity_counts[e][severity] for e in evaluators]
            ax.bar(x, values, width, label=severity.capitalize(),
                  bottom=bottom, color=severity_colors[severity], alpha=0.8)
            bottom += values

        ax.set_ylabel("Number of Issues")
        ax.set_title("Issue Breakdown by Evaluator and Severity")
        ax.set_xticks(x)
        ax.set_xticklabels([e.capitalize() for e in evaluators])
        ax.legend(loc='upper right')

        plt.tight_layout()

        output_path = os.path.join(self.output_dir, "issue_breakdown.png")
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        return output_path

    def plot_correlation_heatmap(self) -> str:
        """
        Create heatmap of correlations between evaluators.

        Returns:
            Path to saved plot
        """
        scores = self._extract_scores()
        evaluators = ["correctness", "robustness", "safety", "hallucination"]

        # Compute correlation matrix
        n = len(evaluators)
        corr_matrix = np.zeros((n, n))

        for i, e1 in enumerate(evaluators):
            for j, e2 in enumerate(evaluators):
                if i == j:
                    corr_matrix[i][j] = 1.0
                else:
                    corr_matrix[i][j] = self._compute_correlation(scores[e1], scores[e2])

        fig, ax = plt.subplots(figsize=(8, 6))

        if HAS_SEABORN:
            sns.heatmap(corr_matrix, annot=True, fmt=".2f",
                       xticklabels=[e.capitalize() for e in evaluators],
                       yticklabels=[e.capitalize() for e in evaluators],
                       cmap="RdYlGn", center=0, vmin=-1, vmax=1, ax=ax)
        else:
            im = ax.imshow(corr_matrix, cmap="RdYlGn", vmin=-1, vmax=1)
            ax.set_xticks(range(n))
            ax.set_yticks(range(n))
            ax.set_xticklabels([e.capitalize() for e in evaluators])
            ax.set_yticklabels([e.capitalize() for e in evaluators])

            # Add annotations
            for i in range(n):
                for j in range(n):
                    ax.text(j, i, f"{corr_matrix[i, j]:.2f}",
                           ha="center", va="center", color="black")

            plt.colorbar(im)

        ax.set_title("Evaluator Score Correlations")

        plt.tight_layout()

        output_path = os.path.join(self.output_dir, "correlation_heatmap.png")
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        return output_path

    def _compute_correlation(self, x: List[float], y: List[float]) -> float:
        """Compute Pearson correlation coefficient."""
        if len(x) < 2 or len(x) != len(y):
            return 0.0

        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        std_x = (sum((xi - mean_x) ** 2 for xi in x) / n) ** 0.5
        std_y = (sum((yi - mean_y) ** 2 for yi in y) / n) ** 0.5

        if std_x == 0 or std_y == 0:
            return 0.0

        return numerator / (n * std_x * std_y)

    def generate_all_plots(self) -> List[str]:
        """
        Generate all visualization plots.

        Returns:
            List of paths to generated plots
        """
        plots = []

        print("Generating visualizations...")

        print("  - Score distribution...")
        plots.append(self.plot_score_distribution())

        print("  - Pass rates...")
        plots.append(self.plot_pass_rates())

        print("  - Category performance...")
        plots.append(self.plot_category_performance())

        print("  - Difficulty analysis...")
        plots.append(self.plot_difficulty_analysis())

        print("  - Issue breakdown...")
        plots.append(self.plot_issue_breakdown())

        print("  - Correlation heatmap...")
        plots.append(self.plot_correlation_heatmap())

        print(f"\nAll plots saved to: {self.output_dir}")

        return plots


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate visualizations from SE-Agent experiment results"
    )
    parser.add_argument(
        "results_file",
        help="Path to raw_results.json"
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

    visualizer = ResultsVisualizer(args.results_file, args.output)
    plots = visualizer.generate_all_plots()

    print(f"\nGenerated {len(plots)} plots:")
    for plot in plots:
        print(f"  - {os.path.basename(plot)}")


if __name__ == "__main__":
    main()
