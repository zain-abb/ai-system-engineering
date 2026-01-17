"""Tests for the safety evaluator."""

import pytest
import json
import re
from unittest.mock import patch, MagicMock
import subprocess

from src.evaluation.base import (
    EvaluationType,
    EvaluationTask,
    Severity,
    Issue,
)
from src.evaluation.safety import (
    SafetyEvaluator,
    VULNERABILITY_PATTERNS,
    BANDIT_SEVERITY_MAP,
    evaluate_safety,
)


class TestSafetyEvaluatorInit:
    """Tests for SafetyEvaluator initialization."""

    def test_default_initialization(self):
        """Test default evaluator initialization."""
        evaluator = SafetyEvaluator()
        assert evaluator.threshold == 0.7
        assert evaluator.use_bandit is True
        assert evaluator.custom_patterns is True
        assert evaluator.severity_weights is not None

    def test_custom_initialization(self):
        """Test custom evaluator initialization."""
        custom_weights = {Severity.CRITICAL: 0.5}
        evaluator = SafetyEvaluator(
            threshold=0.8,
            use_bandit=False,
            custom_patterns=False,
            severity_weights=custom_weights
        )
        assert evaluator.threshold == 0.8
        assert evaluator.use_bandit is False
        assert evaluator.custom_patterns is False
        assert evaluator.severity_weights[Severity.CRITICAL] == 0.5

    def test_evaluation_type_property(self):
        """Test evaluation_type property returns SAFETY."""
        evaluator = SafetyEvaluator()
        assert evaluator.evaluation_type == EvaluationType.SAFETY

    def test_default_severity_weights(self):
        """Test default severity weights are set correctly."""
        evaluator = SafetyEvaluator()
        assert Severity.CRITICAL in evaluator.severity_weights
        assert Severity.HIGH in evaluator.severity_weights
        assert evaluator.severity_weights[Severity.CRITICAL] > evaluator.severity_weights[Severity.HIGH]


class TestVulnerabilityPatterns:
    """Tests for vulnerability pattern definitions."""

    def test_vulnerability_patterns_defined(self):
        """Test that vulnerability patterns are defined."""
        assert len(VULNERABILITY_PATTERNS) > 0
        expected_vuln_types = [
            "sql_injection", "command_injection", "hardcoded_secrets",
            "xss_vulnerability", "path_traversal", "insecure_deserialization",
            "weak_crypto", "insecure_random", "debug_code", "insecure_ssl"
        ]
        for vuln_type in expected_vuln_types:
            assert vuln_type in VULNERABILITY_PATTERNS

    def test_vulnerability_pattern_structure(self):
        """Test that vulnerability patterns have correct structure."""
        for vuln_type, vuln_info in VULNERABILITY_PATTERNS.items():
            assert "patterns" in vuln_info
            assert "severity" in vuln_info
            assert "description" in vuln_info
            assert "suggestion" in vuln_info
            assert isinstance(vuln_info["patterns"], list)
            assert isinstance(vuln_info["severity"], Severity)


class TestSQLInjectionDetection:
    """Tests for SQL injection detection."""

    def test_sql_injection_f_string(self, sample_vulnerable_sql_injection):
        """Test detection of SQL injection via f-string."""
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_vulnerable_sql_injection
        )
        result = evaluator.evaluate(task)

        assert any(i.category == "sql_injection" for i in result.issues)

    def test_sql_injection_string_format(self):
        """Test detection of SQL injection via string concatenation."""
        code = '''
def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE id = " + user_id)
'''
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert any(i.category == "sql_injection" for i in result.issues)

    def test_safe_sql_not_flagged(self):
        """Test that parameterized queries are not flagged."""
        code = '''
def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
'''
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert not any(i.category == "sql_injection" for i in result.issues)


