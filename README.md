# SE-Agent: AI-Powered Software Engineering Assistant

An AI-powered virtual agent that assists software engineers with code generation, test generation, code review, requirements analysis, and documentation. Built with Claude API and includes a comprehensive evaluation framework for assessing correctness, robustness, safety, and hallucination.

## Features

- **Code Generation**: Generate code from natural language requirements
- **Test Generation**: Automatically create unit tests for your code
- **Code Review**: Get detailed feedback on code quality, bugs, and improvements
- **Requirements Analysis**: Analyze and structure software requirements
- **Documentation**: Generate API docs, README files, and inline documentation
- **RAG Support**: Index your codebase for context-aware generation
- **Evaluation Framework**: Assess generated code for quality metrics
- **Real-Time Streaming**: SSE-based streaming with live processing step visibility
- **Modern React UI**: Beautiful, responsive web interface with dark mode
- **State Persistence**: Maintain form inputs and results across tab navigation
- **Global Model Selection**: Choose between Claude Haiku, Sonnet, or Opus for all generations
- **Multi-Model Comparison**: Compare code quality across Claude Opus 4, Sonnet 4, and Haiku 3.5
- **Pass@K Metrics**: Industry-standard evaluation using the Pass@K methodology

## Quick Reference

```bash
# Run tests
pytest tests/unit/ -v          # Unit tests (325 tests)
pytest tests/integration/ -v   # Integration tests (56 tests)
pytest tests/ -v               # All tests (381 tests)

# Run experiments
python -m experiments.run_experiment --max-tasks 10      # Single model experiment
python -m experiments.run_pass_at_k --num-samples 5      # Pass@K evaluation
python -m experiments.run_multi_model --models haiku sonnet  # Multi-model comparison

# Cost estimation (no API calls)
python -m experiments.run_pass_at_k --estimate-only
python -m experiments.run_multi_model --estimate-only

# Analyze results
python -m experiments.analyze experiments/results/exp_*/raw_results.json
python -m experiments.visualize_comparison experiments/results/multi_model/comparison_*/results.json
```

## Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend development)
- Anthropic API key
- Docker & Docker Compose (optional, for containerized deployment)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd project
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key:

```env
ANTHROPIC_API_KEY=your-api-key-here
```

## Running the Application

### Option 1: Development Mode (Recommended for Development)

Start both the backend and frontend in separate terminals:

**Terminal 1 - Backend:**
```bash
python -m src.main
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

- Backend API: `http://localhost:8000`
- Frontend UI: `http://localhost:5173`

### Option 2: Command-Line Interface

The CLI provides quick access to all features:

```bash
# Generate code
python -m src.ui.cli generate "Write a function to calculate fibonacci numbers"

# Generate tests for a file
python -m src.ui.cli test path/to/code.py -o tests.py

# Review code
python -m src.ui.cli review path/to/code.py --focus security

# Evaluate code quality
python -m src.ui.cli evaluate path/to/code.py

# Index a codebase for RAG
python -m src.ui.cli index ./src -e .py

# Search indexed code
python -m src.ui.cli search "authentication logic"

# Auto-detect task type
python -m src.ui.cli ask "How do I implement user authentication?"

# Interactive mode
python -m src.ui.cli interactive

# Show usage statistics
python -m src.ui.cli usage

# Batch evaluation
python -m src.ui.cli batch-evaluate dataset.json -o report.json
```

### Option 3: Docker Deployment (Production)

Build and run with Docker Compose:

```bash
# Start all services (Frontend + Backend + ChromaDB)
docker-compose up --build

# Run in background
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services will be available at:
- Frontend UI: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- ChromaDB: `http://localhost:8001`

## Web Interface Features

The React-based web interface includes:

- **Dashboard**: Overview with quick actions, usage stats, and system status
- **Code Generation**: Generate code from natural language requirements
- **Test Generation**: Create unit tests with framework selection
- **Code Review**: Get detailed code review with focus areas
- **Requirements Analysis**: Analyze and structure requirements
- **Documentation**: Generate API docs, README, and inline comments
- **Evaluation**: Check code for correctness, robustness, safety, and hallucination
- **Settings**: Configure AI model selection, manage RAG indexing, view usage stats, and clear history

### UI Features
- Dark/Light mode toggle
- Syntax-highlighted code editor
- **Real-time streaming** with processing step visibility
- Toast notifications for errors/success
- Responsive design for all screen sizes
- Collapsible sidebar navigation
- **State persistence** across tab navigation
- **Global model selection** (Haiku, Sonnet, Opus) with localStorage persistence
- GitHub-flavored markdown rendering with copy button

