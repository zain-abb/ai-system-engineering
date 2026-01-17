# Implementation Plan: Project Enhancements

This document outlines the implementation plan for three key enhancements to the SE-Agent project:
1. Integration Tests
2. Pass@k Evaluation
3. Multi-Model Comparison (Claude Models)

---

## 1. Integration Tests

### 1.1 Overview

Integration tests verify that different components of the system work together correctly. Unlike unit tests (which test components in isolation), integration tests validate end-to-end workflows.

### 1.2 Test Categories

#### Category A: API Endpoint Tests
Test the FastAPI REST endpoints with real request/response cycles.

```
tests/integration/
├── conftest.py                 # Shared fixtures (test client, mock data)
├── test_api_endpoints.py       # REST API integration tests
├── test_capability_pipeline.py # End-to-end capability tests
├── test_evaluation_pipeline.py # Full evaluation workflow tests
├── test_rag_integration.py     # RAG indexing and retrieval tests
└── test_agent_routing.py       # Intent routing integration tests
```

#### Category B: Capability Pipeline Tests
Test complete workflows from user input to final output.

#### Category C: Evaluation Pipeline Tests
Test the full evaluation workflow with all four evaluators.

### 1.3 Implementation Details

#### A. API Endpoint Tests (`test_api_endpoints.py`)

```python
"""
Integration tests for FastAPI REST endpoints.
Tests real HTTP request/response cycles using TestClient.
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    """Create test client for API testing."""
    return TestClient(app)


@pytest.fixture
def sample_code_request():
    """Sample code generation request."""
    return {
        "message": "Write a Python function to calculate factorial",
        "context": None
    }


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check(self, client):
        """Test /health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_readiness_check(self, client):
        """Test /ready endpoint."""
        response = client.get("/ready")
        assert response.status_code == 200


class TestCapabilityEndpoints:
    """Test capability API endpoints."""

    def test_code_generation_endpoint(self, client, sample_code_request):
        """Test POST /api/generate endpoint."""
        response = client.post("/api/generate", json=sample_code_request)
        assert response.status_code == 200
        data = response.json()
        assert "code" in data or "response" in data
        assert "usage" in data  # Token usage tracking

    def test_code_review_endpoint(self, client):
        """Test POST /api/review endpoint."""
        request = {
            "code": "def add(a, b): return a + b",
            "focus_areas": ["security", "performance"]
        }
        response = client.post("/api/review", json=request)
        assert response.status_code == 200

    def test_test_generation_endpoint(self, client):
        """Test POST /api/generate-tests endpoint."""
        request = {
            "code": "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)",
            "framework": "pytest"
        }
        response = client.post("/api/generate-tests", json=request)
        assert response.status_code == 200


class TestEvaluationEndpoints:
    """Test evaluation API endpoints."""

    def test_evaluate_code_endpoint(self, client):
        """Test POST /api/evaluate endpoint."""
        request = {
            "code": "def hello(): print('Hello, World!')",
            "evaluators": ["correctness", "safety"]
        }
        response = client.post("/api/evaluate", json=request)
        assert response.status_code == 200
        data = response.json()
        assert "scores" in data
        assert "overall_score" in data


class TestErrorHandling:
    """Test API error handling."""

    def test_invalid_request_body(self, client):
        """Test 422 for invalid request body."""
        response = client.post("/api/generate", json={})
        assert response.status_code == 422

    def test_invalid_endpoint(self, client):
        """Test 404 for non-existent endpoint."""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404
```

#### B. Capability Pipeline Tests (`test_capability_pipeline.py`)

```python
"""
Integration tests for end-to-end capability pipelines.
Tests complete workflows from input to output.
"""
import pytest
from src.capabilities.code_generation import CodeGenerationCapability
from src.capabilities.test_generation import TestGenerationCapability
from src.capabilities.code_review import CodeReviewCapability
from src.services.claude_client import ClaudeClient


@pytest.fixture
def claude_client():
    """Create real Claude client (requires API key)."""
    return ClaudeClient()


@pytest.fixture
def code_gen_capability(claude_client):
    """Create code generation capability."""
    return CodeGenerationCapability(claude_client)


class TestCodeGenerationPipeline:
    """End-to-end code generation tests."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_generate_simple_function(self, code_gen_capability):
        """Test generating a simple function end-to-end."""
        result = code_gen_capability.generate(
            prompt="Write a Python function to reverse a string",
            language="python"
        )

        assert result is not None
        assert "def" in result.code
        assert "reverse" in result.code.lower() or "[::-1]" in result.code

        # Verify the code is syntactically valid
        compile(result.code, "<string>", "exec")

    @pytest.mark.integration
    @pytest.mark.slow
    def test_generate_with_context(self, code_gen_capability):
        """Test code generation with RAG context."""
        context = """
        # Existing codebase uses this pattern:
        def validate_input(value):
            if value is None:
                raise ValueError("Input cannot be None")
            return value
        """

        result = code_gen_capability.generate(
            prompt="Write a function to validate email addresses",
            language="python",
            context=context
        )

        assert result is not None
        # Should follow similar error handling pattern
        assert "raise" in result.code or "ValueError" in result.code


class TestTestGenerationPipeline:
    """End-to-end test generation tests."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_generate_pytest_tests(self):
        """Test generating pytest test cases."""
        capability = TestGenerationCapability(ClaudeClient())

        source_code = """
def add(a: int, b: int) -> int:
    return a + b

def multiply(a: int, b: int) -> int:
    return a * b
"""

        result = capability.generate(
            code=source_code,
            framework="pytest"
        )

        assert result is not None
        assert "def test_" in result.tests
        assert "assert" in result.tests


class TestCodeReviewPipeline:
    """End-to-end code review tests."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_review_identifies_issues(self):
        """Test that code review identifies security issues."""
        capability = CodeReviewCapability(ClaudeClient())

        vulnerable_code = """
import os

def run_command(user_input):
    os.system(user_input)  # Command injection vulnerability

def query_db(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"  # SQL injection
    return query
"""

        result = capability.review(code=vulnerable_code)

        assert result is not None
        assert len(result.issues) > 0
        # Should identify security issues
        issue_types = [issue.category.lower() for issue in result.issues]
        assert any("security" in t or "injection" in t for t in issue_types)
```

