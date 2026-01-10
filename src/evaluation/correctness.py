"""Correctness evaluator for generated code."""

import ast
import sys
import subprocess
import tempfile
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

from src.evaluation.base import (
    BaseEvaluator,
    EvaluationType,
    EvaluationTask,
    EvaluationResult,
    Issue,
    Severity,
)

logger = logging.getLogger(__name__)


class CorrectnessEvaluator(BaseEvaluator):
    """
    Evaluates the correctness of generated code.

    Checks:
    - Syntax validity (can be parsed)
    - Execution (runs without errors)
    - Test pass rate (if test cases provided)
    - Semantic similarity (if reference provided)
    """

    def __init__(
        self,
        threshold: float = 0.7,
        timeout: int = 10,
        allow_execution: bool = True
    ):
        """
        Initialize the correctness evaluator.

        Args:
            threshold: Minimum score to pass
            timeout: Execution timeout in seconds
            allow_execution: Whether to allow code execution
        """
        super().__init__(threshold)
        self.timeout = timeout
        self.allow_execution = allow_execution

    @property
    def evaluation_type(self) -> EvaluationType:
        return EvaluationType.CORRECTNESS

    def evaluate(self, task: EvaluationTask) -> EvaluationResult:
        """Evaluate the correctness of generated code."""
        issues = []
        details = {}
        scores = []

        code = task.generated_output

        # 1. Syntax check
        syntax_result = self._check_syntax(code, task.language)
        details["syntax"] = syntax_result
        if syntax_result["valid"]:
            scores.append(1.0)
        else:
            scores.append(0.0)
            issues.append(Issue(
                severity=Severity.CRITICAL,
                category="syntax_error",
                description=syntax_result.get("error", "Syntax error"),
                location=f"line {syntax_result.get('line', 'unknown')}"
            ))

        # 2. Execution check (only if syntax is valid and execution allowed)
        if syntax_result["valid"] and self.allow_execution and task.language == "python":
            exec_result = self._check_execution(code)
            details["execution"] = exec_result
            if exec_result["success"]:
                scores.append(1.0)
            else:
                scores.append(0.0)
                issues.append(Issue(
                    severity=Severity.HIGH,
                    category="execution_error",
                    description=exec_result.get("error", "Execution failed")[:200]
                ))

        # 3. Test case check (if provided)
        test_cases = task.metadata.get("test_cases", [])
        if test_cases and syntax_result["valid"] and self.allow_execution:
            test_result = self._run_tests(code, test_cases, task.language)
            details["tests"] = test_result
            scores.append(test_result["pass_rate"])
            if test_result["pass_rate"] < 1.0:
                for failed in test_result.get("failed_tests", []):
                    issues.append(Issue(
                        severity=Severity.MEDIUM,
                        category="test_failure",
                        description=f"Test failed: {failed['name']}",
                        suggestion=failed.get("error", "")[:100]
                    ))

        # 4. Semantic similarity (if reference provided)
        if task.reference_output:
            similarity = self._compute_similarity(code, task.reference_output)
            details["similarity"] = similarity
            scores.append(similarity)

        # Calculate final score
        final_score = sum(scores) / len(scores) if scores else 0.0

        return self._create_result(
            score=final_score,
            issues=issues,
            details=details
        )

    def _check_syntax(self, code: str, language: str) -> Dict[str, Any]:
        """Check if code has valid syntax."""
        if language != "python":
            # For non-Python, just check if it's not empty
            return {"valid": bool(code.strip()), "language": language}

        try:
            ast.parse(code)
            return {"valid": True}
        except SyntaxError as e:
            return {
                "valid": False,
                "error": str(e.msg),
                "line": e.lineno,
                "offset": e.offset
            }

    def _check_execution(self, code: str) -> Dict[str, Any]:
        """Check if code executes without errors."""
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False
            ) as f:
                # Wrap code to catch execution errors
                wrapped_code = f'''
import sys
try:
{self._indent_code(code)}
except Exception as e:
    print(f"EXECUTION_ERROR: {{type(e).__name__}}: {{e}}", file=sys.stderr)
    sys.exit(1)
'''
                f.write(wrapped_code)
                f.flush()

                result = subprocess.run(
                    [sys.executable, f.name],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )

                # Clean up
                Path(f.name).unlink(missing_ok=True)

                if result.returncode == 0:
                    return {"success": True, "output": result.stdout[:500]}
                else:
                    return {
                        "success": False,
                        "error": result.stderr[:500] or "Unknown error",
                        "return_code": result.returncode
                    }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Execution timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_tests(
        self,
        code: str,
        test_cases: List[Dict[str, Any]],
        language: str
    ) -> Dict[str, Any]:
        """Run test cases against the code."""
        if language != "python":
            return {"pass_rate": 0.0, "error": "Only Python tests supported"}

        passed = 0
        failed_tests = []

        for i, test in enumerate(test_cases):
            test_name = test.get("name", f"test_{i}")
            test_code = test.get("code", "")
            expected = test.get("expected")

            try:
                # Create test file
                full_code = f"{code}\n\n{test_code}"

                with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.py',
                    delete=False
                ) as f:
                    f.write(full_code)
                    f.flush()

                    result = subprocess.run(
                        [sys.executable, f.name],
                        capture_output=True,
                        text=True,
                        timeout=self.timeout
                    )

                    Path(f.name).unlink(missing_ok=True)

                    if result.returncode == 0:
                        # Check expected output if provided
                        if expected is not None:
                            if expected in result.stdout:
                                passed += 1
                            else:
                                failed_tests.append({
                                    "name": test_name,
                                    "error": f"Expected '{expected}' not in output"
                                })
                        else:
                            passed += 1
                    else:
                        failed_tests.append({
                            "name": test_name,
                            "error": result.stderr[:200]
                        })

            except Exception as e:
                failed_tests.append({
                    "name": test_name,
                    "error": str(e)
                })

        total = len(test_cases)
        pass_rate = passed / total if total > 0 else 0.0

        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": pass_rate,
            "failed_tests": failed_tests
        }

    def _compute_similarity(self, code: str, reference: str) -> float:
        """Compute semantic similarity between code and reference."""
        # Simple token-based similarity
        code_tokens = set(code.split())
        ref_tokens = set(reference.split())

        if not code_tokens or not ref_tokens:
            return 0.0

        intersection = code_tokens & ref_tokens
        union = code_tokens | ref_tokens

        return len(intersection) / len(union)

    def _indent_code(self, code: str, spaces: int = 4) -> str:
        """Indent code by given spaces."""
        indent = " " * spaces
        lines = code.split('\n')
        return '\n'.join(indent + line for line in lines)

    def check_syntax_only(self, code: str, language: str = "python") -> bool:
        """Quick syntax check without full evaluation."""
        result = self._check_syntax(code, language)
        return result["valid"]


def evaluate_correctness(
    code: str,
    reference: Optional[str] = None,
    test_cases: Optional[List[Dict]] = None,
    language: str = "python"
) -> EvaluationResult:
    """
    Quick function to evaluate code correctness.

    Args:
        code: Generated code to evaluate
        reference: Optional reference implementation
        test_cases: Optional list of test cases
        language: Programming language

    Returns:
        EvaluationResult
    """
    evaluator = CorrectnessEvaluator()
    task = EvaluationTask(
        task_id="quick_eval",
        input_text="",
        generated_output=code,
        reference_output=reference,
        language=language,
        metadata={"test_cases": test_cases or []}
    )
    return evaluator.evaluate(task)
