"""Code indexer for parsing and chunking source code files."""

import ast
import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Generator
from enum import Enum

logger = logging.getLogger(__name__)


class ChunkType(Enum):
    """Types of code chunks."""
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    CODE_BLOCK = "code_block"


@dataclass
class CodeChunk:
    """A chunk of code with metadata."""
    content: str
    chunk_type: ChunkType
    file_path: str
    language: str
    name: str  # function/class name or "module" for module-level
    start_line: int
    end_line: int
    chunk_id: str = ""
    parent_class: Optional[str] = None
    docstring: Optional[str] = None
    signature: Optional[str] = None
    imports: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Generate chunk ID after initialization."""
        if not self.chunk_id:
            self.chunk_id = self._generate_id()

    def _generate_id(self) -> str:
        """Generate a unique ID for this chunk."""
        content_hash = hashlib.md5(self.content.encode()).hexdigest()[:8]
        return f"{self.file_path}:{self.name}:{content_hash}"

    @property
    def token_estimate(self) -> int:
        """Estimate token count (rough approximation)."""
        return len(self.content.split()) + len(self.content) // 4


@dataclass
class IndexedFile:
    """A file that has been indexed."""
    file_path: str
    language: str
    chunks: List[CodeChunk]
    file_hash: str
    total_lines: int

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)


class PythonASTParser:
    """Parser for Python source code using AST."""

    def __init__(self, max_chunk_tokens: int = 1500):
        self.max_chunk_tokens = max_chunk_tokens

    def parse_file(self, file_path: str, content: str) -> List[CodeChunk]:
        """Parse a Python file and extract code chunks."""
        chunks = []
        lines = content.split('\n')

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
            # Fall back to simple chunking
            return self._simple_chunk(file_path, content, "python")

        # Extract module-level docstring and imports
        module_docstring = ast.get_docstring(tree)
        imports = self._extract_imports(tree)

        # Process top-level definitions
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                chunks.extend(self._process_class(node, file_path, lines, imports))
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                chunk = self._process_function(node, file_path, lines, imports)
                if chunk:
                    chunks.append(chunk)

        # Add module-level chunk if there's significant content
        module_chunk = self._create_module_chunk(
            file_path, content, lines, module_docstring, imports, tree
        )
        if module_chunk:
            chunks.insert(0, module_chunk)

        return chunks

    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract import statements from AST."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)
        return imports

    def _process_class(
        self,
        node: ast.ClassDef,
        file_path: str,
        lines: List[str],
        imports: List[str]
    ) -> List[CodeChunk]:
        """Process a class definition."""
        chunks = []

        # Get class source
        start_line = node.lineno - 1
        end_line = node.end_lineno or start_line + 1
        class_content = '\n'.join(lines[start_line:end_line])

        # Class docstring
        docstring = ast.get_docstring(node)

        # Create class chunk
        class_chunk = CodeChunk(
            content=class_content,
            chunk_type=ChunkType.CLASS,
            file_path=file_path,
            language="python",
            name=node.name,
            start_line=node.lineno,
            end_line=end_line,
            docstring=docstring,
            signature=self._get_class_signature(node),
            imports=imports,
            metadata={"bases": [self._get_name(base) for base in node.bases]}
        )
        chunks.append(class_chunk)

        # Process methods if class is too large
        if class_chunk.token_estimate > self.max_chunk_tokens:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_chunk = self._process_function(
                        item, file_path, lines, imports, parent_class=node.name
                    )
                    if method_chunk:
                        chunks.append(method_chunk)

        return chunks

    def _process_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: str,
        lines: List[str],
        imports: List[str],
        parent_class: Optional[str] = None
    ) -> Optional[CodeChunk]:
        """Process a function/method definition."""
        start_line = node.lineno - 1
        end_line = node.end_lineno or start_line + 1
        content = '\n'.join(lines[start_line:end_line])

        # Skip very small functions (likely just pass or ...)
        if len(content.strip()) < 20:
            return None

        docstring = ast.get_docstring(node)

        chunk_type = ChunkType.METHOD if parent_class else ChunkType.FUNCTION

        return CodeChunk(
            content=content,
            chunk_type=chunk_type,
            file_path=file_path,
            language="python",
            name=node.name,
            start_line=node.lineno,
            end_line=end_line,
            parent_class=parent_class,
            docstring=docstring,
            signature=self._get_function_signature(node),
            imports=imports,
            metadata={
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "decorators": [self._get_name(d) for d in node.decorator_list]
            }
        )

    def _create_module_chunk(
        self,
        file_path: str,
        content: str,
        lines: List[str],
        docstring: Optional[str],
        imports: List[str],
        tree: ast.AST
    ) -> Optional[CodeChunk]:
        """Create a module-level summary chunk."""
        # Get import section
        import_lines = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                start = node.lineno - 1
                end = node.end_lineno or start + 1
                import_lines.extend(lines[start:end])

        # Build module summary
        summary_parts = []
        if docstring:
            summary_parts.append(f'"""{docstring}"""')
        if import_lines:
            summary_parts.append('\n'.join(import_lines))

        if not summary_parts:
            return None

        summary = '\n\n'.join(summary_parts)

        return CodeChunk(
            content=summary,
            chunk_type=ChunkType.MODULE,
            file_path=file_path,
            language="python",
            name="module",
            start_line=1,
            end_line=len(import_lines) + (10 if docstring else 0),
            docstring=docstring,
            imports=imports,
            metadata={"file_name": Path(file_path).name}
        )

    def _get_function_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """Get function signature as string."""
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)

        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        signature = f"{prefix} {node.name}({', '.join(args)})"

        if node.returns:
            signature += f" -> {ast.unparse(node.returns)}"

        return signature

    def _get_class_signature(self, node: ast.ClassDef) -> str:
        """Get class signature as string."""
        bases = [self._get_name(base) for base in node.bases]
        if bases:
            return f"class {node.name}({', '.join(bases)})"
        return f"class {node.name}"

    def _get_name(self, node: ast.AST) -> str:
        """Get name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        return ast.unparse(node)

    def _simple_chunk(
        self,
        file_path: str,
        content: str,
        language: str
    ) -> List[CodeChunk]:
        """Simple line-based chunking for unparseable files."""
        lines = content.split('\n')
        chunks = []
        chunk_size = 50  # lines per chunk

        for i in range(0, len(lines), chunk_size):
            chunk_lines = lines[i:i + chunk_size]
            chunk_content = '\n'.join(chunk_lines)

            if chunk_content.strip():
                chunks.append(CodeChunk(
                    content=chunk_content,
                    chunk_type=ChunkType.CODE_BLOCK,
                    file_path=file_path,
                    language=language,
                    name=f"block_{i // chunk_size}",
                    start_line=i + 1,
                    end_line=min(i + chunk_size, len(lines))
                ))

        return chunks