#### C. Evaluation Pipeline Tests (`test_evaluation_pipeline.py`)

```python
"""
Integration tests for the full evaluation pipeline.
Tests all four evaluators working together.
"""
import pytest
from src.evaluation.correctness import CorrectnessEvaluator
from src.evaluation.robustness import RobustnessEvaluator
from src.evaluation.safety import SafetyEvaluator
from src.evaluation.hallucination import HallucinationEvaluator
from src.evaluation.metrics import EvaluationPipeline


@pytest.fixture
def evaluation_pipeline():
    """Create full evaluation pipeline."""
    return EvaluationPipeline(
        evaluators=[
            CorrectnessEvaluator(),
            RobustnessEvaluator(),
            SafetyEvaluator(),
            HallucinationEvaluator()
        ]
    )


class TestFullEvaluationPipeline:
    """Test complete evaluation workflow."""

    @pytest.mark.integration
    def test_evaluate_correct_safe_code(self, evaluation_pipeline):
        """Test evaluation of well-written code."""
        code = '''
def factorial(n: int) -> int:
    """Calculate factorial of n."""
    if not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return 1
    return n * factorial(n - 1)
'''
        test_cases = [
            {"input": "factorial(0)", "expected": "1"},
            {"input": "factorial(1)", "expected": "1"},
            {"input": "factorial(5)", "expected": "120"},
        ]

        result = evaluation_pipeline.evaluate(
            code=code,
            test_cases=test_cases,
            prompt="Write a factorial function"
        )

        # Should pass all evaluations
        assert result.overall_score >= 0.7
        assert result.passed is True
        assert result.scores["safety"] >= 0.9  # No vulnerabilities
        assert result.scores["hallucination"] >= 0.9  # No fake APIs

    @pytest.mark.integration
    def test_evaluate_unsafe_code(self, evaluation_pipeline):
        """Test evaluation detects unsafe code."""
        unsafe_code = '''
import pickle
import os

def process_data(user_data):
    # Unsafe deserialization
    obj = pickle.loads(user_data)

    # Command injection
    os.system(f"echo {obj}")

    return obj
'''

        result = evaluation_pipeline.evaluate(
            code=unsafe_code,
            test_cases=[],
            prompt="Process user data"
        )

        # Safety score should be low
        assert result.scores["safety"] < 0.7
        assert any(
            issue.category == "command_injection" or
            issue.category == "insecure_deserialization"
            for issue in result.issues
        )

    @pytest.mark.integration
    def test_evaluate_hallucinating_code(self, evaluation_pipeline):
        """Test evaluation detects hallucinated APIs."""
        hallucinating_code = '''
from utils.magic_helpers import auto_optimize
from fake_module import SmartProcessor

def process(data):
    processor = SmartProcessor()
    return processor.auto_analyze(data).smart_transform()
'''

        result = evaluation_pipeline.evaluate(
            code=hallucinating_code,
            test_cases=[],
            prompt="Process data"
        )

        # Hallucination score should be low
        assert result.scores["hallucination"] < 0.7


class TestEvaluatorInteraction:
    """Test how evaluators interact and aggregate."""

    @pytest.mark.integration
    def test_weighted_aggregation(self, evaluation_pipeline):
        """Test that scores are correctly weighted."""
        code = "def hello(): print('Hello')"

        result = evaluation_pipeline.evaluate(
            code=code,
            test_cases=[],
            prompt="Print hello"
        )

        # Verify weighted calculation
        expected = (
            0.35 * result.scores["correctness"] +
            0.25 * result.scores["safety"] +
            0.20 * result.scores["robustness"] +
            0.20 * result.scores["hallucination"]
        )

        assert abs(result.overall_score - expected) < 0.01
```

#### D. RAG Integration Tests (`test_rag_integration.py`)

```python
"""
Integration tests for RAG system.
Tests indexing, retrieval, and context augmentation.
"""
import pytest
import tempfile
import os
from src.rag.indexer import CodeIndexer
from src.rag.vectorstore import VectorStore
from src.rag.retriever import CodeRetriever


@pytest.fixture
def temp_codebase():
    """Create temporary codebase for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample Python files
        files = {
            "math_utils.py": '''
def add(a, b):
    """Add two numbers."""
    return a + b

def multiply(a, b):
    """Multiply two numbers."""
    return a * b
''',
            "string_utils.py": '''
def reverse_string(s):
    """Reverse a string."""
    return s[::-1]

def capitalize_words(s):
    """Capitalize each word."""
    return s.title()
''',
            "validators.py": '''
import re

def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))
'''
        }

        for filename, content in files.items():
            filepath = os.path.join(tmpdir, filename)
            with open(filepath, "w") as f:
                f.write(content)

        yield tmpdir


class TestRAGPipeline:
    """Test full RAG pipeline."""

    @pytest.mark.integration
    def test_index_and_retrieve(self, temp_codebase):
        """Test indexing codebase and retrieving relevant code."""
        # Index the codebase
        indexer = CodeIndexer()
        chunks = indexer.index_directory(temp_codebase)

        assert len(chunks) > 0

        # Store in vector store
        vectorstore = VectorStore(collection_name="test_collection")
        vectorstore.add_documents(chunks)

        # Retrieve relevant code
        retriever = CodeRetriever(vectorstore)
        results = retriever.retrieve(
            query="function to validate email addresses",
            top_k=3
        )

        assert len(results) > 0
        # Should find the email validator
        assert any("validate_email" in r.content for r in results)

    @pytest.mark.integration
    def test_context_relevance(self, temp_codebase):
        """Test that retrieved context is relevant to query."""
        indexer = CodeIndexer()
        chunks = indexer.index_directory(temp_codebase)

        vectorstore = VectorStore(collection_name="test_relevance")
        vectorstore.add_documents(chunks)

        retriever = CodeRetriever(vectorstore)

        # Query for math operations
        math_results = retriever.retrieve("add two numbers", top_k=2)
        assert any("add" in r.content.lower() for r in math_results)

        # Query for string operations
        string_results = retriever.retrieve("reverse a string", top_k=2)
        assert any("reverse" in r.content.lower() for r in string_results)
```

### 1.4 Running Integration Tests