## API Endpoints

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check and capabilities |
| `/generate` | POST | Auto-detect task and generate |
| `/code/generate` | POST | Generate code from requirements |
| `/tests/generate` | POST | Generate tests for code |
| `/code/review` | POST | Review code for issues |
| `/usage` | GET | API usage statistics |
| `/history` | GET | Conversation history |
| `/history` | DELETE | Clear history |
| `/rag/index` | POST | Index a codebase |
| `/rag/stats` | GET | RAG system statistics |
| `/rag/search` | POST | Search indexed code |

### SSE Streaming Endpoints

All streaming endpoints return Server-Sent Events (SSE) with real-time processing updates.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/code/generate/stream` | POST | Stream code generation with step updates |
| `/tests/generate/stream` | POST | Stream test generation with step updates |
| `/code/review/stream` | POST | Stream code review with step updates |
| `/generate/stream` | POST | Stream generic generation (docs, requirements) |

#### SSE Event Types

```
event: step_start
data: {"type": "step_start", "data": {"step": "intent_classification", "message": "Classifying intent..."}}

event: step_complete
data: {"type": "step_complete", "data": {"step": "intent_classification", "message": "Intent classified", "result": {...}}}

event: done
data: {"type": "done", "result": "...", "usage": {...}, "capability_used": "code_generation"}

event: error
data: {"type": "error", "data": {"message": "Error description"}}
```

## Real-Time Streaming

SE-Agent implements Server-Sent Events (SSE) for real-time visibility into the processing pipeline. This provides users with immediate feedback on each stage of code generation, review, and analysis.

### Processing Steps

When using streaming endpoints, the following steps are reported in real-time:

1. **Intent Classification** - Determining the type of request (code generation, review, etc.)
2. **Semantic Search** - Retrieving relevant context from the indexed codebase (RAG)
3. **LLM Generation** - Generating the response using Claude API

### Frontend Integration

The React frontend uses a custom `useStreamingGeneration` hook that:
- Establishes EventSource connections to streaming endpoints
- Tracks processing step status (pending → in-progress → completed)
- Supports request cancellation
- Maintains state across tab navigation

### Using Streaming with cURL

```bash
# Stream code generation
curl -N -X POST http://localhost:8000/code/generate/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"requirements": "Write a factorial function", "language": "python"}'

# Stream code review
curl -N -X POST http://localhost:8000/code/review/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"code": "def add(a,b): return a+b", "language": "python"}'
```

### Using Streaming with JavaScript

```javascript
const eventSource = new EventSource('/code/generate/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ requirements: 'Write a factorial function', language: 'python' })
});

eventSource.addEventListener('step_start', (e) => {
  const data = JSON.parse(e.data);
  console.log(`Starting: ${data.data.step}`);
});

eventSource.addEventListener('step_complete', (e) => {
  const data = JSON.parse(e.data);
  console.log(`Completed: ${data.data.step}`);
});

eventSource.addEventListener('done', (e) => {
  const data = JSON.parse(e.data);
  console.log('Result:', data.result);
  eventSource.close();
});

eventSource.addEventListener('error', (e) => {
  console.error('Error:', e.data);
  eventSource.close();
});
```

### State Persistence

The frontend maintains state across tab navigation using React Context (`CapabilityStateContext`). This means:
- Form inputs are preserved when switching between pages
- Generated results remain visible after navigation
- Processing history is maintained for each capability

## Usage Examples

### Python API

```python
from src.agent import create_agent

# Create agent
agent = create_agent(use_llm_routing=True)

# Generate code
response = agent.generate_code(
    requirements="Create a function that validates email addresses",
    language="python"
)
print(response.result)

# Generate tests
response = agent.generate_tests(
    code="def add(a, b): return a + b",
    framework="pytest"
)
print(response.result)

# Auto-detect intent
response = agent.process(
    user_input="Write unit tests for this authentication module",
    context="existing code context..."
)
print(f"Detected: {response.capability_used}")
print(response.result)
```

### Evaluation Framework

```python
from src.evaluation import quick_evaluate, generate_evaluation_report

# Quick evaluation
result = quick_evaluate(
    code="def factorial(n): return 1 if n <= 1 else n * factorial(n-1)",
    prompt="Write a factorial function"
)

