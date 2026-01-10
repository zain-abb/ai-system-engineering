"""Hallucination detector for LLM-generated code."""

import ast
import re
import sys
import logging
import importlib.util
from typing import Optional, Dict, Any, List, Set, Tuple
from dataclasses import dataclass

from src.evaluation.base import (
    BaseEvaluator,
    EvaluationType,
    EvaluationTask,
    EvaluationResult,
    Issue,
    Severity,
)

logger = logging.getLogger(__name__)


# Known standard library modules (Python 3.11)
STDLIB_MODULES = {
    "abc", "aifc", "argparse", "array", "ast", "asyncio", "atexit",
    "base64", "bdb", "binascii", "binhex", "bisect", "builtins",
    "bz2", "calendar", "cgi", "cgitb", "chunk", "cmath", "cmd",
    "code", "codecs", "codeop", "collections", "colorsys", "compileall",
    "concurrent", "configparser", "contextlib", "contextvars", "copy",
    "copyreg", "cProfile", "crypt", "csv", "ctypes", "curses",
    "dataclasses", "datetime", "dbm", "decimal", "difflib", "dis",
    "distutils", "doctest", "email", "encodings", "enum", "errno",
    "faulthandler", "fcntl", "filecmp", "fileinput", "fnmatch",
    "fractions", "ftplib", "functools", "gc", "getopt", "getpass",
    "gettext", "glob", "graphlib", "grp", "gzip", "hashlib", "heapq",
    "hmac", "html", "http", "idlelib", "imaplib", "imghdr", "imp",
    "importlib", "inspect", "io", "ipaddress", "itertools", "json",
    "keyword", "lib2to3", "linecache", "locale", "logging", "lzma",
    "mailbox", "mailcap", "marshal", "math", "mimetypes", "mmap",
    "modulefinder", "multiprocessing", "netrc", "nis", "nntplib",
    "numbers", "operator", "optparse", "os", "pathlib", "pdb",
    "pickle", "pickletools", "pipes", "pkgutil", "platform", "plistlib",
    "poplib", "posix", "posixpath", "pprint", "profile", "pstats",
    "pty", "pwd", "py_compile", "pyclbr", "pydoc", "queue", "quopri",
    "random", "re", "readline", "reprlib", "resource", "rlcompleter",
    "runpy", "sched", "secrets", "select", "selectors", "shelve",
    "shlex", "shutil", "signal", "site", "smtpd", "smtplib", "sndhdr",
    "socket", "socketserver", "spwd", "sqlite3", "ssl", "stat",
    "statistics", "string", "stringprep", "struct", "subprocess",
    "sunau", "symtable", "sys", "sysconfig", "syslog", "tabnanny",
    "tarfile", "telnetlib", "tempfile", "termios", "test", "textwrap",
    "threading", "time", "timeit", "tkinter", "token", "tokenize",
    "tomllib", "trace", "traceback", "tracemalloc", "tty", "turtle",
    "turtledemo", "types", "typing", "unicodedata", "unittest", "urllib",
    "uu", "uuid", "venv", "warnings", "wave", "weakref", "webbrowser",
    "winreg", "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc",
    "zipapp", "zipfile", "zipimport", "zlib", "zoneinfo",
    # Common submodules
    "typing_extensions", "collections.abc", "os.path", "urllib.parse",
    "urllib.request", "http.client", "http.server", "email.mime",
    "concurrent.futures", "asyncio.tasks", "unittest.mock",
}

# Common third-party packages (popular ones)
COMMON_PACKAGES = {
    "numpy", "pandas", "scipy", "matplotlib", "seaborn", "sklearn",
    "scikit-learn", "tensorflow", "torch", "pytorch", "keras",
    "flask", "django", "fastapi", "uvicorn", "starlette",
    "requests", "httpx", "aiohttp", "urllib3", "beautifulsoup4", "bs4",
    "lxml", "selenium", "scrapy", "pillow", "PIL", "opencv", "cv2",
    "sqlalchemy", "psycopg2", "pymongo", "redis", "celery",
    "pytest", "unittest", "nose", "mock", "hypothesis",
    "boto3", "botocore", "google", "azure",
    "pydantic", "marshmallow", "attrs", "dataclasses",
    "click", "typer", "argparse", "fire",
    "rich", "tqdm", "colorama", "termcolor",
    "yaml", "pyyaml", "toml", "configparser",
    "cryptography", "bcrypt", "passlib", "jwt", "pyjwt",
    "networkx", "igraph", "graphviz",
    "spacy", "nltk", "transformers", "huggingface",
    "openai", "anthropic", "langchain", "llama_index",
    "streamlit", "gradio", "dash", "plotly", "bokeh",
    "arrow", "pendulum", "dateutil", "pytz",
    "numpy", "np", "pd", "plt", "tf", "nn",  # Common aliases
}