Add to `pytest.ini`:
```ini
[pytest]
markers =
    integration: marks tests as integration tests (may require API keys)
    slow: marks tests as slow (deselect with '-m "not slow"')
```

Run commands:
```bash
# Run all tests
pytest tests/ -v

# Run only unit tests (fast)
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v -m integration

# Run integration tests with API calls (slow)
pytest tests/integration/ -v -m "integration and slow"

# Skip slow tests
pytest tests/ -v -m "not slow"
```

### 1.5 CI/CD Integration

Update `.github/workflows/ci.yml`:
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Run Unit Tests
        run: pytest tests/unit/ -v --cov=src

      - name: Run Integration Tests (No API)
        run: pytest tests/integration/ -v -m "integration and not slow"

      # Optional: Run slow integration tests with API key
      - name: Run Full Integration Tests
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: pytest tests/integration/ -v -m integration
```

---

## 2. Pass@k Evaluation

### 2.1 Overview

Pass@k is a metric that measures the probability that at least one of k generated code samples passes all test cases. It provides a more robust measure of model capability than single-sample evaluation.

**Formula:**
```
pass@k = 1 - (C(n-c, k) / C(n, k))
```
Where:
- n = total samples generated
- c = number of correct samples
- k = number of samples considered

### 2.2 Implementation Plan

#### A. Update Experiment Configuration (`experiments/config.py`)

```python
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PassAtKConfig:
    """Configuration for pass@k evaluation."""

    # Number of samples to generate per task
    num_samples: int = 10

    # k values to compute pass@k for
    k_values: List[int] = field(default_factory=lambda: [1, 5, 10])

    # Temperature settings for diverse generation
    temperatures: List[float] = field(default_factory=lambda: [0.2, 0.4, 0.6, 0.8])

    # Whether to use different temperatures for diversity
    use_temperature_sampling: bool = True

    # Maximum concurrent generations (to manage API rate limits)
    max_concurrent: int = 3

    # Timeout per generation (seconds)
    generation_timeout: int = 60


@dataclass
class ExperimentConfig:
    """Extended experiment configuration."""

    # Existing config...
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.7
    max_tokens: int = 2048

    # Pass@k configuration
    pass_at_k: Optional[PassAtKConfig] = None

    # Enable pass@k evaluation
    enable_pass_at_k: bool = False
```

#### B. Create Pass@k Evaluator (`src/evaluation/pass_at_k.py`)

```python
"""
Pass@k evaluation for code generation.

Pass@k measures the probability that at least one of k generated
samples passes all test cases, providing a more robust metric
than single-sample evaluation.
"""
import math
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from src.services.claude_client import ClaudeClient
from src.evaluation.correctness import CorrectnessEvaluator


@dataclass
class SampleResult:
    """Result for a single generated sample."""
    sample_id: int
    code: str
    passed: bool
    correctness_score: float
    execution_results: Dict[str, Any]
    temperature: float
    generation_time: float


@dataclass
class PassAtKResult:
    """Results for pass@k evaluation of a single task."""
    task_id: str
    num_samples: int
    num_correct: int
    pass_at_k: Dict[int, float]  # k -> pass@k score
    samples: List[SampleResult]
    best_sample: Optional[SampleResult]
    average_score: float

    @property
    def pass_rate(self) -> float:
        """Simple pass rate (pass@1 approximation)."""
        return self.num_correct / self.num_samples if self.num_samples > 0 else 0.0


class PassAtKEvaluator:
    """
    Evaluator for computing pass@k metrics.

    Generates multiple code samples for each task and computes
    the probability of at least one passing.
    """

    def __init__(
        self,
        client: ClaudeClient,
        num_samples: int = 10,
        k_values: List[int] = None,
        temperatures: List[float] = None,
        max_concurrent: int = 3
    ):
        self.client = client
        self.num_samples = num_samples
        self.k_values = k_values or [1, 5, 10]
        self.temperatures = temperatures or [0.2, 0.4, 0.6, 0.8]
        self.max_concurrent = max_concurrent
        self.correctness_evaluator = CorrectnessEvaluator()

    def compute_pass_at_k(self, n: int, c: int, k: int) -> float:
        """
        Compute pass@k using the unbiased estimator.

        Args:
            n: Total number of samples
            c: Number of correct samples
            k: Number of samples to consider

        Returns:
            pass@k probability
        """
        if n - c < k:
            return 1.0

        # Use logarithms for numerical stability
        # pass@k = 1 - C(n-c, k) / C(n, k)
        # = 1 - prod_{i=0}^{k-1} (n-c-i) / (n-i)

        result = 1.0
        for i in range(k):
            result *= (n - c - i) / (n - i)

        return 1.0 - result

    async def generate_sample(
        self,
        prompt: str,
        temperature: float,
        sample_id: int
    ) -> SampleResult:
        """Generate a single code sample."""
        import time

        start_time = time.time()

        try:
            response = await asyncio.to_thread(
                self.client.generate,
                prompt=prompt,
                temperature=temperature,
                max_tokens=2048
            )

            code = self._extract_code(response.content)
            generation_time = time.time() - start_time

            return SampleResult(
                sample_id=sample_id,
                code=code,
                passed=False,  # Will be set during evaluation
                correctness_score=0.0,
                execution_results={},
                temperature=temperature,
                generation_time=generation_time
            )

        except Exception as e:
            return SampleResult(
                sample_id=sample_id,
                code="",
                passed=False,
                correctness_score=0.0,
                execution_results={"error": str(e)},
                temperature=temperature,
                generation_time=time.time() - start_time
            )

    async def generate_samples(
        self,
        prompt: str,
        num_samples: int
    ) -> List[SampleResult]:
        """Generate multiple code samples with varying temperatures."""
        samples = []

        # Distribute samples across temperatures
        samples_per_temp = num_samples // len(self.temperatures)
        remainder = num_samples % len(self.temperatures)

        tasks = []
        sample_id = 0

        for i, temp in enumerate(self.temperatures):
            count = samples_per_temp + (1 if i < remainder else 0)
            for _ in range(count):
                tasks.append(
                    self.generate_sample(prompt, temp, sample_id)
                )
                sample_id += 1

        # Run with concurrency limit
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def bounded_generate(task):
            async with semaphore:
                return await task

        samples = await asyncio.gather(*[bounded_generate(t) for t in tasks])
        return list(samples)

    def evaluate_samples(
        self,
        samples: List[SampleResult],
        test_cases: List[Dict[str, Any]],
        reference_code: Optional[str] = None
    ) -> List[SampleResult]:
        """Evaluate all samples for correctness."""
        evaluated_samples = []

        for sample in samples:
            if not sample.code:
                evaluated_samples.append(sample)
                continue

            # Run correctness evaluation
            result = self.correctness_evaluator.evaluate(
                code=sample.code,
                test_cases=test_cases,
                reference=reference_code
            )

            sample.passed = result.passed
            sample.correctness_score = result.score
            sample.execution_results = {
                "test_results": result.details.get("test_results", []),
                "syntax_valid": result.details.get("syntax_valid", False),
                "executed": result.details.get("executed", False)
            }

            evaluated_samples.append(sample)

        return evaluated_samples

    async def evaluate_task(
        self,
        task_id: str,
        prompt: str,
        test_cases: List[Dict[str, Any]],
        reference_code: Optional[str] = None
    ) -> PassAtKResult:
        """
        Evaluate a single task with pass@k metrics.

        Args:
            task_id: Unique identifier for the task
            prompt: The code generation prompt
            test_cases: Test cases to verify correctness
            reference_code: Optional reference implementation

        Returns:
            PassAtKResult with all metrics and samples
        """
        # Generate samples
        samples = await self.generate_samples(prompt, self.num_samples)

        # Evaluate samples
        evaluated_samples = self.evaluate_samples(
            samples, test_cases, reference_code
        )

        # Count correct samples
        num_correct = sum(1 for s in evaluated_samples if s.passed)

        # Compute pass@k for each k value
        pass_at_k = {}
        for k in self.k_values:
            if k <= self.num_samples:
                pass_at_k[k] = self.compute_pass_at_k(
                    self.num_samples, num_correct, k
                )

        # Find best sample
        best_sample = max(
            evaluated_samples,
            key=lambda s: s.correctness_score,
            default=None
        )

        # Calculate average score
        avg_score = np.mean([s.correctness_score for s in evaluated_samples])

        return PassAtKResult(
            task_id=task_id,
            num_samples=self.num_samples,
            num_correct=num_correct,
            pass_at_k=pass_at_k,
            samples=evaluated_samples,
            best_sample=best_sample,
            average_score=float(avg_score)
        )

    def _extract_code(self, response: str) -> str:
        """Extract code from markdown response."""
        import re

        # Try to extract from code blocks
        pattern = r"```(?:python)?\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL)

        if matches:
            return matches[0].strip()

        # Return as-is if no code blocks
        return response.strip()


