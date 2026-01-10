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

## Prerequisites

- Python 3.11+
- Anthropic API key
- Docker & Docker Compose (optional, for containerized deployment)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd project
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
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

### Option 1: FastAPI Server

Start the REST API server:

```bash
python -m src.main
```

The API will be available at `http://localhost:8000`

**API Endpoints:**
- `GET /health` - Health check
- `POST /generate` - Auto-detect task and generate response
- `POST /code/generate` - Generate code from requirements
- `POST /tests/generate` - Generate tests for code
- `POST /code/review` - Review code for issues
- `POST /rag/index` - Index a codebase
- `POST /rag/search` - Search indexed code
- `GET /usage` - Get API usage statistics

### Option 2: Gradio Web UI

Launch the web interface:

```bash
python -m src.ui.gradio_app
```

Open `http://localhost:7860` in your browser.

**Available Tabs:**
- **Auto Mode**: Enter any request, agent auto-detects the task
- **Code Generation**: Generate code from requirements
- **Test Generation**: Generate tests for your code
- **Code Review**: Get code review feedback
- **Requirements**: Analyze software requirements
- **Documentation**: Generate documentation
- **Evaluate Code**: Run quality evaluation on code

### Option 3: Command-Line Interface

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

### Option 4: Docker Deployment

Build and run with Docker Compose:

```bash
# Start all services (SE-Agent + ChromaDB)
docker-compose up --build

# Run in background
docker-compose up -d --build

# View logs
docker-compose logs -f se-agent

# Stop services
docker-compose down
```

Services will be available at:
- FastAPI: `http://localhost:8000`
- Gradio UI: `http://localhost:7860`
- ChromaDB: `http://localhost:8001`

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

# Code review
response = agent.review_code(
    code="your code here",
    focus="security"
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
from src.evaluation import quick_evaluate, EvaluationPipeline

# Quick evaluation
result = quick_evaluate(
    code="def factorial(n): return 1 if n <= 1 else n * factorial(n-1)",
    prompt="Write a factorial function"
)

print(f"Overall Score: {result.overall_score:.2f}")
print(f"Passed: {result.overall_passed}")

for eval_type, eval_result in result.results.items():
    print(f"{eval_type.value}: {eval_result.score:.2f}")

# Batch evaluation
from src.evaluation import generate_evaluation_report

tasks = [
    {"prompt": "Write a sorting function", "code": "def sort(arr): ..."},
    {"prompt": "Write a search function", "code": "def search(arr, x): ..."},
]

report = generate_evaluation_report(tasks, output_path="report.json")
print(f"Pass rate: {report.summary['pass_rate']:.1%}")
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

# Auto-detect and generate
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Review this code for security issues: def login(user, pwd): ..."}'
```

## Evaluation Metrics

The evaluation framework assesses generated code across four dimensions:

| Metric | Description | Checks |
|--------|-------------|--------|
| **Correctness** | Code works as intended | Syntax validity, execution success, test pass rate |
| **Robustness** | Handles edge cases | Input variations, error handling, consistency |
| **Safety** | Free from vulnerabilities | SQL injection, XSS, command injection, hardcoded secrets |
| **Hallucination** | No made-up APIs/imports | Invalid imports, fake functions, incorrect signatures |

## Project Structure

```
project/
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
│       ├── gradio_app.py       # Web interface
│       └── cli.py              # Command-line interface
├── data/
│   └── evaluation/             # Evaluation datasets
├── reports/                    # Generated reports
├── tests/                      # Unit tests
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
APP_GRADIO_PORT=7860
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=html

# Run specific test file
pytest tests/test_evaluation.py -v
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Anthropic Claude API](https://www.anthropic.com/)
- Vector storage powered by [ChromaDB](https://www.trychroma.com/)
- Web UI built with [Gradio](https://gradio.app/)
- CLI powered by [Click](https://click.palletsprojects.com/) and [Rich](https://rich.readthedocs.io/)