# Known fake/hallucinated modules that LLMs sometimes generate
KNOWN_FAKE_MODULES = {
    "utils.helpers", "common.utils", "helpers", "my_module",
    "project.utils", "app.helpers", "core.utils",
    "api_helpers", "data_utils", "model_utils",
}


@dataclass
class ImportInfo:
    """Information about an import statement."""
    module: str
    names: List[str]
    line: int
    is_from_import: bool


@dataclass
class FunctionCallInfo:
    """Information about a function call."""
    name: str
    module: Optional[str]
    line: int
    args_count: int


class HallucinationDetector(BaseEvaluator):
    """
    Detects hallucinations in LLM-generated code.

    Checks for:
    - Non-existent modules/packages
    - Fake API calls or functions
    - Invalid function signatures
    - Made-up class names or methods
    - Incorrect standard library usage
    """

    def __init__(
        self,
        threshold: float = 0.7,
        check_imports: bool = True,
        check_apis: bool = True,
        check_signatures: bool = True,
        strict_mode: bool = False
    ):
        """
        Initialize the hallucination detector.

        Args:
            threshold: Minimum score to pass
            check_imports: Whether to validate imports
            check_apis: Whether to check for fake APIs
            check_signatures: Whether to validate signatures
            strict_mode: If True, unknown imports are flagged as issues
        """
        super().__init__(threshold)
        self.check_imports = check_imports
        self.check_apis = check_apis
        self.check_signatures = check_signatures
        self.strict_mode = strict_mode

    @property
    def evaluation_type(self) -> EvaluationType:
        return EvaluationType.HALLUCINATION

    def evaluate(self, task: EvaluationTask) -> EvaluationResult:
        """Evaluate code for hallucinations."""
        issues = []
        details = {}

        code = task.generated_output
        language = task.language

        # Only full support for Python
        if language != "python":
            return self._create_result(
                score=1.0,
                issues=[],
                details={"note": "Hallucination detection only supports Python"}
            )

        # Parse code
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return self._create_result(
                score=0.5,
                issues=[Issue(
                    severity=Severity.HIGH,
                    category="parse_error",
                    description=f"Could not parse code: {e}"
                )],
                details={"parse_error": str(e)}
            )

        # 1. Check imports
        if self.check_imports:
            import_result = self._check_imports(tree, code)
            details["imports"] = import_result
            issues.extend(import_result.get("issues", []))

        # 2. Check for fake APIs
        if self.check_apis:
            api_result = self._check_apis(tree, code)
            details["apis"] = api_result
            issues.extend(api_result.get("issues", []))

        # 3. Check function signatures
        if self.check_signatures:
            sig_result = self._check_signatures(tree, code)
            details["signatures"] = sig_result
            issues.extend(sig_result.get("issues", []))

        # 4. Check for common hallucination patterns
        pattern_result = self._check_hallucination_patterns(code)
        details["patterns"] = pattern_result
        issues.extend(pattern_result.get("issues", []))

        # Calculate score
        final_score = self._calculate_score(issues)

        # Summary
        details["summary"] = {
            "total_hallucinations": len(issues),
            "import_issues": sum(1 for i in issues if "import" in i.category),
            "api_issues": sum(1 for i in issues if "api" in i.category),
            "signature_issues": sum(1 for i in issues if "signature" in i.category),
        }

        return self._create_result(
            score=final_score,
            issues=issues,
            details=details
        )

    def _check_imports(self, tree: ast.AST, code: str) -> Dict[str, Any]:
        """Check for invalid or hallucinated imports."""
        issues = []
        imports_found = []
        invalid_imports = []
        valid_imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_info = ImportInfo(
                        module=alias.name,
                        names=[alias.name],
                        line=node.lineno,
                        is_from_import=False
                    )
                    imports_found.append(import_info)
                    is_valid, reason = self._validate_module(alias.name)
                    if not is_valid:
                        invalid_imports.append((alias.name, reason))
                    else:
                        valid_imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [alias.name for alias in node.names]
                import_info = ImportInfo(
                    module=module,
                    names=names,
                    line=node.lineno,
                    is_from_import=True
                )
                imports_found.append(import_info)

                is_valid, reason = self._validate_module(module)
                if not is_valid:
                    invalid_imports.append((module, reason))
                else:
                    valid_imports.append(module)
                    # Check if imported names exist
                    for name in names:
                        if name != "*":
                            is_name_valid = self._validate_import_name(module, name)
                            if not is_name_valid and self.strict_mode:
                                invalid_imports.append((f"{module}.{name}", "name may not exist"))

        # Create issues for invalid imports
        for module, reason in invalid_imports:
            severity = Severity.HIGH if reason == "known_fake" else Severity.MEDIUM
            issues.append(Issue(
                severity=severity,
                category="invalid_import",
                description=f"Potentially hallucinated import: {module}",
                suggestion=f"Reason: {reason}. Verify this module exists."
            ))

        return {
            "total_imports": len(imports_found),
            "valid_imports": valid_imports,
            "invalid_imports": [m for m, _ in invalid_imports],
            "issues": issues
        }

    def _validate_module(self, module: str) -> Tuple[bool, str]:
        """Validate if a module exists."""
        if not module:
            return True, "empty"

        # Get base module
        base_module = module.split('.')[0]

        # Check if it's a known fake module
        if module in KNOWN_FAKE_MODULES or base_module in KNOWN_FAKE_MODULES:
            return False, "known_fake"

        # Check standard library
        if base_module in STDLIB_MODULES:
            return True, "stdlib"

        # Check common packages
        if base_module in COMMON_PACKAGES:
            return True, "common_package"

        # Try to find the module spec (only works if installed)
        try:
            spec = importlib.util.find_spec(base_module)
            if spec is not None:
                return True, "installed"
        except (ImportError, ModuleNotFoundError, ValueError):
            pass

        # In strict mode, unknown modules are suspicious
        if self.strict_mode:
            return False, "unknown"

        # In non-strict mode, give benefit of doubt for plausible names
        if self._is_plausible_module_name(module):
            return True, "plausible"

        return False, "unlikely"

    def _is_plausible_module_name(self, module: str) -> bool:
        """Check if a module name looks plausible."""
        # Check for common patterns that suggest real modules
        plausible_patterns = [
            r'^[a-z][a-z0-9_]*$',  # Simple lowercase name
            r'^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$',  # module.submodule
        ]
        for pattern in plausible_patterns:
            if re.match(pattern, module):
                return True
        return False

    def _validate_import_name(self, module: str, name: str) -> bool:
        """Validate if a name can be imported from a module."""
        try:
            mod = importlib.import_module(module)
            return hasattr(mod, name)
        except (ImportError, ModuleNotFoundError):
            return True  # Can't verify, assume OK

    def _check_apis(self, tree: ast.AST, code: str) -> Dict[str, Any]:
        """Check for fake or hallucinated API calls."""
        issues = []
        suspicious_calls = []

        # Common fake API patterns that LLMs generate
        fake_api_patterns = [
            # Fake OpenAI-like APIs
            r'\.generate_completion\(',
            r'\.create_embedding\(',
            r'\.get_response\(',
            r'\.send_message\(',
            r'\.ask\(',
            # Fake helper methods
            r'\.to_dataframe\(\)',  # On non-pandas objects
            r'\.convert\(',
            r'\.transform_to\(',
            # Fake utility functions
            r'parse_json_safely\(',
            r'safe_execute\(',
            r'auto_retry\(',
        ]

        for pattern in fake_api_patterns:
            matches = re.findall(pattern, code)
            if matches:
                suspicious_calls.extend(matches)

        # Check for method calls on objects
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_info = self._extract_call_info(node)
                if call_info:
                    if self._is_suspicious_call(call_info):
                        suspicious_calls.append(f"{call_info.module}.{call_info.name}" if call_info.module else call_info.name)

        if suspicious_calls:
            issues.append(Issue(
                severity=Severity.MEDIUM,
                category="suspicious_api",
                description=f"Potentially hallucinated API calls: {', '.join(set(suspicious_calls)[:5])}",
                suggestion="Verify these API calls exist in the libraries being used"
            ))

        return {
            "suspicious_calls": list(set(suspicious_calls)),
            "issues": issues
        }

    def _extract_call_info(self, node: ast.Call) -> Optional[FunctionCallInfo]:
        """Extract information about a function call."""
        try:
            if isinstance(node.func, ast.Name):
                return FunctionCallInfo(
                    name=node.func.id,
                    module=None,
                    line=node.lineno,
                    args_count=len(node.args)
                )
            elif isinstance(node.func, ast.Attribute):
                module = None
                if isinstance(node.func.value, ast.Name):
                    module = node.func.value.id
                return FunctionCallInfo(
                    name=node.func.attr,
                    module=module,
                    line=node.lineno,
                    args_count=len(node.args)
                )
        except Exception:
            pass
        return None

    def _is_suspicious_call(self, call_info: FunctionCallInfo) -> bool:
        """Check if a call looks suspicious/hallucinated."""
        suspicious_names = {
            "get_data", "fetch_data", "load_data",
            "process", "transform", "convert",
            "helper", "utility", "wrapper",
        }

        # Very generic names without known module context are suspicious
        if call_info.name in suspicious_names and call_info.module is None:
            return True

        return False

    def _check_signatures(self, tree: ast.AST, code: str) -> Dict[str, Any]:
        """Check for incorrect function signatures."""
        issues = []
        signature_issues = []

        # Common signature mistakes
        signature_checks = {
            "print": {"max_args": 10},  # print can have many args
            "len": {"exact_args": 1},
            "range": {"min_args": 1, "max_args": 3},
            "open": {"min_args": 1, "max_args": 8},
            "map": {"min_args": 2},
            "filter": {"exact_args": 2},
            "zip": {"min_args": 1},
            "sorted": {"min_args": 1, "max_args": 4},
            "enumerate": {"min_args": 1, "max_args": 2},
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in signature_checks:
                        args_count = len(node.args) + len(node.keywords)
                        check = signature_checks[func_name]

                        if "exact_args" in check and args_count != check["exact_args"]:
                            signature_issues.append(f"{func_name}() expects {check['exact_args']} args, got {args_count}")
                        elif "min_args" in check and args_count < check["min_args"]:
                            signature_issues.append(f"{func_name}() expects at least {check['min_args']} args")
                        elif "max_args" in check and args_count > check["max_args"]:
                            signature_issues.append(f"{func_name}() expects at most {check['max_args']} args")

        for issue_desc in signature_issues:
            issues.append(Issue(
                severity=Severity.MEDIUM,
                category="signature_error",
                description=f"Incorrect function signature: {issue_desc}",
                suggestion="Check function documentation for correct usage"
            ))

        return {
            "signature_issues": signature_issues,
            "issues": issues
        }

    def _check_hallucination_patterns(self, code: str) -> Dict[str, Any]:
        """Check for common hallucination patterns in code."""
        issues = []
        patterns_found = []

        # Patterns that often indicate hallucinations
        hallucination_patterns = [
            # Made-up context managers
            (r'with\s+auto_\w+\(', "Auto-prefixed context manager"),
            # Fake decorators
            (r'@auto_\w+', "Auto-prefixed decorator"),
            (r'@smart_\w+', "Smart-prefixed decorator"),
            # Made-up class methods
            (r'\.auto_\w+\(', "Auto-prefixed method"),
            (r'\.smart_\w+\(', "Smart-prefixed method"),
            # Overly convenient APIs
            (r'\.from_any\(', "from_any method"),
            (r'\.to_any\(', "to_any method"),
            (r'\.auto_convert\(', "auto_convert method"),
            # Comments indicating uncertainty
            (r'#\s*TODO:\s*verify', "Uncertain code marker"),
            (r'#\s*Note:\s*not\s+sure', "Uncertainty marker"),
        ]

        for pattern, description in hallucination_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                patterns_found.append(description)

        if patterns_found:
            issues.append(Issue(
                severity=Severity.LOW,
                category="hallucination_pattern",
                description=f"Potential hallucination patterns found: {', '.join(patterns_found[:3])}",
                suggestion="Review code for made-up APIs or methods"
            ))

        return {
            "patterns_found": patterns_found,
            "issues": issues
        }

    def _calculate_score(self, issues: List[Issue]) -> float:
        """Calculate hallucination score based on issues found."""
        if not issues:
            return 1.0

        # Weight by severity
        weights = {
            Severity.CRITICAL: 0.4,
            Severity.HIGH: 0.25,
            Severity.MEDIUM: 0.15,
            Severity.LOW: 0.1,
            Severity.INFO: 0.05,
        }

        total_penalty = sum(weights.get(i.severity, 0.1) for i in issues)
        return max(0.0, 1.0 - min(total_penalty, 1.0))

    def get_import_validation_report(self, code: str) -> Dict[str, Any]:
        """Generate a detailed import validation report."""
        try:
            tree = ast.parse(code)
            return self._check_imports(tree, code)
        except SyntaxError as e:
            return {"error": str(e)}


def detect_hallucinations(code: str, strict: bool = False) -> EvaluationResult:
    """
    Quick function to detect hallucinations in code.

    Args:
        code: Generated code to check
        strict: Whether to use strict mode

    Returns:
        EvaluationResult
    """
    detector = HallucinationDetector(strict_mode=strict)
    task = EvaluationTask(
        task_id="quick_eval",
        input_text="",
        generated_output=code,
        language="python"
    )
    return detector.evaluate(task)
