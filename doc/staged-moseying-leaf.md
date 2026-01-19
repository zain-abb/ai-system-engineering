# Implementation Plan: Multi-Model Comparison & Pass@K Integration

## Overview

Implement two enhancements to the SE-Agent experiment framework:
1. **Multi-Model Comparison Framework** - Run identical benchmarks across Claude Opus 4, Sonnet 4, and Haiku 3.5 with comparative analysis
2. **Pass@K Integration** - Integrate existing PassAtKEvaluator into the experiment runner CLI

**Estimated Total: ~950 lines of new code across 8 files**

---

## Files to Create/Modify

| File | Action | Lines |
|------|--------|-------|
| `experiments/models.py` | CREATE | ~150 |
| `experiments/multi_model_runner.py` | CREATE | ~300 |
| `experiments/visualize_comparison.py` | CREATE | ~150 |
| `experiments/run_multi_model.py` | CREATE | ~100 |
| `experiments/run_pass_at_k.py` | CREATE | ~120 |
| `experiments/config.py` | MODIFY | +30 |
| `experiments/runner.py` | MODIFY | +80 |
| `src/config.py` | MODIFY | +10 |

---

## Phase 1: Model Configuration (`experiments/models.py`)

Create centralized model configuration with pricing and rate limits.

```python
# Key components:
class ClaudeModel(Enum):
    OPUS_4 = "claude-opus-4-20250514"
    SONNET_4 = "claude-sonnet-4-20250514"
    HAIKU_3_5 = "claude-3-5-haiku-20241022"

@dataclass
class ModelConfig:
    model_id: str
    display_name: str
    input_cost: float      # Per 1M tokens
    output_cost: float     # Per 1M tokens
    max_tokens: int = 4096
    rate_limit_rpm: int = 50
    expected_latency_ms: int = 2000

MODEL_CONFIGS: Dict[ClaudeModel, ModelConfig] = {...}

def get_model_config(model: ClaudeModel) -> ModelConfig
def estimate_experiment_cost(model, num_tasks, samples_per_task=1) -> Dict
```

**Model Pricing (per 1M tokens):**
| Model | Input | Output |
|-------|-------|--------|
| Opus 4 | $15.00 | $75.00 |
| Sonnet 4 | $3.00 | $15.00 |
| Haiku 3.5 | $0.80 | $4.00 |

---

## Phase 2: Multi-Model Runner (`experiments/multi_model_runner.py`)

Create runner for comparative experiments across models.

```python
# Key components:
@dataclass
class ModelExperimentResult:
    model: str
    pass_rate: float
    average_score: float
    correctness_score: float
    robustness_score: float
    safety_score: float
    hallucination_score: float
    total_cost_usd: float
    average_latency_ms: float
    task_results: List[Dict]

@dataclass
class MultiModelComparisonResult:
    experiment_id: str
    model_results: Dict[str, ModelExperimentResult]
    best_model_by_score: str
    best_model_by_cost: str
    score_ranking: List[str]
    cost_efficiency_ranking: List[str]

class MultiModelExperimentRunner:
    def __init__(models: List[ClaudeModel], output_dir: str)
    def estimate_total_cost(num_tasks, samples_per_task) -> Dict
    async def run_single_model_experiment(model, dataset, pipeline) -> ModelExperimentResult
    async def run_comparison(dataset) -> MultiModelComparisonResult
    def _analyze_comparison(model_results) -> Dict
    def _save_results(result)
```

**Design Decisions:**
- Sequential model execution (avoid rate limit conflicts)
- Reuse existing `EvaluationPipeline` and `ClaudeClient`
- Create new ClaudeClient per model (different model_id)
- Follow existing `ExperimentJSONEncoder` pattern

---

## Phase 3: Comparison Visualization (`experiments/visualize_comparison.py`)

Generate comparison charts following existing `visualize.py` patterns.

```python
def plot_model_comparison(results_path: str) -> str:
    """Creates 2x2 subplot figure:
    1. Overall score comparison (bar chart)
    2. Per-evaluator comparison (grouped bars)
    3. Cost vs Performance scatter
    4. Latency comparison (bar chart)
    """

def generate_comparison_table(results_path: str) -> str:
    """Generate markdown table for reports."""

def plot_cost_efficiency_analysis(results_path: str) -> str:
    """Score per dollar spent."""
```

**Output:** `experiments/results/multi_model/comparison_{timestamp}/comparison_plots.png`

---

## Phase 4: Multi-Model CLI (`experiments/run_multi_model.py`)

```bash
# Usage examples:
python -m experiments.run_multi_model --estimate-only
python -m experiments.run_multi_model --models haiku sonnet
python -m experiments.run_multi_model --models haiku sonnet opus --max-tasks 10
```

**CLI Arguments:**
- `--dataset` - Path to benchmark JSON
- `--output` - Output directory
- `--models` - Models to compare (haiku, sonnet, opus)
- `--max-tasks` - Limit tasks for testing
- `--estimate-only` - Only show cost estimate

---

## Phase 5: Pass@K Config (`experiments/config.py`)

Add PassAtKConfig dataclass.

```python
@dataclass
class PassAtKConfig:
    num_samples: int = 10
    k_values: List[int] = field(default_factory=lambda: [1, 5, 10])
    temperatures: List[float] = field(default_factory=lambda: [0.2, 0.4, 0.6, 0.8])
    max_concurrent: int = 3
    correctness_threshold: float = 0.7

# Add to ExperimentConfig:
pass_at_k_config: Optional[PassAtKConfig] = None
```

