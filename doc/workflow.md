# SE-Agent Project Workflow & Architecture

## Overview

**SE-Agent** is an AI-powered Software Engineering Assistant that uses Anthropic's Claude API to help developers with:
- Code generation from natural language
- Test generation (pytest, unittest)
- Code review (security, performance, quality)
- Requirements analysis
- Documentation generation

It also includes a **research component** for evaluating LLM-generated code quality.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND (React + TypeScript) / CLI                        │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│  FASTAPI (REST API on port 8000)                           │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│  AGENT CONTROLLER + INTENT ROUTER                                 │
│  (Routes requests, manages conversation history)                  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│  5 CAPABILITIES                                                   │
│  CodeGen │ TestGen │ Review │ Requirements │ Documentation       │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│  RAG LAYER (ChromaDB + Sentence Transformers)                     │
│  (Semantic code search for context augmentation)                  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│  CLAUDE CLIENT (API wrapper with cost tracking)                   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│  EVALUATION FRAMEWORK                                             │
│  Correctness │ Robustness │ Safety │ Hallucination                │
└─────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
project/
├── frontend/                    # React TypeScript UI
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── src/
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Configuration management
│   ├── agent/                  # Orchestration & routing
│   ├── capabilities/           # 5 core modules
│   ├── evaluation/             # Quality assessment (4 evaluators)
│   ├── rag/                    # Retrieval augmented generation
│   ├── services/               # Claude API client
│   └── ui/                     # CLI interface
├── tests/                       # Test directory
├── docker-compose.yml          # 3-service orchestration
└── requirements.txt            # Dependencies
```

---

## Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **AgentController** | `src/agent/controller.py` | Main orchestrator, routes requests |
| **IntentRouter** | `src/agent/router.py` | Classifies user intent (rule + LLM-based) |
| **ClaudeClient** | `src/services/claude_client.py` | API wrapper with cost tracking |
| **RAG System** | `src/rag/` | Code indexing & semantic search |
| **Evaluators** | `src/evaluation/` | 4 quality metrics for LLM output |
| **Capabilities** | `src/capabilities/` | 5 specialized modules |

---

## Data Flow

```
User Input
    ↓
FastAPI Endpoint → Request Validation
    ↓
AgentController.process()
    ├─→ IntentRouter.classify() [Rule-based + LLM]
    ├─→ RAG Retrieval (if enabled)
    └─→ Execute Capability
        ├─→ Format Prompt
        ├─→ ClaudeClient.generate()
        └─→ Post-process Result
    ↓
Return Response
    ├─→ Result
    ├─→ Task Type
    ├─→ Confidence Score
    ├─→ Usage Stats
    └─→ Error (if failed)