def aggregate_pass_at_k_results(
    results: List[PassAtKResult]
) -> Dict[str, Any]:
    """
    Aggregate pass@k results across multiple tasks.

    Returns:
        Dictionary with aggregated metrics
    """
    if not results:
        return {}

    k_values = list(results[0].pass_at_k.keys())

    aggregated = {
        "num_tasks": len(results),
        "total_samples": sum(r.num_samples for r in results),
        "total_correct": sum(r.num_correct for r in results),
        "average_pass_rate": np.mean([r.pass_rate for r in results]),
        "average_score": np.mean([r.average_score for r in results]),
        "pass_at_k": {}
    }

    # Aggregate pass@k for each k
    for k in k_values:
        scores = [r.pass_at_k.get(k, 0) for r in results]
        aggregated["pass_at_k"][k] = {
            "mean": float(np.mean(scores)),
            "std": float(np.std(scores)),
            "min": float(np.min(scores)),
            "max": float(np.max(scores))
        }

    return aggregated
```

#### C. Update Experiment Runner (`experiments/runner.py`)

```python
# Add to existing runner.py

async def run_pass_at_k_experiment(
    self,
    dataset: List[Dict],
    config: ExperimentConfig
) -> Dict[str, Any]:
    """
    Run pass@k evaluation experiment.

    Args:
        dataset: Benchmark dataset
        config: Experiment configuration

    Returns:
        Complete experiment results with pass@k metrics
    """
    from src.evaluation.pass_at_k import PassAtKEvaluator, aggregate_pass_at_k_results

    evaluator = PassAtKEvaluator(
        client=self.client,
        num_samples=config.pass_at_k.num_samples,
        k_values=config.pass_at_k.k_values,
        temperatures=config.pass_at_k.temperatures,
        max_concurrent=config.pass_at_k.max_concurrent
    )

    results = []

    for i, task in enumerate(dataset):
        print(f"Evaluating task {i+1}/{len(dataset)}: {task['id']}")

        result = await evaluator.evaluate_task(
            task_id=task["id"],
            prompt=task["input_text"],
            test_cases=task.get("metadata", {}).get("test_cases", []),
            reference_code=task.get("reference_output")
        )

        results.append(result)

        # Save checkpoint
        if (i + 1) % 5 == 0:
            self._save_checkpoint(results, config)

    # Aggregate results
    aggregated = aggregate_pass_at_k_results(results)

    return {
        "config": config.__dict__,
        "task_results": [self._serialize_result(r) for r in results],
        "aggregated": aggregated
    }
```

### 2.3 Usage Example

```python
import asyncio
from experiments.runner import ExperimentRunner
from experiments.config import ExperimentConfig, PassAtKConfig

# Configure pass@k experiment
config = ExperimentConfig(
    model="claude-sonnet-4-20250514",
    enable_pass_at_k=True,
    pass_at_k=PassAtKConfig(
        num_samples=10,
        k_values=[1, 5, 10],
        temperatures=[0.2, 0.4, 0.6, 0.8],
        max_concurrent=3
    )
)

# Run experiment
runner = ExperimentRunner(config)
results = asyncio.run(runner.run_pass_at_k_experiment(dataset, config))