print(f"Overall Score: {result.overall_score:.2f}")
print(f"Passed: {result.overall_passed}")

for eval_type, eval_result in result.results.items():
    print(f"{eval_type.value}: {eval_result.score:.2f}")
```

### Evaluation Pipeline

The evaluation pipeline runs all four evaluators and aggregates results:

```python
from src.evaluation import EvaluationPipeline, EvaluationConfig

# Create pipeline with custom thresholds
config = EvaluationConfig(
    correctness_threshold=0.7,
    robustness_threshold=0.6,
    safety_threshold=0.7,
    hallucination_threshold=0.7,
    weights={
        "correctness": 0.35,
        "robustness": 0.20,
        "safety": 0.25,
        "hallucination": 0.20
    }
)
pipeline = EvaluationPipeline(config=config)

# Evaluate code
result = pipeline.evaluate(
    code="def add(a, b): return a + b",
    prompt="Add two numbers",
    language="python"
)

print(f"Passed: {result.overall_passed}")
print(f"Score: {result.overall_score:.3f}")
```

### Pass@K Evaluator

Evaluate code generation with multiple samples:

```python
from src.evaluation import PassAtKEvaluator

evaluator = PassAtKEvaluator(
    num_samples=10,
    k_values=[1, 5, 10],
    temperatures=[0.2, 0.4, 0.6, 0.8]
)

# Evaluate a task
result = await evaluator.evaluate_task(
    task_id="factorial",
    prompt="Write a factorial function",
    test_cases=[
        {"input": {"n": 5}, "expected": 120},
        {"input": {"n": 0}, "expected": 1}
    ]
)

print(f"Pass@1: {result['pass_at_k']['pass@1']:.3f}")
print(f"Pass@5: {result['pass_at_k']['pass@5']:.3f}")
```

### REST API

```bash
# Health check
curl http://localhost:8000/health

# Generate code
curl -X POST http://localhost:8000/code/generate \
  -H "Content-Type: application/json" \
  -d '{"requirements": "Write a function to reverse a string", "language": "python"}'

# Generate tests
curl -X POST http://localhost:8000/tests/generate \
  -H "Content-Type: application/json" \
  -d '{"code": "def add(a, b): return a + b", "framework": "pytest"}'
```

## Evaluation Metrics

The evaluation framework assesses generated code across four dimensions:

| Metric | Description | Checks |
|--------|-------------|--------|
| **Correctness** | Code works as intended | Syntax validity, execution success, test pass rate |
| **Robustness** | Handles edge cases | Input variations, error handling, consistency |
| **Safety** | Free from vulnerabilities | SQL injection, XSS, command injection, hardcoded secrets |
| **Hallucination** | No made-up APIs/imports | Invalid imports, fake functions, incorrect signatures |

## Testing

The project includes comprehensive test suites for unit and integration testing.

### Running Unit Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage report
pytest tests/unit/ --cov=src --cov-report=term-missing

# Run specific test module
pytest tests/unit/evaluation/ -v

# Run tests matching a pattern
pytest tests/unit/ -k "correctness" -v
```

### Running Integration Tests

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run evaluation pipeline tests
pytest tests/integration/test_evaluation_pipeline.py -v

# Run RAG integration tests
pytest tests/integration/test_rag.py -v

# Run API endpoint tests
pytest tests/integration/test_api.py -v
```

### Running All Tests

```bash
# Run full test suite
pytest tests/ -v

# Run with parallel execution (faster)
pytest tests/ -v -n auto

# Generate HTML coverage report
pytest tests/ --cov=src --cov-report=html
```

### Test Coverage Summary

| Test Type | Count | Coverage |
|-----------|-------|----------|
| Unit Tests | 325 | Core modules, evaluators |
| Integration Tests | 56 | Pipeline, RAG, API |
| **Total** | **381** | **Comprehensive** |

## Running Experiments

The project includes a comprehensive experiment framework for empirical evaluation of LLM code generation quality.

### Benchmark Dataset

The benchmark dataset (`data/evaluation/benchmark_dataset.json`) contains 27 coding tasks across 5 categories:

| Category | Tasks | Description |
|----------|-------|-------------|
| Algorithms | 10 | Sorting, searching, recursion, dynamic programming |
| Data Structures | 5 | Stack, queue, linked list, BST, hash table |
| String Manipulation | 5 | Parsing, validation, compression |
| File/API | 4 | JSON parsing, CSV handling, HTTP utilities |
| Error Handling | 3 | Safe operations, validation, parsing |

### Running an Experiment

```bash
# Run full experiment (evaluates all 27 tasks)
python -m experiments.run_experiment