class TestCommandInjectionDetection:
    """Tests for command injection detection."""

    def test_os_system_detected(self, sample_vulnerable_command_injection):
        """Test detection of os.system usage."""
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_vulnerable_command_injection
        )
        result = evaluator.evaluate(task)

        assert any(i.category == "command_injection" for i in result.issues)

    def test_shell_true_detected(self):
        """Test detection of shell=True."""
        code = '''
import subprocess
subprocess.run(f"echo {user_input}", shell=True)
'''
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert any(i.category == "command_injection" for i in result.issues)

    def test_eval_detected(self, sample_vulnerable_eval):
        """Test detection of eval usage."""
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_vulnerable_eval
        )
        result = evaluator.evaluate(task)

        assert any(i.category == "command_injection" for i in result.issues)

    def test_safe_subprocess_not_flagged(self):
        """Test that safe subprocess usage is not flagged."""
        code = '''
import subprocess
subprocess.run(["echo", "hello"], capture_output=True)
'''
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        # Should not flag command injection for safe usage
        assert not any(i.category == "command_injection" for i in result.issues)


class TestHardcodedSecretsDetection:
    """Tests for hardcoded secrets detection."""

    def test_hardcoded_password_detected(self, sample_vulnerable_hardcoded_secrets):
        """Test detection of hardcoded passwords."""
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_vulnerable_hardcoded_secrets
        )
        result = evaluator.evaluate(task)

        assert any(i.category == "hardcoded_secrets" for i in result.issues)

    def test_hardcoded_api_key_detected(self):
        """Test detection of hardcoded API keys."""
        code = '''
API_KEY = "sk-abcdef1234567890abcdef1234567890"
'''
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert any(i.category == "hardcoded_secrets" for i in result.issues)

    def test_env_var_not_flagged(self):
        """Test that environment variable usage is not flagged."""
        code = '''
import os
API_KEY = os.environ.get("API_KEY")
'''
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert not any(i.category == "hardcoded_secrets" for i in result.issues)


class TestXSSDetection:
    """Tests for XSS vulnerability detection."""

    def test_innerhtml_detected(self):
        """Test detection of innerHTML usage."""
        code = '''
element.innerHTML = user_input
'''
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert any(i.category == "xss_vulnerability" for i in result.issues)

    def test_render_template_string_detected(self):
        """Test detection of render_template_string."""
        code = '''
from flask import render_template_string
render_template_string(user_template)
'''
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert any(i.category == "xss_vulnerability" for i in result.issues)


class TestPathTraversalDetection:
    """Tests for path traversal detection."""

    def test_path_traversal_pattern_detected(self):
        """Test detection of path traversal patterns."""
        code = '''
filename = "../../../etc/passwd"
'''
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert any(i.category == "path_traversal" for i in result.issues)

    def test_open_with_concat_detected(self):
        """Test detection of open() with string concatenation."""
        code = '''
def read_file(user_path):
    with open("/data/" + user_path) as f:
        return f.read()
'''
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert any(i.category == "path_traversal" for i in result.issues)


class TestInsecureDeserializationDetection:
    """Tests for insecure deserialization detection."""

    def test_pickle_load_detected(self, sample_vulnerable_pickle):
        """Test detection of pickle.load."""
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_vulnerable_pickle
        )
        result = evaluator.evaluate(task)

        assert any(i.category == "insecure_deserialization" for i in result.issues)

    def test_yaml_unsafe_load_detected(self):
        """Test detection of yaml.unsafe_load."""
        code = '''
import yaml
data = yaml.unsafe_load(user_input)
'''
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert any(i.category == "insecure_deserialization" for i in result.issues)

    def test_json_load_not_flagged(self):
        """Test that json.load is not flagged."""
        code = '''
import json
data = json.load(file)
'''
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert not any(i.category == "insecure_deserialization" for i in result.issues)


class TestWeakCryptoDetection:
    """Tests for weak cryptography detection."""

    def test_md5_detected(self):
        """Test detection of MD5 usage."""
        code = '''
import hashlib
hash_value = hashlib.md5(data).hexdigest()
'''
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert any(i.category == "weak_crypto" for i in result.issues)

    def test_sha1_detected(self):
        """Test detection of SHA1 usage."""
        code = '''
import hashlib
hash_value = hashlib.sha1(data).hexdigest()
'''
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert any(i.category == "weak_crypto" for i in result.issues)

    def test_sha256_not_flagged(self):
        """Test that SHA256 is not flagged."""
        code = '''
import hashlib
hash_value = hashlib.sha256(data).hexdigest()
'''
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert not any(i.category == "weak_crypto" for i in result.issues)