---

## Phase 6: Pass@K Runner Method (`experiments/runner.py`)

Add async method to ExperimentRunner.

```python
async def run_pass_at_k_experiment(
    self,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    1. Load dataset
    2. Create PassAtKEvaluator with config
    3. For each task: await evaluator.evaluate_task()
    4. Checkpoint every N tasks
    5. Aggregate results with aggregate_pass_at_k_results()
    6. Save: pass_at_k_results.json, pass_at_k_summary.json
    """
```

**Integration with existing PassAtKEvaluator:**
- Uses `asyncio.to_thread()` for API calls
- Semaphore-based concurrency (max_concurrent=3)
- Temperature sampling: [0.2, 0.4, 0.6, 0.8]

---

## Phase 7: Pass@K CLI (`experiments/run_pass_at_k.py`)

```bash
# Usage examples:
python -m experiments.run_pass_at_k
python -m experiments.run_pass_at_k --num-samples 5 --max-tasks 5
python -m experiments.run_pass_at_k --k-values 1 5 10 --model claude-3-5-haiku-20241022
```

**CLI Arguments:**
- `--num-samples` - Samples per task (default: 10)
- `--k-values` - K values to compute (default: 1, 5, 10)
- `--temperatures` - Temperature distribution
- `--max-concurrent` - API concurrency limit
- `--model` - Model to use

---

## Phase 8: Update Pricing (`src/config.py`)

Add new models to CostConfig.pricing:

```python
pricing: dict = {
    "claude-opus-4-20250514": {"input": 0.015, "output": 0.075},
    "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
    "claude-3-5-haiku-20241022": {"input": 0.0008, "output": 0.004},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
}
```

---

## Data Flow

```
run_multi_model.py (CLI)
    │
    ▼
MultiModelExperimentRunner
    │
    ├─► ClaudeClient(model=haiku) ──► EvaluationPipeline ──► ModelExperimentResult
    ├─► ClaudeClient(model=sonnet) ──► EvaluationPipeline ──► ModelExperimentResult
    └─► ClaudeClient(model=opus) ──► EvaluationPipeline ──► ModelExperimentResult
    │
    ▼
MultiModelComparisonResult
    │
    ├─► results.json
    ├─► summary.json
    └─► comparison_plots.png
```

```
run_pass_at_k.py (CLI)
    │
    ▼
ExperimentRunner.run_pass_at_k_experiment()
    │
    ▼
PassAtKEvaluator.evaluate_task() (async)
    │
    ├─► generate_samples() ──► 10 samples at varying temps
    └─► evaluate_samples() ──► CorrectnessEvaluator
    │
    ▼
aggregate_pass_at_k_results()
    │
    ├─► pass_at_k_results.json
    └─► pass_at_k_summary.json
```

---

## Output Directory Structure

```
experiments/results/
├── multi_model/
│   └── comparison_20260118_143022/
│       ├── config.json
│       ├── results.json
│       ├── summary.json
│       └── comparison_plots.png
│
└── pass_at_k_20260118_150000/
    ├── config.json
    ├── pass_at_k_results.json
    ├── pass_at_k_summary.json
    └── checkpoints/
        └── pass_at_k_checkpoint_5.json
```

---

## Verification Plan

### 1. Unit Tests
```bash
# Test model configs
pytest tests/unit/experiments/test_models.py -v

# Test multi-model runner (with mocks)
pytest tests/unit/experiments/test_multi_model_runner.py -v
```

### 2. Cost Estimation (No API calls)
```bash
# Verify cost estimation works
python -m experiments.run_multi_model --estimate-only --models haiku sonnet
```

### 3. Quick Integration Test (Minimal API usage)
```bash
# Run with 1 task, Haiku only (~$0.01)
python -m experiments.run_multi_model --models haiku --max-tasks 1

# Run pass@k with 3 samples, 2 tasks (~$0.02)
python -m experiments.run_pass_at_k --num-samples 3 --max-tasks 2 --model claude-3-5-haiku-20241022
```

### 4. Visualization Test
```bash
# Generate plots from results
python -m experiments.visualize_comparison experiments/results/multi_model/comparison_*/results.json
```

### 5. Full Run (After verification)
```bash
# Multi-model comparison (Haiku + Sonnet)
python -m experiments.run_multi_model --models haiku sonnet

# Pass@k with Sonnet
python -m experiments.run_pass_at_k --num-samples 10
```

---

## Estimated API Costs (27 tasks)

| Experiment | Haiku | Sonnet | Opus |
|------------|-------|--------|------|
| Single sample | $0.03 | $0.18 | $0.92 |
| Pass@5 | $0.15 | $0.92 | $4.60 |
| Pass@10 | $0.31 | $1.85 | $9.20 |

**Recommended approach:** Start with Haiku for testing, then Haiku+Sonnet for comparison.

---

## Implementation Order

1. `experiments/models.py` - Foundation
2. `src/config.py` - Update pricing
3. `experiments/config.py` - Add PassAtKConfig
4. `experiments/runner.py` - Add run_pass_at_k_experiment
5. `experiments/run_pass_at_k.py` - Pass@K CLI
6. `experiments/multi_model_runner.py` - Multi-model runner
7. `experiments/run_multi_model.py` - Multi-model CLI
8. `experiments/visualize_comparison.py` - Visualization