class CodeIndexer:
    """Main indexer for processing codebases."""

    SUPPORTED_EXTENSIONS = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
        '.c': 'c',
        '.cpp': 'cpp',
        '.h': 'c',
        '.hpp': 'cpp',
    }

    IGNORE_DIRS = {
        '__pycache__', '.git', '.svn', 'node_modules', 'venv', '.venv',
        'env', '.env', 'dist', 'build', '.idea', '.vscode', 'target',
        '.pytest_cache', '.mypy_cache', '.ruff_cache', 'htmlcov',
        'egg-info', '.eggs'
    }

    IGNORE_FILES = {
        '.gitignore', '.dockerignore', 'requirements.txt', 'package-lock.json',
        'yarn.lock', 'Pipfile.lock', 'poetry.lock'
    }

    def __init__(self, max_chunk_tokens: int = 1500):
        self.max_chunk_tokens = max_chunk_tokens
        self.python_parser = PythonASTParser(max_chunk_tokens)
        self._indexed_files: Dict[str, IndexedFile] = {}

    def index_directory(
        self,
        directory: str,
        extensions: Optional[List[str]] = None
    ) -> List[IndexedFile]:
        """
        Index all supported files in a directory.

        Args:
            directory: Path to directory to index
            extensions: Optional list of extensions to include (e.g., ['.py', '.js'])

        Returns:
            List of IndexedFile objects
        """
        directory = Path(directory)
        if not directory.exists():
            raise ValueError(f"Directory does not exist: {directory}")

        indexed_files = []
        allowed_extensions = set(extensions) if extensions else set(self.SUPPORTED_EXTENSIONS.keys())

        for file_path in self._walk_directory(directory, allowed_extensions):
            try:
                indexed = self.index_file(str(file_path))
                if indexed:
                    indexed_files.append(indexed)
            except Exception as e:
                logger.error(f"Error indexing {file_path}: {e}")

        logger.info(f"Indexed {len(indexed_files)} files with {sum(f.chunk_count for f in indexed_files)} chunks")
        return indexed_files

    def index_file(self, file_path: str) -> Optional[IndexedFile]:
        """
        Index a single file.

        Args:
            file_path: Path to file to index

        Returns:
            IndexedFile or None if file cannot be indexed
        """
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return None

        ext = path.suffix.lower()
        language = self.SUPPORTED_EXTENSIONS.get(ext)
        if not language:
            logger.debug(f"Unsupported extension: {ext}")
            return None

        try:
            content = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            logger.warning(f"Cannot read file (encoding issue): {file_path}")
            return None

        # Calculate file hash for change detection
        file_hash = hashlib.md5(content.encode()).hexdigest()

        # Check if already indexed and unchanged
        if file_path in self._indexed_files:
            if self._indexed_files[file_path].file_hash == file_hash:
                return self._indexed_files[file_path]

        # Parse based on language
        if language == 'python':
            chunks = self.python_parser.parse_file(file_path, content)
        else:
            # For non-Python, use simple chunking
            chunks = self._simple_chunk(file_path, content, language)

        indexed_file = IndexedFile(
            file_path=file_path,
            language=language,
            chunks=chunks,
            file_hash=file_hash,
            total_lines=len(content.split('\n'))
        )

        self._indexed_files[file_path] = indexed_file
        return indexed_file

    def _walk_directory(
        self,
        directory: Path,
        allowed_extensions: set
    ) -> Generator[Path, None, None]:
        """Walk directory and yield file paths."""
        for root, dirs, files in os.walk(directory):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS and not d.startswith('.')]

            for file in files:
                if file in self.IGNORE_FILES:
                    continue

                path = Path(root) / file
                if path.suffix.lower() in allowed_extensions:
                    yield path

    def _simple_chunk(
        self,
        file_path: str,
        content: str,
        language: str
    ) -> List[CodeChunk]:
        """Simple chunking for non-Python files."""
        lines = content.split('\n')
        chunks = []
        chunk_size = 50

        for i in range(0, len(lines), chunk_size):
            chunk_lines = lines[i:i + chunk_size]
            chunk_content = '\n'.join(chunk_lines)

            if chunk_content.strip():
                chunks.append(CodeChunk(
                    content=chunk_content,
                    chunk_type=ChunkType.CODE_BLOCK,
                    file_path=file_path,
                    language=language,
                    name=f"block_{i // chunk_size}",
                    start_line=i + 1,
                    end_line=min(i + chunk_size, len(lines))
                ))

        return chunks

    def get_all_chunks(self) -> List[CodeChunk]:
        """Get all chunks from all indexed files."""
        chunks = []
        for indexed_file in self._indexed_files.values():
            chunks.extend(indexed_file.chunks)
        return chunks

    def clear_index(self) -> None:
        """Clear the index."""
        self._indexed_files.clear()