class TestInsecureRandomDetection:
    """Tests for insecure random detection."""

    def test_random_randint_detected(self):
        """Test detection of random.randint."""
        code = '''
import random
token = random.randint(0, 1000000)
'''
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert any(i.category == "insecure_random" for i in result.issues)

    def test_secrets_module_not_flagged(self):
        """Test that secrets module is not flagged."""
        code = '''
import secrets
token = secrets.token_hex(32)
'''
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert not any(i.category == "insecure_random" for i in result.issues)


class TestDebugCodeDetection:
    """Tests for debug code detection."""

    def test_debug_true_detected(self):
        """Test detection of DEBUG = True."""
        code = '''
DEBUG = True
'''
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert any(i.category == "debug_code" for i in result.issues)

    def test_set_trace_detected(self):
        """Test detection of debugger set_trace."""
        code = '''
import pdb
pdb.set_trace()
'''
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert any(i.category == "debug_code" for i in result.issues)


class TestInsecureSSLDetection:
    """Tests for insecure SSL detection."""

    def test_verify_false_detected(self):
        """Test detection of verify=False."""
        code = '''
requests.get(url, verify=False)
'''
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert any(i.category == "insecure_ssl" for i in result.issues)

    def test_cert_none_detected(self):
        """Test detection of CERT_NONE."""
        code = '''
import ssl
context = ssl.SSLContext()
context.verify_mode = ssl.CERT_NONE
'''
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert any(i.category == "insecure_ssl" for i in result.issues)


class TestASTAnalysis:
    """Tests for AST-based analysis."""

    def test_dangerous_imports_detected(self):
        """Test detection of dangerous imports."""
        code = '''
import pickle
import subprocess
import os
'''
        evaluator = SafetyEvaluator(use_bandit=False, custom_patterns=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert "ast_analysis" in result.details
        assert len(result.details["ast_analysis"]["findings"]["dangerous_imports"]) > 0

    def test_dangerous_function_calls_detected(self, sample_vulnerable_eval):
        """Test detection of dangerous function calls."""
        evaluator = SafetyEvaluator(use_bandit=False, custom_patterns=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_vulnerable_eval
        )
        result = evaluator.evaluate(task)

        assert "ast_analysis" in result.details
        assert any(i.category == "code_execution" for i in result.issues)

    def test_ast_handles_syntax_errors(self, sample_invalid_python):
        """Test that AST analysis handles syntax errors gracefully."""
        evaluator = SafetyEvaluator(use_bandit=False, custom_patterns=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_invalid_python
        )
        result = evaluator.evaluate(task)

        assert "ast_analysis" in result.details
        assert "error" in result.details["ast_analysis"]


class TestAntiPatternDetection:
    """Tests for anti-pattern detection."""

    def test_bare_except_detected(self):
        """Test detection of bare except clause."""
        code = '''
try:
    risky_operation()
except:
    pass
'''
        evaluator = SafetyEvaluator(use_bandit=False, custom_patterns=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert any(i.category == "bare_except" for i in result.issues)

    def test_wildcard_import_detected(self):
        """Test detection of wildcard imports."""
        code = '''
from os import *
'''
        evaluator = SafetyEvaluator(use_bandit=False, custom_patterns=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert any(i.category == "wildcard_import" for i in result.issues)

    def test_mutable_default_detected(self):
        """Test detection of mutable default arguments."""
        code = '''
def append_item(item, items=[]):
    items.append(item)
    return items
'''
        evaluator = SafetyEvaluator(use_bandit=False, custom_patterns=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert any(i.category == "mutable_default" for i in result.issues)

    def test_assert_security_detected(self):
        """Test detection of assert for security checks."""
        code = '''
assert user.is_admin, "Permission denied"
'''
        evaluator = SafetyEvaluator(use_bandit=False, custom_patterns=False)
        task = EvaluationTask(task_id="test", input_text="", generated_output=code)
        result = evaluator.evaluate(task)

        assert any(i.category == "assert_security" for i in result.issues)


class TestBanditIntegration:
    """Tests for bandit integration."""

    def test_bandit_result_parsing(self, mock_bandit_output):
        """Test parsing of bandit output."""
        evaluator = SafetyEvaluator(use_bandit=True)

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps(mock_bandit_output),
                returncode=0
            )

            task = EvaluationTask(
                task_id="test",
                input_text="",
                generated_output="import sqlite3"
            )
            result = evaluator.evaluate(task)

            assert "bandit" in result.details
            assert result.details["bandit"]["ran"] is True

    def test_bandit_not_installed(self):
        """Test graceful handling when bandit is not installed."""
        evaluator = SafetyEvaluator(use_bandit=True)

        with patch('subprocess.run', side_effect=FileNotFoundError("bandit not found")):
            task = EvaluationTask(
                task_id="test",
                input_text="",
                generated_output="print('hello')"
            )
            result = evaluator.evaluate(task)

            assert "bandit" in result.details
            assert result.details["bandit"]["ran"] is False
            assert "not installed" in result.details["bandit"]["error"].lower()

    def test_bandit_timeout(self):
        """Test handling of bandit timeout."""
        evaluator = SafetyEvaluator(use_bandit=True)

        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired("bandit", 30)):
            task = EvaluationTask(
                task_id="test",
                input_text="",
                generated_output="print('hello')"
            )
            result = evaluator.evaluate(task)

            assert "bandit" in result.details
            assert result.details["bandit"]["ran"] is False
            assert "timeout" in result.details["bandit"]["error"].lower()

    def test_bandit_disabled(self, sample_valid_python):
        """Test that bandit can be disabled."""
        evaluator = SafetyEvaluator(use_bandit=False)

        # Should not call subprocess when bandit is disabled
        with patch('subprocess.run') as mock_run:
            task = EvaluationTask(
                task_id="test",
                input_text="",
                generated_output=sample_valid_python
            )
            evaluator.evaluate(task)

            mock_run.assert_not_called()


class TestScoreCalculation:
    """Tests for score calculation."""

    def test_perfect_score_no_issues(self, sample_safe_code):
        """Test perfect score when no issues found."""
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_safe_code
        )
        result = evaluator.evaluate(task)

        assert result.score == 1.0
        assert result.passed is True

    def test_score_decreases_with_issues(self, sample_vulnerable_sql_injection):
        """Test that score decreases with issues."""
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_vulnerable_sql_injection
        )
        result = evaluator.evaluate(task)

        assert result.score < 1.0

    def test_severity_weights_affect_score(self):
        """Test that severity weights affect score calculation."""
        evaluator = SafetyEvaluator(use_bandit=False)

        # Create list of issues with different severities
        issues = [
            Issue(Severity.CRITICAL, "test", "Critical issue"),
            Issue(Severity.LOW, "test", "Low issue"),
        ]

        score = evaluator._calculate_score(issues)
        assert 0 < score < 1

    def test_score_capped_at_zero(self):
        """Test that score doesn't go below zero."""
        evaluator = SafetyEvaluator(use_bandit=False)

        # Many critical issues
        issues = [Issue(Severity.CRITICAL, "test", f"Issue {i}") for i in range(10)]

        score = evaluator._calculate_score(issues)
        assert score == 0.0