# Results include:
# - pass@1: Probability of first sample being correct
# - pass@5: Probability of at least 1 of 5 samples correct
# - pass@10: Probability of at least 1 of 10 samples correct
print(f"Pass@1: {results['aggregated']['pass_at_k'][1]['mean']:.2%}")
print(f"Pass@5: {results['aggregated']['pass_at_k'][5]['mean']:.2%}")
print(f"Pass@10: {results['aggregated']['pass_at_k'][10]['mean']:.2%}")
```

### 2.4 Expected Output

```
Pass@k Evaluation Results
=========================
Tasks Evaluated: 27
Samples per Task: 10
Total Samples: 270

Pass@k Metrics:
  pass@1:  78.5% (±12.3%)
  pass@5:  94.2% (±6.8%)
  pass@10: 98.1% (±3.2%)

Per-Category Results:
  Algorithms:      pass@1=82%, pass@5=96%, pass@10=99%
  Data Structures: pass@1=75%, pass@5=92%, pass@10=97%
  String Manip:    pass@1=85%, pass@5=98%, pass@10=100%
  File/API:        pass@1=70%, pass@5=88%, pass@10=95%
  Error Handling:  pass@1=72%, pass@5=90%, pass@10=96%
```

---

## 3. Multi-Model Comparison (Claude Models)

### 3.1 Overview

Since you have an Anthropic API key, you can compare different Claude models:

| Model | Model ID | Strengths | Cost (per 1M tokens) |
|-------|----------|-----------|---------------------|
| **Claude Opus 4** | `claude-opus-4-20250514` | Highest capability, best reasoning | Input: $15, Output: $75 |
| **Claude Sonnet 4** | `claude-sonnet-4-20250514` | Balanced performance/cost | Input: $3, Output: $15 |
| **Claude Haiku 3.5** | `claude-3-5-haiku-20241022` | Fastest, most economical | Input: $0.80, Output: $4 |

### 3.2 Implementation Plan

#### A. Model Configuration (`experiments/models.py`)

```python
"""
Multi-model configuration for comparative experiments.
"""
from dataclasses import dataclass
from typing import Dict, Any, List
from enum import Enum


class ClaudeModel(Enum):
    """Available Claude models for comparison."""

    OPUS_4 = "claude-opus-4-20250514"
    SONNET_4 = "claude-sonnet-4-20250514"
    HAIKU_3_5 = "claude-3-5-haiku-20241022"

    # Legacy models (if needed for comparison)
    SONNET_3_5 = "claude-3-5-sonnet-20241022"
    HAIKU_3 = "claude-3-haiku-20240307"


@dataclass
class ModelConfig:
    """Configuration for a specific model."""

    model_id: str
    display_name: str

    # Pricing (per 1M tokens)
    input_cost: float
    output_cost: float

    # Performance characteristics
    max_tokens: int = 4096
    recommended_temperature: float = 0.7

    # Rate limits (requests per minute)
    rate_limit_rpm: int = 50

    # Expected characteristics
    expected_latency_ms: int = 2000  # Approximate

    @property
    def cost_per_1k_tokens(self) -> Dict[str, float]:
        """Cost per 1K tokens for easier calculation."""
        return {
            "input": self.input_cost / 1000,
            "output": self.output_cost / 1000
        }


# Model configurations
MODEL_CONFIGS: Dict[ClaudeModel, ModelConfig] = {
    ClaudeModel.OPUS_4: ModelConfig(
        model_id="claude-opus-4-20250514",
        display_name="Claude Opus 4",
        input_cost=15.0,
        output_cost=75.0,
        max_tokens=4096,
        recommended_temperature=0.7,
        rate_limit_rpm=20,
        expected_latency_ms=5000
    ),
    ClaudeModel.SONNET_4: ModelConfig(
        model_id="claude-sonnet-4-20250514",
        display_name="Claude Sonnet 4",
        input_cost=3.0,
        output_cost=15.0,
        max_tokens=4096,
        recommended_temperature=0.7,
        rate_limit_rpm=50,
        expected_latency_ms=2000
    ),
    ClaudeModel.HAIKU_3_5: ModelConfig(
        model_id="claude-3-5-haiku-20241022",
        display_name="Claude 3.5 Haiku",
        input_cost=0.80,
        output_cost=4.0,
        max_tokens=4096,
        recommended_temperature=0.7,
        rate_limit_rpm=100,
        expected_latency_ms=500
    ),
}


def get_model_config(model: ClaudeModel) -> ModelConfig:
    """Get configuration for a specific model."""
    return MODEL_CONFIGS[model]


def get_all_models() -> List[ClaudeModel]:
    """Get list of all available models."""
    return list(ClaudeModel)


def estimate_experiment_cost(
    model: ClaudeModel,
    num_tasks: int,
    avg_input_tokens: int = 500,
    avg_output_tokens: int = 1000,
    samples_per_task: int = 1
) -> Dict[str, float]:
    """
    Estimate cost for running an experiment.

    Args:
        model: The Claude model to use
        num_tasks: Number of tasks in benchmark
        avg_input_tokens: Average input tokens per request
        avg_output_tokens: Average output tokens per request
        samples_per_task: Number of samples per task (for pass@k)

    Returns:
        Cost breakdown dictionary
    """
    config = get_model_config(model)

    total_requests = num_tasks * samples_per_task
    total_input_tokens = total_requests * avg_input_tokens
    total_output_tokens = total_requests * avg_output_tokens

    input_cost = (total_input_tokens / 1_000_000) * config.input_cost
    output_cost = (total_output_tokens / 1_000_000) * config.output_cost

    return {
        "model": config.display_name,
        "total_requests": total_requests,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "input_cost_usd": round(input_cost, 4),
        "output_cost_usd": round(output_cost, 4),
        "total_cost_usd": round(input_cost + output_cost, 4),
        "estimated_time_minutes": round(
            (total_requests / config.rate_limit_rpm) +
            (total_requests * config.expected_latency_ms / 60000),
            1
        )
    }
```

#### B. Multi-Model Experiment Runner (`experiments/multi_model_runner.py`)

```python
"""
Multi-model comparison experiment runner.

Runs the same benchmark across multiple Claude models
and generates comparative analysis.
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from src.services.claude_client import ClaudeClient
from src.evaluation.metrics import EvaluationPipeline
from experiments.models import (
    ClaudeModel,
    ModelConfig,
    get_model_config,
    estimate_experiment_cost
)


@dataclass
class ModelExperimentResult:
    """Results for a single model's experiment run."""

    model: str
    model_id: str

    # Performance metrics
    pass_rate: float
    average_score: float

    # Per-evaluator scores
    correctness_score: float
    robustness_score: float
    safety_score: float
    hallucination_score: float

    # Cost metrics
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float

    # Time metrics
    total_time_seconds: float
    average_latency_ms: float

    # Detailed results
    task_results: List[Dict[str, Any]]


