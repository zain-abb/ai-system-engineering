"""
Experiments module for SE-Agent evaluation.

This module provides tools for running evaluation experiments on
LLM-generated code, analyzing results, and creating visualizations.
"""

# Lazy imports to avoid circular dependencies
__all__ = ["ExperimentConfig", "ExperimentRunner"]


def __getattr__(name):
    if name == "ExperimentConfig":
        from experiments.config import ExperimentConfig
        return ExperimentConfig
    elif name == "ExperimentRunner":
        from experiments.runner import ExperimentRunner
        return ExperimentRunner
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