```

---

## Agent Orchestration

### AgentController (`src/agent/controller.py`)

The main orchestrator that:
- Routes user requests to appropriate capabilities
- Manages conversation history (configurable max_history)
- Integrates RAG for context retrieval
- Tracks API usage and costs
- Handles multi-turn conversations

### IntentRouter (`src/agent/router.py`)

Dual-layer classification:
1. **Rule-based classification** - Keywords matching against 5 capability types
2. **LLM-based classification** - Uses Claude Haiku (fast model) for ambiguous cases
3. **Combination logic** - Boosts confidence when both methods agree

**Intent Keywords:**
- Code Generation: generate, create, write, implement, build, code, function, class
- Test Generation: test, testing, unittest, pytest, coverage
- Code Review: review, check, analyze, find bugs, security, vulnerability
- Requirements: requirements, specs, specification, user story, feature
- Documentation: document, docstring, readme, explain, describe, api doc

---

## Capabilities

All inherit from `BaseCapability`:

### 1. CodeGenerationCapability
- Generates code from natural language requirements
- Post-processes markdown code blocks
- Supports context from RAG
- Returns largest code block if multiple found

### 2. TestGenerationCapability
- Creates unit tests from code snippets
- Supports multiple frameworks (pytest, unittest)
- Extracts code blocks from LLM response
- Can combine multiple test blocks

### 3. CodeReviewCapability
- Reviews code for bugs, security, quality, performance
- Specialized methods: `review_for_security()`, `review_for_performance()`
- Focus parameter for targeted reviews
- Structured issue tracking (severity, category, line number)

### 4. RequirementsCapability
- Analyzes and structures requirements
- Generates specifications from descriptions

### 5. DocumentationCapability
- Generates API docs, README, inline documentation
- Supports different doc types (docstrings, API docs, tutorials)

---

## RAG System

Three-component architecture:

### 1. CodeIndexer (`src/rag/indexer.py`)
- AST-based Python parser using `ast` module
- Extracts: classes, functions, methods, imports, docstrings
- Handles Python syntax errors gracefully with fallback to line-based chunking
- Supports multiple languages (Python, JavaScript, TypeScript, Java, Go, Rust, Ruby, PHP, C/C++)
- Generates unique chunk IDs with MD5 hashing
- Tracks: file_path, language, chunk_type, start_line, end_line, docstring, signature
- Ignores: `__pycache__`, `.git`, `node_modules`, `venv`, `dist`, `build`, `.pytest_cache`

### 2. ChromaVectorStore (`src/rag/vectorstore.py`)
- Wraps ChromaDB for persistent vector storage
- Uses sentence-transformers for embeddings (all-MiniLM-L6-v2)
- Supports local persistence or client mode connection
- Methods: `add_chunks()`, `search()`, `search_functions()`, `search_classes()`, `clear()`

### 3. CodeRetriever (`src/rag/retriever.py`)
- Orchestrates indexing and semantic search
- **RetrievalConfig:**
  - initial_k: 20 (fetch more for re-ranking)
  - final_n: 5 (return top 5)
  - similarity_threshold: 0.3
  - max_context_tokens: 4000
- **Specialized retrieval methods:**
  - `retrieve_for_code_generation()`
  - `retrieve_for_test_generation()` (prioritizes test files)
  - `retrieve_for_code_review()`
- **Re-ranking logic:**
  - Boosts exact name matches (1.3x)
  - Boosts functions/methods (1.1x)
  - Boosts chunks with docstrings (1.1x)
  - Penalizes very long chunks (0.9x)

---

## Claude API Client

### ClaudeClient (`src/services/claude_client.py`)

Wrapper around Anthropic API:
- Cost tracking with daily budget enforcement
- Retry logic with exponential backoff (3 retries)
- Handles RateLimitError, APIConnectionError, APIError
- Token-based pricing calculation
- Usage statistics tracking
- Models: `claude-sonnet-4-20250514`, `claude-3-haiku-20240307`

### CostTracker
- Daily budget limits ($10.00 default)
- Daily reset at midnight
- Usage history maintenance
- Estimated cost checking

---

## Evaluation Framework

Four independent evaluators for LLM code quality:

### 1. CorrectnessEvaluator
- **Checks:**
  1. Syntax validity (AST parsing)
  2. Execution success (subprocess with timeout)
  3. Test pass rate (if test cases provided)
  4. Semantic similarity (Jaccard index on tokens)
- **Scores:** Returns average of all checks
- **Safety:** Runs code in isolated subprocess with timeout (default 10s)
- **Output:** Syntax errors, execution errors, test failures

### 2. RobustnessEvaluator
- **Tests:**
  1. Output quality (non-empty, not truncated, repetition check)
  2. Consistency across prompt variations (6 variations):
     - original, lowercase, uppercase, extra_whitespace, polite, terse
  3. Edge case handling (null/None, empty input, error handling)
  4. Perturbation sensitivity (4 small changes)
- **Scoring:** Average of all components
- **Methods:** Token-based similarity (Jaccard), trigram repetition detection

### 3. SafetyEvaluator
- **Multiple detection layers:**
  1. **Bandit analysis** (bandit CLI tool if available)
  2. **Custom pattern matching** (11 vulnerability types):
     - SQL injection, command injection, hardcoded secrets, XSS
     - Path traversal, insecure deserialization, weak crypto
     - Insecure random, debug code, insecure SSL
  3. **AST analysis:**
     - Dangerous imports (pickle, subprocess, os, eval, exec)
     - Dangerous function calls (eval, exec, compile, getattr)
  4. **Anti-pattern detection:**
     - Assert for security, wildcard imports, bare except
     - Mutable default arguments, unsafe input()
- **Scoring:** 1.0 - sum of severity weights (capped at 1.0)
- **Severity mapping:** CRITICAL (0.4), HIGH (0.25), MEDIUM (0.15), LOW (0.1), INFO (0.05)

### 4. HallucinationDetector
- **Detects fabricated/invalid code elements:**
  1. **Invalid imports** (1500+ stdlib modules tracked for Python 3.11)
  2. **Fake API calls** (pattern matching for suspicious methods)
  3. **Incorrect function signatures** (validates builtin function signatures)
  4. **Hallucination patterns** (auto_*, smart_*, from_any, to_any)
- **Validation strategies:**
  - Known fake modules list (utils.helpers, common.utils, etc.)
  - `importlib.util.find_spec()` for installed packages
  - Plausible module name checking (regex patterns)
  - Strict vs permissive modes
- **Scoring:** Based on issue severity weights

### Evaluation Pipeline (`src/evaluation/metrics.py`)
- **EvaluationPipeline** - Main orchestrator running all evaluators
- **TaskEvaluationResult** - Results for single task with overall score
- **EvaluationReport** - Batch results with summary statistics
- **Configurable thresholds:**
  - Correctness: 0.7
  - Robustness: 0.6
  - Safety: 0.7
  - Hallucination: 0.7
- **Weighted scoring:**
  - Correctness: 35%
  - Robustness: 20%
  - Safety: 25%
  - Hallucination: 20%

---

## API Endpoints

FastAPI Application with CORS configured for localhost frontend:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check, returns capabilities |
| `/generate` | POST | Auto-detect task type and generate |
| `/code/generate` | POST | Generate code from requirements |
| `/tests/generate` | POST | Generate tests for code |
| `/code/review` | POST | Review code for issues |
| `/usage` | GET | API usage statistics |
| `/history` | GET | Get conversation history |
| `/history` | DELETE | Clear conversation |
| `/rag/index` | POST | Index a codebase |
| `/rag/stats` | GET | RAG system statistics |
| `/rag/search` | POST | Semantic code search |

### Request/Response Models
- **GenerateRequest:** prompt, task_type, context, language, options
- **CodeGenRequest:** requirements, language, context
- **TestGenRequest:** code, language, framework
- **CodeReviewRequest:** code, language, focus
- **IndexRequest:** directory, extensions
- **SearchRequest:** query, n_results, language

---

## Configuration

### AnthropicConfig
- api_key (from `ANTHROPIC_API_KEY` env var)
- default_model: `claude-sonnet-4-20250514`
- fast_model: `claude-3-haiku-20240307`
- max_tokens: 4096, temperature: 0.7

### ChromaConfig
- host: localhost, port: 8001
- collection_name: codebase

### CostConfig
- daily_budget: $10.00
- pricing per 1K tokens:
  - Sonnet: input $0.003, output $0.015
  - Haiku: input $0.00025, output $0.00125

### AppConfig
- debug: false, log_level: INFO
- host: 0.0.0.0, api_port: 8000

---

## Docker Deployment

3-service orchestration via `docker-compose.yml`:

### 1. frontend (port 3000)
- Nginx-based React build
- Depends on se-agent

### 2. se-agent (port 8000)
- FastAPI backend
- Connects to ChromaDB
- Environment variables: `ANTHROPIC_API_KEY`, `CHROMA_HOST`, `LOG_LEVEL`
- Volumes: `./data`, `app-logs`

### 3. chromadb (port 8001)
- Latest ChromaDB image
- Persistent storage: `chroma-data` volume
- Health check enabled
- Environment: `IS_PERSISTENT=TRUE`, `ANONYMIZED_TELEMETRY=FALSE`

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, Python 3.11+, uvicorn |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, ShadCN UI |
| **Vector DB** | ChromaDB |
| **LLM** | Anthropic Claude (Sonnet & Haiku) |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) |
| **Code Parsing** | tree-sitter, pygments, AST |
| **Security** | bandit |
| **CLI** | Click, Rich |

---

## Implementation Status

| Component | Status |
|-----------|--------|
| Agent orchestration | Complete |
| 5 Capability modules | Complete |
| RAG system | Complete |
| Claude API client | Complete |
| 4 Evaluators | Complete |
| FastAPI endpoints | Complete |
| Docker config | Complete |
| CLI interface | Partial |
| React frontend | Structure exists |
| Tests | Empty |

**Overall:** ~85-90% feature complete

---

## Design Patterns

- **Strategy Pattern:** BaseCapability with specialized implementations
- **Factory Pattern:** `create_agent()`, `create_retriever()`
- **Template Method:** BaseEvaluator with execute flow
- **Lazy Loading:** `_retriever` and embedding model initialization
- **Cost Tracking:** CostTracker with daily budget limits

---

## Security Considerations

### Implemented
- Cost budget enforcement to prevent runaway API charges
- Timeout protections on code execution
- Comprehensive security vulnerability scanning (SafetyEvaluator)
- Sandbox for test execution (tempfile, subprocess)
- Input validation via Pydantic models

### Areas to Monitor
- API key management (should use secrets manager in production)
- RAG index permissions (ensure proper access control)
- Code execution sandboxing (subprocess is basic)