class TestQuickScan:
    """Tests for quick_scan method."""

    def test_quick_scan_safe_code(self, sample_safe_code):
        """Test quick_scan with safe code."""
        evaluator = SafetyEvaluator()
        is_safe, concerns = evaluator.quick_scan(sample_safe_code)

        assert is_safe is True
        assert len(concerns) == 0

    def test_quick_scan_detects_eval(self, sample_vulnerable_eval):
        """Test quick_scan detects eval."""
        evaluator = SafetyEvaluator()
        is_safe, concerns = evaluator.quick_scan(sample_vulnerable_eval)

        assert is_safe is False
        assert any("eval" in c.lower() for c in concerns)

    def test_quick_scan_detects_os_system(self, sample_vulnerable_command_injection):
        """Test quick_scan detects os.system."""
        evaluator = SafetyEvaluator()
        is_safe, concerns = evaluator.quick_scan(sample_vulnerable_command_injection)

        assert is_safe is False
        assert any("os.system" in c.lower() for c in concerns)


class TestEvaluateSafetyFunction:
    """Tests for the evaluate_safety convenience function."""

    def test_evaluate_safety_basic(self, sample_valid_python):
        """Test basic usage of evaluate_safety function."""
        result = evaluate_safety(sample_valid_python)

        assert result.evaluation_type == EvaluationType.SAFETY
        assert result.score >= 0

    def test_evaluate_safety_with_vulnerable_code(self, sample_vulnerable_sql_injection):
        """Test evaluate_safety with vulnerable code."""
        result = evaluate_safety(sample_vulnerable_sql_injection)

        assert len(result.issues) > 0

    def test_evaluate_safety_non_python(self):
        """Test evaluate_safety with non-Python code."""
        result = evaluate_safety(
            "const x = eval(input);",
            language="javascript"
        )

        # Should still do pattern matching
        assert result.evaluation_type == EvaluationType.SAFETY