# Quick test with limited tasks
python -m experiments.run_experiment --max-tasks 5

# Filter by category
python -m experiments.run_experiment --categories algorithms data_structures

# Filter by difficulty
python -m experiments.run_experiment --difficulties easy medium

# Custom output directory
python -m experiments.run_experiment --output experiments/my_results
```

### Analyzing Results

```bash
# Print detailed analysis report
python -m experiments.analyze experiments/results/exp_*/raw_results.json

# Export to CSV
python -m experiments.analyze experiments/results/exp_*/raw_results.json --csv results.csv

# Export analysis to JSON
python -m experiments.analyze experiments/results/exp_*/raw_results.json --json analysis.json
```

### Generating Visualizations

```bash
# Generate all plots
python -m experiments.visualize experiments/results/exp_*/raw_results.json

# Custom output directory
python -m experiments.visualize experiments/results/exp_*/raw_results.json --output plots/
```

Generated visualizations include:
- `score_distribution.png` - Box plots of scores per evaluator
- `pass_rates.png` - Bar chart of pass rates by evaluator
- `category_performance.png` - Performance breakdown by task category
- `difficulty_analysis.png` - Scores vs difficulty level
- `issue_breakdown.png` - Issues by severity per evaluator
- `correlation_heatmap.png` - Correlations between evaluator scores

### Experiment Output Structure

```
experiments/results/exp_YYYYMMDD_HHMMSS/
├── config.json              # Experiment configuration & environment
├── raw_results.json         # Full task-by-task results
├── evaluation_report.json   # Detailed evaluation data
├── summary.json             # Aggregated statistics
├── checkpoints/             # Intermediate saves for resumability
└── plots/                   # Generated visualizations
    ├── score_distribution.png
    ├── pass_rates.png
    ├── category_performance.png
    ├── difficulty_analysis.png
    ├── issue_breakdown.png
    └── correlation_heatmap.png
```

### Reproducing Experiments

For full reproducibility, each experiment saves:
- Git commit hash
- Python and library versions
- Dataset SHA-256 hash
- Full configuration parameters
- Timestamped results

## Pass@K Evaluation

Pass@K measures the probability that at least one of K generated samples passes all tests. This is a standard metric for evaluating code generation quality used in benchmarks like HumanEval.

### Running Pass@K Experiments

```bash
# Run Pass@K experiment with defaults (10 samples, k=[1,5,10])
python -m experiments.run_pass_at_k

# Cost estimation only (no API calls)
python -m experiments.run_pass_at_k --estimate-only

# Quick test with fewer samples
python -m experiments.run_pass_at_k --num-samples 5 --max-tasks 5

# Custom K values
python -m experiments.run_pass_at_k --k-values 1 3 5

# Use specific model
python -m experiments.run_pass_at_k --model claude-3-5-haiku-20241022
```

### Pass@K CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--num-samples` | 10 | Number of code samples per task |
| `--k-values` | 1, 5, 10 | K values to compute Pass@K for |
| `--temperatures` | 0.2, 0.4, 0.6, 0.8 | Temperature distribution for sampling |
| `--max-concurrent` | 3 | Maximum concurrent API calls |
| `--model` | claude-3-5-haiku-20241022 | Model to use |
| `--max-tasks` | None | Limit number of tasks (for testing) |
| `--estimate-only` | False | Only show cost estimate |

### Pass@K Output

Results are saved to `experiments/results/pass_at_k_YYYYMMDD_HHMMSS/`:
- `pass_at_k_results.json` - Detailed per-task results
- `pass_at_k_summary.json` - Aggregated statistics
- `checkpoints/` - Intermediate saves for resumability

### Understanding Pass@K Results

```
Pass@K Results:
  Pass@1:  Mean: 0.850, Std: 0.120
  Pass@5:  Mean: 0.950, Std: 0.080
  Pass@10: Mean: 0.980, Std: 0.040
```

- **Pass@1**: Probability that the first sample is correct (strictest)
- **Pass@5**: Probability at least 1 of 5 samples is correct
- **Pass@10**: Probability at least 1 of 10 samples is correct

## Multi-Model Comparison

Compare code generation quality across different Claude models on identical benchmarks.

### Supported Models

