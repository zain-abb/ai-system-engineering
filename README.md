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
- **Modern React UI**: Beautiful, responsive web interface with dark mode

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
- **Settings**: Manage RAG indexing, view usage stats, and clear history

### UI Features
- Dark/Light mode toggle
- Syntax-highlighted code editor
- Real-time loading states
- Toast notifications for errors/success
- Responsive design for all screen sizes
- Collapsible sidebar navigation

## API Endpoints

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
│   ├── config.py               # Experiment configuration
│   ├── runner.py               # Experiment runner
│   ├── analyze.py              # Results analysis
│   ├── visualize.py            # Visualization generation
│   ├── run_experiment.py       # CLI entry point
│   └── results/                # Experiment outputs
├── data/
│   └── evaluation/
│       └── benchmark_dataset.json  # 27 coding tasks
├── doc/
│   └── workflow.md             # Architecture documentation
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Configuration

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