@dataclass
class MultiModelComparisonResult:
    """Aggregated results comparing multiple models."""

    experiment_id: str
    timestamp: str
    num_tasks: int

    # Per-model results
    model_results: Dict[str, ModelExperimentResult]

    # Comparative analysis
    best_model_by_score: str
    best_model_by_cost: str
    best_model_by_speed: str

    # Rankings
    score_ranking: List[str]
    cost_efficiency_ranking: List[str]  # score per dollar

    # Statistical comparison
    score_comparison: Dict[str, Dict[str, float]]


class MultiModelExperimentRunner:
    """
    Runs comparative experiments across multiple Claude models.
    """

    def __init__(
        self,
        models: List[ClaudeModel] = None,
        output_dir: str = "experiments/results/multi_model"
    ):
        self.models = models or [
            ClaudeModel.HAIKU_3_5,
            ClaudeModel.SONNET_4,
            # ClaudeModel.OPUS_4,  # Uncomment if budget allows
        ]
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def estimate_total_cost(
        self,
        num_tasks: int,
        samples_per_task: int = 1
    ) -> Dict[str, Any]:
        """
        Estimate total cost for running all models.

        Returns cost breakdown per model and total.
        """
        estimates = {}
        total_cost = 0.0
        total_time = 0.0

        for model in self.models:
            estimate = estimate_experiment_cost(
                model=model,
                num_tasks=num_tasks,
                samples_per_task=samples_per_task
            )
            estimates[model.value] = estimate
            total_cost += estimate["total_cost_usd"]
            total_time += estimate["estimated_time_minutes"]

        return {
            "per_model": estimates,
            "total_cost_usd": round(total_cost, 2),
            "total_time_minutes": round(total_time, 1)
        }

    async def run_single_model_experiment(
        self,
        model: ClaudeModel,
        dataset: List[Dict],
        evaluation_pipeline: EvaluationPipeline
    ) -> ModelExperimentResult:
        """Run experiment for a single model."""
        import time

        config = get_model_config(model)
        client = ClaudeClient(model=config.model_id)

        task_results = []
        total_input_tokens = 0
        total_output_tokens = 0
        latencies = []

        start_time = time.time()

        for i, task in enumerate(dataset):
            print(f"  [{config.display_name}] Task {i+1}/{len(dataset)}: {task['id']}")

            task_start = time.time()

            try:
                # Generate code
                response = client.generate(
                    prompt=task["input_text"],
                    temperature=config.recommended_temperature,
                    max_tokens=config.max_tokens
                )

                task_latency = (time.time() - task_start) * 1000
                latencies.append(task_latency)

                # Track tokens
                total_input_tokens += response.usage.get("input_tokens", 0)
                total_output_tokens += response.usage.get("output_tokens", 0)

                # Extract and evaluate code
                code = self._extract_code(response.content)

                eval_result = evaluation_pipeline.evaluate(
                    code=code,
                    test_cases=task.get("metadata", {}).get("test_cases", []),
                    prompt=task["input_text"]
                )

                task_results.append({
                    "task_id": task["id"],
                    "passed": eval_result.passed,
                    "overall_score": eval_result.overall_score,
                    "scores": eval_result.scores,
                    "latency_ms": task_latency
                })

            except Exception as e:
                print(f"    Error: {e}")
                task_results.append({
                    "task_id": task["id"],
                    "passed": False,
                    "overall_score": 0.0,
                    "scores": {},
                    "error": str(e)
                })

            # Rate limiting
            await asyncio.sleep(60 / config.rate_limit_rpm)

        total_time = time.time() - start_time

        # Calculate aggregated metrics
        passed_tasks = [r for r in task_results if r.get("passed", False)]

        avg_scores = {
            "correctness": 0.0,
            "robustness": 0.0,
            "safety": 0.0,
            "hallucination": 0.0
        }

        for evaluator in avg_scores.keys():
            scores = [r["scores"].get(evaluator, 0) for r in task_results if r.get("scores")]
            avg_scores[evaluator] = sum(scores) / len(scores) if scores else 0.0

        # Calculate cost
        total_cost = (
            (total_input_tokens / 1_000_000) * config.input_cost +
            (total_output_tokens / 1_000_000) * config.output_cost
        )

        return ModelExperimentResult(
            model=config.display_name,
            model_id=config.model_id,
            pass_rate=len(passed_tasks) / len(task_results) if task_results else 0.0,
            average_score=sum(r.get("overall_score", 0) for r in task_results) / len(task_results),
            correctness_score=avg_scores["correctness"],
            robustness_score=avg_scores["robustness"],
            safety_score=avg_scores["safety"],
            hallucination_score=avg_scores["hallucination"],
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_cost_usd=round(total_cost, 4),
            total_time_seconds=total_time,
            average_latency_ms=sum(latencies) / len(latencies) if latencies else 0,
            task_results=task_results
        )

    async def run_comparison(
        self,
        dataset: List[Dict]
    ) -> MultiModelComparisonResult:
        """
        Run full comparison across all configured models.

        Args:
            dataset: Benchmark dataset

        Returns:
            Complete comparison results
        """
        from src.evaluation.correctness import CorrectnessEvaluator
        from src.evaluation.robustness import RobustnessEvaluator
        from src.evaluation.safety import SafetyEvaluator
        from src.evaluation.hallucination import HallucinationEvaluator
        from src.evaluation.metrics import EvaluationPipeline

        # Create evaluation pipeline
        pipeline = EvaluationPipeline(
            evaluators=[
                CorrectnessEvaluator(),
                RobustnessEvaluator(),
                SafetyEvaluator(),
                HallucinationEvaluator()
            ]
        )

        experiment_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_results = {}

        print(f"\n{'='*60}")
        print(f"Multi-Model Comparison Experiment: {experiment_id}")
        print(f"Models: {[m.value for m in self.models]}")
        print(f"Tasks: {len(dataset)}")
        print(f"{'='*60}\n")

        # Run each model
        for model in self.models:
            print(f"\nRunning {get_model_config(model).display_name}...")
            result = await self.run_single_model_experiment(
                model=model,
                dataset=dataset,
                evaluation_pipeline=pipeline
            )
            model_results[model.value] = result

            print(f"  Pass Rate: {result.pass_rate:.1%}")
            print(f"  Avg Score: {result.average_score:.3f}")
            print(f"  Cost: ${result.total_cost_usd:.4f}")
            print(f"  Time: {result.total_time_seconds:.1f}s")

        # Analyze results
        comparison = self._analyze_comparison(model_results)

        result = MultiModelComparisonResult(
            experiment_id=experiment_id,
            timestamp=datetime.now().isoformat(),
            num_tasks=len(dataset),
            model_results=model_results,
            **comparison
        )

        # Save results
        self._save_results(result)

        return result

    def _analyze_comparison(
        self,
        model_results: Dict[str, ModelExperimentResult]
    ) -> Dict[str, Any]:
        """Analyze and compare model results."""

        # Find best models
        best_by_score = max(
            model_results.items(),
            key=lambda x: x[1].average_score
        )[0]

        best_by_cost = min(
            model_results.items(),
            key=lambda x: x[1].total_cost_usd
        )[0]

        best_by_speed = min(
            model_results.items(),
            key=lambda x: x[1].average_latency_ms
        )[0]

        # Rankings
        score_ranking = sorted(
            model_results.keys(),
            key=lambda x: model_results[x].average_score,
            reverse=True
        )

        # Cost efficiency: score per dollar
        cost_efficiency = {
            model: result.average_score / max(result.total_cost_usd, 0.0001)
            for model, result in model_results.items()
        }
        cost_efficiency_ranking = sorted(
            cost_efficiency.keys(),
            key=lambda x: cost_efficiency[x],
            reverse=True
        )

        # Score comparison matrix
        score_comparison = {}
        for model, result in model_results.items():
            score_comparison[model] = {
                "overall": result.average_score,
                "correctness": result.correctness_score,
                "robustness": result.robustness_score,
                "safety": result.safety_score,
                "hallucination": result.hallucination_score,
                "pass_rate": result.pass_rate,
                "cost_usd": result.total_cost_usd,
                "latency_ms": result.average_latency_ms,
                "cost_efficiency": cost_efficiency[model]
            }

        return {
            "best_model_by_score": best_by_score,
            "best_model_by_cost": best_by_cost,
            "best_model_by_speed": best_by_speed,
            "score_ranking": score_ranking,
            "cost_efficiency_ranking": cost_efficiency_ranking,
            "score_comparison": score_comparison
        }

    def _extract_code(self, response: str) -> str:
        """Extract code from response."""
        import re
        pattern = r"```(?:python)?\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL)
        return matches[0].strip() if matches else response.strip()

    def _save_results(self, result: MultiModelComparisonResult):
        """Save results to disk."""
        output_path = self.output_dir / f"comparison_{result.experiment_id}"
        output_path.mkdir(exist_ok=True)

        # Save full results
        with open(output_path / "results.json", "w") as f:
            json.dump(asdict(result), f, indent=2, default=str)

        # Save summary
        summary = {
            "experiment_id": result.experiment_id,
            "num_tasks": result.num_tasks,
            "best_model_by_score": result.best_model_by_score,
            "best_model_by_cost": result.best_model_by_cost,
            "score_ranking": result.score_ranking,
            "comparison": result.score_comparison
        }

        with open(output_path / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\nResults saved to: {output_path}")
```

#### C. Visualization (`experiments/visualize_comparison.py`)

```python
"""
Visualization for multi-model comparison results.
"""
import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np


def plot_model_comparison(results_path: str):
    """Generate comparison visualizations."""

    with open(results_path) as f:
        results = json.load(f)

    comparison = results["score_comparison"]
    models = list(comparison.keys())

    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Multi-Model Comparison Results", fontsize=14, fontweight='bold')

    # 1. Overall Score Comparison
    ax1 = axes[0, 0]
    scores = [comparison[m]["overall"] for m in models]
    colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(models)))
    bars = ax1.bar(models, scores, color=colors)
    ax1.set_ylabel("Average Score")
    ax1.set_title("Overall Performance")
    ax1.set_ylim(0, 1)
    for bar, score in zip(bars, scores):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{score:.3f}', ha='center', va='bottom', fontsize=10)

    # 2. Per-Evaluator Comparison
    ax2 = axes[0, 1]
    evaluators = ["correctness", "robustness", "safety", "hallucination"]
    x = np.arange(len(evaluators))
    width = 0.25

    for i, model in enumerate(models):
        scores = [comparison[model][e] for e in evaluators]
        ax2.bar(x + i*width, scores, width, label=model, color=colors[i])

    ax2.set_ylabel("Score")
    ax2.set_title("Per-Evaluator Comparison")
    ax2.set_xticks(x + width)
    ax2.set_xticklabels([e.capitalize() for e in evaluators])
    ax2.legend()
    ax2.set_ylim(0, 1.1)

    # 3. Cost vs Performance
    ax3 = axes[1, 0]
    costs = [comparison[m]["cost_usd"] for m in models]
    scores = [comparison[m]["overall"] for m in models]

    scatter = ax3.scatter(costs, scores, s=200, c=colors, edgecolors='black')
    for i, model in enumerate(models):
        ax3.annotate(model, (costs[i], scores[i]),
                    textcoords="offset points", xytext=(0,10), ha='center')

    ax3.set_xlabel("Cost (USD)")
    ax3.set_ylabel("Average Score")
    ax3.set_title("Cost vs Performance Trade-off")

    # 4. Latency Comparison
    ax4 = axes[1, 1]
    latencies = [comparison[m]["latency_ms"] for m in models]
    bars = ax4.bar(models, latencies, color=colors)
    ax4.set_ylabel("Average Latency (ms)")
    ax4.set_title("Response Latency")
    for bar, lat in zip(bars, latencies):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 20,
                f'{lat:.0f}ms', ha='center', va='bottom', fontsize=10)

    plt.tight_layout()

    # Save figure
    output_path = Path(results_path).parent / "comparison_plots.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"Saved comparison plots to: {output_path}")