| Model | ID | Input Cost | Output Cost | Best For |
|-------|-----|------------|-------------|----------|
| **Claude Opus 4** | claude-opus-4-20250514 | $15.00/1M | $75.00/1M | Complex reasoning |
| **Claude Sonnet 4** | claude-sonnet-4-20250514 | $3.00/1M | $15.00/1M | Balanced performance |
| **Claude 3.5 Haiku** | claude-3-5-haiku-20241022 | $0.80/1M | $4.00/1M | Fast & cost-effective |

### Running Multi-Model Experiments

```bash
# Cost estimation only
python -m experiments.run_multi_model --estimate-only

# Compare Haiku and Sonnet (recommended starting point)
python -m experiments.run_multi_model --models haiku sonnet

# Compare all three models
python -m experiments.run_multi_model --models haiku sonnet opus

# Quick test with limited tasks
python -m experiments.run_multi_model --models haiku sonnet --max-tasks 5

# Full benchmark
python -m experiments.run_multi_model --models haiku sonnet opus
```

### Multi-Model CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--models` | haiku, sonnet | Models to compare (haiku, sonnet, opus) |
| `--max-tasks` | None | Limit number of tasks |
| `--estimate-only` | False | Only show cost estimate |
| `--dataset` | benchmark_dataset.json | Path to dataset |
| `--output` | experiments/results | Output directory |

### Multi-Model Output

Results are saved to `experiments/results/multi_model/comparison_YYYYMMDD_HHMMSS/`:
- `results.json` - Full comparison data
- `summary.json` - Rankings and key metrics
- `comparison_plots.png` - Visualization charts

### Visualizing Comparison Results

```bash
# Generate comparison visualizations
python -m experiments.visualize_comparison experiments/results/multi_model/comparison_*/results.json
```

Generated plots include:
- Overall score comparison (bar chart)
- Per-evaluator breakdown (grouped bars)
- Cost vs Performance scatter plot
- Cost efficiency analysis (score per dollar)

### Example Multi-Model Results

```
======================================================================
MULTI-MODEL COMPARISON SUMMARY
======================================================================
Model                      Pass Rate  Avg Score       Cost     Duration
----------------------------------------------------------------------
Claude Sonnet 4               100.0%      0.910 $  0.0815       69.9s
Claude 3.5 Haiku              100.0%      0.909 $  0.0836       70.4s
----------------------------------------------------------------------

Rankings:
  Best by Score: Claude Sonnet 4
  Best by Cost Efficiency: Claude Sonnet 4
```

## Project Structure

```
project/
├── frontend/                    # React + ShadCN UI
│   ├── src/
│   │   ├── components/         # Reusable UI components
│   │   ├── pages/              # Page components
│   │   ├── hooks/              # Custom React hooks
│   │   ├── lib/                # Utilities and API client
│   │   └── types/              # TypeScript types
│   ├── package.json
│   └── Dockerfile
├── src/
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Configuration management
│   ├── agent/
│   │   ├── controller.py       # Main agent orchestration
│   │   ├── router.py           # Intent classification
│   │   └── prompts/            # Prompt templates
│   ├── capabilities/
│   │   ├── code_generation.py
│   │   ├── test_generation.py
│   │   ├── code_review.py
│   │   ├── requirements.py
│   │   └── documentation.py
│   ├── evaluation/
│   │   ├── correctness.py      # Syntax & execution checks
│   │   ├── robustness.py       # Edge case handling
│   │   ├── safety.py           # Security vulnerability scan
│   │   ├── hallucination.py    # Fake API detection
│   │   ├── pass_at_k.py        # Pass@K metric implementation
│   │   └── metrics.py          # Aggregation & reporting
│   ├── rag/
│   │   ├── indexer.py          # AST-based code parsing
│   │   ├── vectorstore.py      # ChromaDB integration
│   │   └── retriever.py        # Semantic search
│   ├── services/
│   │   └── claude_client.py    # Anthropic API wrapper
│   └── ui/
│       └── cli.py              # Command-line interface
├── experiments/                 # Experiment framework
│   ├── config.py               # Experiment & Pass@K configuration
│   ├── runner.py               # Single-model experiment runner
│   ├── models.py               # Model configs, pricing, aliases
│   ├── multi_model_runner.py   # Multi-model comparison runner
│   ├── analyze.py              # Results analysis
│   ├── visualize.py            # Single experiment visualization
│   ├── visualize_comparison.py # Multi-model comparison plots
│   ├── run_experiment.py       # Single experiment CLI
│   ├── run_pass_at_k.py        # Pass@K experiment CLI
│   ├── run_multi_model.py      # Multi-model comparison CLI
│   └── results/                # Experiment outputs
│       ├── exp_*/              # Single experiment results
│       ├── pass_at_k_*/        # Pass@K results
│       └── multi_model/        # Multi-model comparison results
├── tests/
│   ├── unit/                   # Unit tests (325 tests)
│   │   ├── evaluation/         # Evaluator tests
│   │   ├── capabilities/       # Capability module tests
│   │   └── ...
│   └── integration/            # Integration tests (56 tests)
│       ├── test_evaluation_pipeline.py
│       ├── test_rag.py
│       └── test_api.py
├── data/
│   └── evaluation/
│       └── benchmark_dataset.json  # 27 coding tasks
├── reports/
│   ├── se_agent_report.tex     # LaTeX research report
│   └── figures/                # Report figures
├── doc/
│   └── workflow.md             # Architecture documentation
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Configuration

### Global Model Selection

The web UI includes a global model selector in the Settings page that persists across sessions:

| Model | Description | Best For |
|-------|-------------|----------|
| **Haiku** (default) | Fast & cost-effective | Quick iterations, simple tasks |
| **Sonnet** | Balanced performance | Most development work |
| **Opus** | Highest quality | Complex reasoning, critical code |

The selected model is stored in localStorage and used for all capability pages (Code Generation, Test Generation, Code Review, Documentation, Requirements).

### Environment Variables

Key configuration options in `.env`:

```env
# Required
ANTHROPIC_API_KEY=your-api-key

