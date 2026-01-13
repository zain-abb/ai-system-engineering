#!/usr/bin/env python3
"""
Results analyzer for SE-Agent evaluation experiments.

Provides statistical analysis, aggregations, and insights from experiment results.

Usage:
    python -m experiments.analyze experiments/results/exp_*/raw_results.json
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from collections import defaultdict
import csv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class AnalysisResults:
    """Container for analysis results."""
    summary: Dict[str, Any]
    per_evaluator: Dict[str, Dict[str, Any]]
    per_category: Dict[str, Dict[str, Any]]
    per_difficulty: Dict[str, Dict[str, Any]]
    failure_patterns: List[Dict[str, Any]]
    correlations: Optional[Dict[str, float]] = None


class ResultsAnalyzer:
    """
    Analyzer for experiment results.

    Computes various statistics and insights from evaluation data.
    """

    def __init__(self, results_path: str):
        """
        Initialize analyzer with results file.

        Args:
            results_path: Path to raw_results.json
        """
        self.results_path = results_path
        self.data = self._load_results(results_path)
        self.tasks = self.data.get("tasks", [])

    def _load_results(self, path: str) -> Dict:
        """Load results from JSON file."""
        with open(path, 'r') as f:
            return json.load(f)

    def compute_summary_statistics(self) -> Dict[str, Any]:
        """
        Compute overall summary statistics.

        Returns:
            Dictionary with summary stats
        """
        if not self.tasks:
            return {"error": "No tasks found"}

        scores = []
        passed = 0
        total_issues = 0

        for task in self.tasks:
            eval_data = task.get("evaluation", {})
            overall_score = eval_data.get("overall_score", 0)
            scores.append(overall_score)

            if eval_data.get("overall_passed", False):
                passed += 1

            # Count issues from all evaluators
            for eval_type, result in eval_data.get("results", {}).items():
                total_issues += result.get("issue_count", 0)

        return {
            "total_tasks": len(self.tasks),
            "passed_tasks": passed,
            "failed_tasks": len(self.tasks) - passed,
            "pass_rate": passed / len(self.tasks) if self.tasks else 0,
            "average_score": sum(scores) / len(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "std_score": self._compute_std(scores),
            "total_issues": total_issues,
            "api_cost": self.data.get("api_cost", 0),
        }

    def compute_per_evaluator_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Compute statistics per evaluator type.

        Returns:
            Dictionary mapping evaluator name to stats
        """
        evaluator_stats = defaultdict(lambda: {
            "scores": [],
            "passed": 0,
            "issues": 0,
            "severity_counts": defaultdict(int)
        })

        for task in self.tasks:
            eval_data = task.get("evaluation", {})
            for eval_type, result in eval_data.get("results", {}).items():
                stats = evaluator_stats[eval_type]
                stats["scores"].append(result.get("score", 0))
                if result.get("passed", False):
                    stats["passed"] += 1
                stats["issues"] += result.get("issue_count", 0)

                # Count by severity
                for issue in result.get("issues", []):
                    severity = issue.get("severity", "unknown")
                    stats["severity_counts"][severity] += 1

        # Compute final stats
        final_stats = {}
        for eval_type, stats in evaluator_stats.items():
            scores = stats["scores"]
            final_stats[eval_type] = {
                "average_score": sum(scores) / len(scores) if scores else 0,
                "min_score": min(scores) if scores else 0,
                "max_score": max(scores) if scores else 0,
                "std_score": self._compute_std(scores),
                "pass_rate": stats["passed"] / len(scores) if scores else 0,
                "total_issues": stats["issues"],
                "severity_breakdown": dict(stats["severity_counts"]),
            }

        return final_stats

    def compute_per_category_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Compute statistics per task category.

        Returns:
            Dictionary mapping category to stats
        """
        category_stats = defaultdict(lambda: {
            "scores": [],
            "passed": 0,
            "tasks": []
        })

        for task in self.tasks:
            category = task.get("category", "unknown")
            eval_data = task.get("evaluation", {})
            score = eval_data.get("overall_score", 0)

            stats = category_stats[category]
            stats["scores"].append(score)
            stats["tasks"].append(task.get("task_id"))
            if eval_data.get("overall_passed", False):
                stats["passed"] += 1

        # Compute final stats
        final_stats = {}
        for category, stats in category_stats.items():
            scores = stats["scores"]
            final_stats[category] = {
                "task_count": len(scores),
                "average_score": sum(scores) / len(scores) if scores else 0,
                "min_score": min(scores) if scores else 0,
                "max_score": max(scores) if scores else 0,
                "pass_rate": stats["passed"] / len(scores) if scores else 0,
                "task_ids": stats["tasks"],
            }

        return final_stats

    def compute_per_difficulty_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Compute statistics per difficulty level.

        Returns:
            Dictionary mapping difficulty to stats
        """
        difficulty_stats = defaultdict(lambda: {
            "scores": [],
            "passed": 0
        })

        for task in self.tasks:
            difficulty = task.get("difficulty", "unknown")
            eval_data = task.get("evaluation", {})
            score = eval_data.get("overall_score", 0)

            stats = difficulty_stats[difficulty]
            stats["scores"].append(score)
            if eval_data.get("overall_passed", False):
                stats["passed"] += 1

        # Compute final stats
        final_stats = {}
        for difficulty, stats in difficulty_stats.items():
            scores = stats["scores"]
            final_stats[difficulty] = {
                "task_count": len(scores),
                "average_score": sum(scores) / len(scores) if scores else 0,
                "pass_rate": stats["passed"] / len(scores) if scores else 0,
            }

        return final_stats

    def identify_failure_patterns(self) -> List[Dict[str, Any]]:
        """
        Identify common failure patterns.

        Returns:
            List of failure pattern dictionaries
        """
        issue_patterns = defaultdict(lambda: {
            "count": 0,
            "tasks": [],
            "severities": defaultdict(int)
        })

        for task in self.tasks:
            eval_data = task.get("evaluation", {})
            for eval_type, result in eval_data.get("results", {}).items():
                for issue in result.get("issues", []):
                    category = issue.get("category", "unknown")
                    pattern = issue_patterns[category]
                    pattern["count"] += 1
                    pattern["tasks"].append(task.get("task_id"))
                    pattern["severities"][issue.get("severity", "unknown")] += 1

        # Sort by count
        patterns = []
        for category, data in sorted(issue_patterns.items(), key=lambda x: -x[1]["count"]):
            patterns.append({
                "category": category,
                "count": data["count"],
                "affected_tasks": len(set(data["tasks"])),
                "severity_breakdown": dict(data["severities"]),
            })

        return patterns[:20]  # Top 20 patterns

    def compute_correlations(self) -> Dict[str, float]:
        """
        Compute correlations between evaluator scores.

        Returns:
            Dictionary of correlation pairs
        """
        evaluators = ["correctness", "robustness", "safety", "hallucination"]
        scores = {e: [] for e in evaluators}

        for task in self.tasks:
            eval_data = task.get("evaluation", {})
            results = eval_data.get("results", {})
            for e in evaluators:
                score = results.get(e, {}).get("score", 0)
                scores[e].append(score)

        correlations = {}
        for i, e1 in enumerate(evaluators):
            for e2 in evaluators[i+1:]:
                corr = self._compute_correlation(scores[e1], scores[e2])
                correlations[f"{e1}_vs_{e2}"] = round(corr, 3)

        return correlations

    def _compute_std(self, values: List[float]) -> float:
        """Compute standard deviation."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

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

    def run_full_analysis(self) -> AnalysisResults:
        """
        Run complete analysis.

        Returns:
            AnalysisResults with all statistics
        """
        return AnalysisResults(
            summary=self.compute_summary_statistics(),
            per_evaluator=self.compute_per_evaluator_stats(),
            per_category=self.compute_per_category_stats(),
            per_difficulty=self.compute_per_difficulty_stats(),
            failure_patterns=self.identify_failure_patterns(),
            correlations=self.compute_correlations(),
        )

    def export_to_csv(self, output_path: str):
        """
        Export task-level results to CSV.

        Args:
            output_path: Path to output CSV file
        """
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            header = [
                "task_id", "category", "difficulty",
                "overall_score", "overall_passed",
                "correctness_score", "robustness_score",
                "safety_score", "hallucination_score"
            ]
            writer.writerow(header)

            # Data
            for task in self.tasks:
                eval_data = task.get("evaluation", {})
                results = eval_data.get("results", {})

                row = [
                    task.get("task_id", ""),
                    task.get("category", ""),
                    task.get("difficulty", ""),
                    eval_data.get("overall_score", 0),
                    eval_data.get("overall_passed", False),
                    results.get("correctness", {}).get("score", 0),
                    results.get("robustness", {}).get("score", 0),
                    results.get("safety", {}).get("score", 0),
                    results.get("hallucination", {}).get("score", 0),
                ]
                writer.writerow(row)

        print(f"CSV exported to: {output_path}")

    def print_report(self):
        """Print analysis report to console."""
        analysis = self.run_full_analysis()

        print("\n" + "=" * 70)
        print("EXPERIMENT ANALYSIS REPORT")
        print("=" * 70)

        # Summary
        s = analysis.summary
        print(f"\n{'SUMMARY':^70}")
        print("-" * 70)
        print(f"Total Tasks:     {s['total_tasks']}")
        print(f"Passed:          {s['passed_tasks']} ({s['pass_rate']*100:.1f}%)")
        print(f"Failed:          {s['failed_tasks']}")
        print(f"Average Score:   {s['average_score']:.3f} (std: {s['std_score']:.3f})")
        print(f"Score Range:     [{s['min_score']:.3f}, {s['max_score']:.3f}]")
        print(f"Total Issues:    {s['total_issues']}")
        print(f"API Cost:        ${s['api_cost']:.4f}")

        # Per-evaluator
        print(f"\n{'PER-EVALUATOR STATISTICS':^70}")
        print("-" * 70)
        print(f"{'Evaluator':<15} {'Avg Score':>10} {'Pass Rate':>12} {'Issues':>10}")
        print("-" * 70)
        for eval_type, stats in analysis.per_evaluator.items():
            print(f"{eval_type:<15} {stats['average_score']:>10.3f} {stats['pass_rate']*100:>11.1f}% {stats['total_issues']:>10}")

        # Per-category
        print(f"\n{'PER-CATEGORY STATISTICS':^70}")
        print("-" * 70)
        print(f"{'Category':<20} {'Tasks':>8} {'Avg Score':>12} {'Pass Rate':>12}")
        print("-" * 70)
        for category, stats in analysis.per_category.items():
            print(f"{category:<20} {stats['task_count']:>8} {stats['average_score']:>12.3f} {stats['pass_rate']*100:>11.1f}%")

        # Per-difficulty
        print(f"\n{'PER-DIFFICULTY STATISTICS':^70}")
        print("-" * 70)
        print(f"{'Difficulty':<15} {'Tasks':>8} {'Avg Score':>12} {'Pass Rate':>12}")
        print("-" * 70)
        for difficulty in ["easy", "medium", "hard"]:
            if difficulty in analysis.per_difficulty:
                stats = analysis.per_difficulty[difficulty]
                print(f"{difficulty:<15} {stats['task_count']:>8} {stats['average_score']:>12.3f} {stats['pass_rate']*100:>11.1f}%")

        # Correlations
        if analysis.correlations:
            print(f"\n{'EVALUATOR CORRELATIONS':^70}")
            print("-" * 70)
            for pair, corr in analysis.correlations.items():
                e1, e2 = pair.split("_vs_")
                print(f"{e1} <-> {e2}: {corr:+.3f}")

        # Top failure patterns
        print(f"\n{'TOP FAILURE PATTERNS':^70}")
        print("-" * 70)
        print(f"{'Category':<30} {'Count':>10} {'Affected Tasks':>15}")
        print("-" * 70)
        for pattern in analysis.failure_patterns[:10]:
            print(f"{pattern['category']:<30} {pattern['count']:>10} {pattern['affected_tasks']:>15}")

        print("\n" + "=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze SE-Agent experiment results"
    )
    parser.add_argument(
        "results_file",
        help="Path to raw_results.json"
    )
    parser.add_argument(
        "--csv", "-c",
        help="Export results to CSV file"
    )
    parser.add_argument(
        "--json", "-j",
        help="Export analysis to JSON file"
    )

    args = parser.parse_args()

    if not os.path.exists(args.results_file):
        print(f"Error: Results file not found: {args.results_file}")
        sys.exit(1)

    analyzer = ResultsAnalyzer(args.results_file)

    # Print report
    analyzer.print_report()

    # Export if requested
    if args.csv:
        analyzer.export_to_csv(args.csv)

    if args.json:
        analysis = analyzer.run_full_analysis()
        with open(args.json, 'w') as f:
            json.dump({
                "summary": analysis.summary,
                "per_evaluator": analysis.per_evaluator,
                "per_category": analysis.per_category,
                "per_difficulty": analysis.per_difficulty,
                "failure_patterns": analysis.failure_patterns,
                "correlations": analysis.correlations,
            }, f, indent=2)
        print(f"Analysis exported to: {args.json}")


if __name__ == "__main__":
    main()