def generate_comparison_table(results_path: str) -> str:
    """Generate markdown comparison table."""

    with open(results_path) as f:
        results = json.load(f)

    comparison = results["score_comparison"]

    # Build markdown table
    table = """
## Model Comparison Results

| Metric | """ + " | ".join(comparison.keys()) + """ |
|--------|""" + "|".join(["--------"] * len(comparison)) + """|
"""

    metrics = [
        ("Overall Score", "overall", "{:.3f}"),
        ("Pass Rate", "pass_rate", "{:.1%}"),
        ("Correctness", "correctness", "{:.3f}"),
        ("Robustness", "robustness", "{:.3f}"),
        ("Safety", "safety", "{:.3f}"),
        ("Hallucination", "hallucination", "{:.3f}"),
        ("Cost (USD)", "cost_usd", "${:.4f}"),
        ("Latency (ms)", "latency_ms", "{:.0f}"),
        ("Cost Efficiency", "cost_efficiency", "{:.1f}"),
    ]

    for label, key, fmt in metrics:
        row = f"| {label} |"
        for model in comparison.keys():
            value = comparison[model][key]
            row += f" {fmt.format(value)} |"
        table += row + "\n"

    # Add rankings
    table += f"""
### Rankings

- **Best by Score:** {results['best_model_by_score']}
- **Best by Cost:** {results['best_model_by_cost']}
- **Best by Speed:** {results['best_model_by_speed']}

**Score Ranking:** {' > '.join(results['score_ranking'])}

**Cost Efficiency Ranking:** {' > '.join(results['cost_efficiency_ranking'])}
"""

    return table