# Optional - Model Selection
ANTHROPIC_MODEL=claude-sonnet-4-20250514
ANTHROPIC_FAST_MODEL=claude-haiku-4-20250514

# Optional - Cost Control
COST_DAILY_LIMIT=10.0
COST_WARNING_THRESHOLD=0.8

# Optional - ChromaDB (for RAG)
CHROMA_HOST=localhost
CHROMA_PORT=8001

# Optional - Server
APP_HOST=0.0.0.0
APP_API_PORT=8000
```

## Model Configuration & Pricing

The experiment framework includes centralized model configuration with accurate pricing for cost estimation.

### Available Models

```python
from experiments.models import ClaudeModel, get_model_config

# Get model configuration
config = get_model_config(ClaudeModel.SONNET_4)
print(f"Model: {config.display_name}")
print(f"Input cost: ${config.input_cost}/1M tokens")
print(f"Output cost: ${config.output_cost}/1M tokens")
```

### Model Aliases

For convenience, use short aliases in CLI commands:

| Alias | Full Model ID |
|-------|---------------|
| `opus` | claude-opus-4-20250514 |
| `sonnet` | claude-sonnet-4-20250514 |
| `haiku` | claude-3-5-haiku-20241022 |

### Cost Estimation

Estimate experiment costs before running:

```python
from experiments.models import estimate_experiment_cost, ClaudeModel

# Single model estimate
estimate = estimate_experiment_cost(ClaudeModel.HAIKU_3_5, num_tasks=27)
print(f"Estimated cost: ${estimate['total_cost']:.2f}")
print(f"Estimated time: {estimate['estimated_time_minutes']:.1f} minutes")

# Multi-model estimate
from experiments.models import estimate_multi_model_cost
estimate = estimate_multi_model_cost(
    models=[ClaudeModel.HAIKU_3_5, ClaudeModel.SONNET_4],
    num_tasks=27
)
print(f"Total cost: ${estimate['total_cost']:.2f}")
```

### Estimated Costs (27 tasks)

| Experiment Type | Haiku | Sonnet | Opus |
|-----------------|-------|--------|------|
| Single sample | ~$0.03 | ~$0.18 | ~$0.92 |
| Pass@5 | ~$0.15 | ~$0.92 | ~$4.60 |
| Pass@10 | ~$0.31 | ~$1.85 | ~$9.20 |

**Recommendation**: Start with Haiku for testing, then use Haiku+Sonnet for production comparisons.

## Technology Stack

### Backend
- **FastAPI** - High-performance Python web framework
- **Anthropic Claude API** - LLM for code generation and analysis
- **ChromaDB** - Vector database for RAG
- **sentence-transformers** - Local embeddings

### Frontend
- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Utility-first styling
- **ShadCN UI** - Component library (Radix primitives)
- **TanStack Query** - Data fetching and caching
- **React Router** - Client-side routing

## License

This project is licensed under the MIT License - see the LICENSE file for details.
