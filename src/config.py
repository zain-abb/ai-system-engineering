"""Configuration management for SE-Agent."""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"


@dataclass
class AnthropicConfig:
    """Anthropic API configuration."""
    api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    default_model: str = "claude-sonnet-4-20250514"
    fast_model: str = "claude-3-haiku-20240307"
    max_tokens: int = 4096
    temperature: float = 0.7


@dataclass
class ChromaConfig:
    """ChromaDB configuration."""
    host: str = field(default_factory=lambda: os.getenv("CHROMA_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("CHROMA_PORT", "8001")))
    collection_name: str = "codebase"


@dataclass
class CostConfig:
    """API cost management configuration."""
    daily_budget: float = field(
        default_factory=lambda: float(os.getenv("DAILY_API_BUDGET", "10.0"))
    )
    # Pricing per 1K tokens (as of 2025)
    pricing: dict = field(default_factory=lambda: {
        "claude-opus-4-20250514": {"input": 0.015, "output": 0.075},
        "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
        "claude-3-5-haiku-20241022": {"input": 0.0008, "output": 0.004},
        "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
    })


@dataclass
class UploadConfig:
    """File upload configuration."""
    upload_directory: str = field(
        default_factory=lambda: os.getenv("UPLOAD_DIRECTORY", "/app/uploads")
    )
    max_file_size_mb: int = 10
    max_total_size_mb: int = 100


@dataclass
class AppConfig:
    """Main application configuration."""
    debug: bool = field(
        default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true"
    )
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    host: str = "0.0.0.0"
    api_port: int = 8000


@dataclass
class Config:
    """Combined configuration."""
    anthropic: AnthropicConfig = field(default_factory=AnthropicConfig)
    chroma: ChromaConfig = field(default_factory=ChromaConfig)
    cost: CostConfig = field(default_factory=CostConfig)
    app: AppConfig = field(default_factory=AppConfig)
    upload: UploadConfig = field(default_factory=UploadConfig)

    def validate(self) -> bool:
        """Validate required configuration."""
        if not self.anthropic.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        return True


# Global config instance
config = Config()