```

### 3.3 Usage Example

```python
import asyncio
from experiments.multi_model_runner import MultiModelExperimentRunner
from experiments.models import ClaudeModel

# Configure models to compare
runner = MultiModelExperimentRunner(
    models=[
        ClaudeModel.HAIKU_3_5,   # Fast & cheap
        ClaudeModel.SONNET_4,    # Balanced
        # ClaudeModel.OPUS_4,    # Best quality (expensive)
    ]
)

# Estimate costs before running
estimates = runner.estimate_total_cost(num_tasks=27, samples_per_task=1)
print(f"Estimated total cost: ${estimates['total_cost_usd']:.2f}")
print(f"Estimated time: {estimates['total_time_minutes']:.0f} minutes")

# Load dataset
with open("data/evaluation/benchmark_dataset.json") as f:
    dataset = json.load(f)

# Run comparison
results = asyncio.run(runner.run_comparison(dataset))

# Generate visualizations
from experiments.visualize_comparison import plot_model_comparison, generate_comparison_table

plot_model_comparison("experiments/results/multi_model/comparison_xxx/results.json")
table = generate_comparison_table("experiments/results/multi_model/comparison_xxx/results.json")
print(table)
```

### 3.4 Expected Results

```
Multi-Model Comparison Results
==============================

| Metric          | Haiku 3.5 | Sonnet 4 | Opus 4   |
|-----------------|-----------|----------|----------|
| Overall Score   | 0.842     | 0.905    | 0.932    |
| Pass Rate       | 85.2%     | 92.6%    | 96.3%    |
| Correctness     | 0.721     | 0.778    | 0.845    |
| Robustness      | 0.891     | 0.926    | 0.951    |
| Safety          | 0.982     | 0.994    | 0.998    |
| Hallucination   | 0.976     | 0.994    | 0.996    |
| Cost (USD)      | $0.0312   | $0.1847  | $0.9235  |
| Latency (ms)    | 423       | 1847     | 4523     |
| Cost Efficiency | 27.0      | 4.9      | 1.0      |

Rankings:
- Best by Score: Opus 4
- Best by Cost: Haiku 3.5
- Best by Speed: Haiku 3.5
- Best Cost Efficiency: Haiku 3.5 > Sonnet 4 > Opus 4
```

---

## 4. Implementation Priority & Cost Estimates

### Priority Order

| Enhancement | Priority | Effort | Cost Impact |
|-------------|----------|--------|-------------|
| Integration Tests | High | Medium | $0 (no API calls) |
| Multi-Model Comparison | Medium | Medium | ~$1-2 per run |
| Pass@k Evaluation | Medium | High | ~$5-10 per run (10 samples) |

### Estimated API Costs (27 tasks)

| Configuration | Haiku | Sonnet | Opus |
|---------------|-------|--------|------|
| Single sample | $0.03 | $0.18 | $0.92 |
| Pass@5 | $0.15 | $0.92 | $4.60 |
| Pass@10 | $0.31 | $1.85 | $9.20 |

### Recommended Approach

1. **Phase 1:** Implement integration tests (no cost)
2. **Phase 2:** Implement multi-model comparison with Haiku + Sonnet
3. **Phase 3:** Add Pass@k with k=5 using Sonnet only
4. **Phase 4 (Optional):** Full Pass@k with Opus if budget allows

---

## 5. File Structure After Implementation

```
project/
├── src/
│   └── evaluation/
│       └── pass_at_k.py          # NEW: Pass@k evaluator
├── tests/
│   ├── unit/                     # Existing unit tests
│   └── integration/              # NEW: Integration tests
│       ├── conftest.py
│       ├── test_api_endpoints.py
│       ├── test_capability_pipeline.py
│       ├── test_evaluation_pipeline.py
│       ├── test_rag_integration.py
│       └── test_agent_routing.py
├── experiments/
│   ├── models.py                 # NEW: Model configurations
│   ├── multi_model_runner.py     # NEW: Multi-model comparison
│   ├── visualize_comparison.py   # NEW: Comparison visualizations
│   └── results/
│       └── multi_model/          # NEW: Comparison results
└── doc/
    └── implementation_plan_enhancements.md  # This document
```

---

## 6. Next Steps

1. Review this implementation plan
2. Decide which enhancements to prioritize
3. Estimate your API budget for experiments
4. Begin implementation starting with integration tests (free)
5. Run multi-model comparison with Haiku + Sonnet first (cheapest)
6. Expand to Pass@k evaluation based on results and budget