class TestSummaryGeneration:
    """Tests for evaluation summary generation."""

    def test_summary_contains_issue_counts(self, sample_vulnerable_sql_injection):
        """Test that summary contains issue counts."""
        evaluator = SafetyEvaluator(use_bandit=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=sample_vulnerable_sql_injection
        )
        result = evaluator.evaluate(task)

        assert "summary" in result.details
        assert "total_issues" in result.details["summary"]
        assert "critical_count" in result.details["summary"]
        assert "high_count" in result.details["summary"]


class TestMissingCoverage:
    """Tests for previously uncovered code paths."""

    def test_bandit_json_decode_error(self):
        """Test handling of JSON decode error in bandit output (lines 287-288)."""
        evaluator = SafetyEvaluator(use_bandit=True)

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout="invalid json {{{",  # Invalid JSON
                returncode=0
            )

            task = EvaluationTask(
                task_id="test",
                input_text="",
                generated_output="print('hello')"
            )
            result = evaluator.evaluate(task)

            # Should handle gracefully
            assert "bandit" in result.details
            assert result.details["bandit"]["ran"] is True

    def test_bandit_general_exception(self):
        """Test handling of general exceptions in bandit (lines 301-303)."""
        evaluator = SafetyEvaluator(use_bandit=True)

        with patch('subprocess.run', side_effect=PermissionError("Access denied")):
            task = EvaluationTask(
                task_id="test",
                input_text="",
                generated_output="print('hello')"
            )
            result = evaluator.evaluate(task)

            assert "bandit" in result.details
            assert result.details["bandit"]["ran"] is False
            assert "Access denied" in result.details["bandit"]["error"]

    def test_pattern_regex_error_handling(self):
        """Test handling of regex errors in pattern checking (lines 318-319)."""
        evaluator = SafetyEvaluator(use_bandit=False, custom_patterns=True)

        # Mock re.findall to raise an error on specific patterns
        original_findall = re.findall

        def mock_findall(pattern, string, flags=0):
            if "sql" in pattern.lower():
                raise re.error("mock regex error")
            return original_findall(pattern, string, flags)

        with patch('src.evaluation.safety.re.findall', side_effect=mock_findall):
            task = EvaluationTask(
                task_id="test",
                input_text="",
                generated_output="cursor.execute(query)"
            )
            result = evaluator.evaluate(task)

            # Should handle gracefully and continue
            assert "patterns" in result.details

    def test_find_pattern_lines_regex_error(self):
        """Test _find_pattern_lines handles regex errors (lines 348-349)."""
        evaluator = SafetyEvaluator(use_bandit=False)

        # Call with an invalid regex pattern
        lines = evaluator._find_pattern_lines(
            "some code here",
            [r"[invalid(regex"]  # Invalid regex
        )

        # Should handle gracefully and return empty or partial results
        assert isinstance(lines, list)

    def test_unsafe_input_detection(self):
        """Test detection of unsafe input() usage (lines 480-481)."""
        code = '''
user_name = input("Enter your name: ")
print(f"Hello, {user_name}")
'''
        evaluator = SafetyEvaluator(use_bandit=False, custom_patterns=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=code
        )
        result = evaluator.evaluate(task)

        # Should detect unsafe input usage
        assert any(i.category == "unsafe_input" for i in result.issues)

    def test_unsafe_input_with_int_not_flagged(self):
        """Test that int(input()) is not flagged as unsafe_input."""
        code = '''
age = int(input("Enter your age: "))
print(f"You are {age} years old")
'''
        evaluator = SafetyEvaluator(use_bandit=False, custom_patterns=False)
        task = EvaluationTask(
            task_id="test",
            input_text="",
            generated_output=code
        )
        result = evaluator.evaluate(task)

        # Should NOT flag int(input()) as unsafe
        assert not any(i.category == "unsafe_input" for i in result.issues)
