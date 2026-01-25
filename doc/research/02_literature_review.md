# Literature Review: Current Solutions and Limitations

## 1. Overview

This document surveys existing approaches to evaluating LLM-generated code and identifies their limitations.

## 2. Existing Evaluation Approaches

### 2.1 Functional Correctness Metrics

#### Pass@k (Chen et al., 2021 - Codex/HumanEval)
- **Description**: Measures probability of generating at least one correct solution in k attempts
- **Strengths**: Standard benchmark for code generation
- **Limitations**: Only measures functional correctness, ignores security and robustness

#### CodeBLEU (Ren et al., 2020)
- **Description**: Combines BLEU with syntax and semantic matching
- **Strengths**: Considers code structure
- **Limitations**: Reference-based, doesn't evaluate actual execution

### 2.2 Security Analysis Tools

#### Bandit
- **Description**: Python static security analyzer
- **Strengths**: Detects common security issues
- **Limitations**: High false positive rate, Python-only, no LLM-specific checks

#### Semgrep
- **Description**: Pattern-based code analysis
- **Strengths**: Customizable rules
- **Limitations**: Requires rule configuration, no hallucination detection

### 2.3 Code Quality Tools

#### SonarQube
- **Description**: Comprehensive code quality platform
- **Strengths**: Wide language support, CI integration
- **Limitations**: Not designed for LLM evaluation, no robustness testing

#### Pylint/Flake8
- **Description**: Python linting tools
- **Strengths**: Style and error detection
- **Limitations**: Surface-level analysis, no semantic understanding

### 2.4 LLM-Specific Benchmarks

#### HumanEval (OpenAI)
- **Description**: 164 hand-written programming problems
- **Strengths**: Standard benchmark
- **Limitations**: Limited to correctness, small dataset

#### MBPP (Google)
- **Description**: 974 Python programming problems
- **Strengths**: Larger dataset
- **Limitations**: Still focused only on correctness

#### CodeXGLUE (Microsoft)
- **Description**: Multi-task benchmark
- **Strengths**: Diverse tasks
- **Limitations**: No quality dimension analysis

## 3. Identified Gaps

| Gap | Description | Impact |
|-----|-------------|--------|
| **Single-Dimensional** | Most tools focus on one aspect (correctness OR security) | Incomplete quality picture |
| **No Robustness Testing** | No systematic edge case evaluation | Fragile code in production |
| **No Hallucination Detection** | Tools don't check for fake imports/APIs | Runtime errors, confusion |
| **No Integration** | Separate tools, no unified framework | Difficult to use in practice |
| **No LLM-Specific Focus** | Tools designed for human-written code | Miss LLM-specific issues |

## 4. Summary of Limitations

### 4.1 Correctness Tools
- Focus only on functional correctness
- Don't assess code quality beyond "does it work"

### 4.2 Security Tools
- Designed for human-written code patterns
- High false positive rates
- Don't understand LLM-specific vulnerabilities

### 4.3 Benchmarks
- Measure aggregate performance
- Don't provide actionable feedback
- Limited to specific task types

### 4.4 Quality Tools
- Style-focused, not substance-focused
- No understanding of LLM generation patterns
- No hallucination awareness

## 5. Research Opportunity

There is a clear need for an **integrated, multi-dimensional evaluation framework** that:

1. Combines correctness, robustness, safety, and hallucination detection
2. Is designed specifically for LLM-generated code
3. Provides actionable feedback with severity levels
4. Supports batch evaluation for research
5. Integrates with development workflows

This gap motivates our proposed solution.

---

## References

1. Chen, M., et al. (2021). "Evaluating Large Language Models Trained on Code." arXiv:2107.03374
2. Ren, S., et al. (2020). "CodeBLEU: a Method for Automatic Evaluation of Code Synthesis." arXiv:2009.10297
3. Austin, J., et al. (2021). "Program Synthesis with Large Language Models." arXiv:2108.07732
4. Lu, S., et al. (2021). "CodeXGLUE: A Machine Learning Benchmark Dataset for Code Understanding and Generation." arXiv:2102.04664

---

*Document Version: 1.0*
*Last Updated: January 2026*
