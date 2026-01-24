"""Anthropic Claude API client with cost tracking and error handling."""

import json
import logging
from datetime import datetime, date
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any

import anthropic
from anthropic import APIError, RateLimitError, APIConnectionError

from src.config import config, PROJECT_ROOT

logger = logging.getLogger(__name__)

# Persistence directory and file
DATA_DIR = PROJECT_ROOT / "data" / "persistence"
USAGE_FILE = DATA_DIR / "usage_stats.json"


@dataclass
class UsageStats:
    """Track API usage statistics."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost: float = 0.0
    request_count: int = 0


@dataclass
class CostTracker:
    """Track and limit API costs."""
    daily_limit: float = field(default_factory=lambda: config.cost.daily_budget)
    daily_usage: float = 0.0
    last_reset: date = field(default_factory=date.today)
    usage_history: List[UsageStats] = field(default_factory=list)
    # Cumulative totals (persisted across sessions)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    total_requests: int = 0

    def __post_init__(self):
        """Load persisted data after initialization."""
        self._load()

    def _maybe_reset(self) -> None:
        """Reset daily usage if it's a new day."""
        today = date.today()
        if today > self.last_reset:
            logger.info(f"Resetting daily usage. Previous: ${self.daily_usage:.4f}")
            self.daily_usage = 0.0
            self.last_reset = today

    def check_budget(self, estimated_cost: float) -> bool:
        """Check if we have budget for the estimated cost."""
        self._maybe_reset()
        return (self.daily_usage + estimated_cost) <= self.daily_limit

    def record_usage(
        self, input_tokens: int, output_tokens: int, model: str
    ) -> float:
        """Record API usage and return the cost."""
        self._maybe_reset()

        pricing = config.cost.pricing.get(model, {"input": 0.003, "output": 0.015})
        cost = (
            (input_tokens / 1000) * pricing["input"] +
            (output_tokens / 1000) * pricing["output"]
        )

        self.daily_usage += cost

        stats = UsageStats(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_cost=cost,
            request_count=1
        )
        self.usage_history.append(stats)

        # Update cumulative totals
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost
        self.total_requests += 1

        # Persist to disk
        self._save()

        logger.info(
            f"API cost: ${cost:.4f} | Daily total: ${self.daily_usage:.2f}/{self.daily_limit:.2f}"
        )

        return cost

    def get_remaining_budget(self) -> float:
        """Get remaining daily budget."""
        self._maybe_reset()
        return self.daily_limit - self.daily_usage

    def _save(self) -> None:
        """Save usage stats to disk."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "total_input_tokens": self.total_input_tokens,
                "total_output_tokens": self.total_output_tokens,
                "total_cost": self.total_cost,
                "total_requests": self.total_requests,
                "daily_usage": self.daily_usage,
                "last_reset": self.last_reset.isoformat(),
            }
            with open(USAGE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save usage stats: {e}")

    def _load(self) -> None:
        """Load usage stats from disk."""
        try:
            if USAGE_FILE.exists():
                with open(USAGE_FILE, 'r') as f:
                    data = json.load(f)
                self.total_input_tokens = data.get("total_input_tokens", 0)
                self.total_output_tokens = data.get("total_output_tokens", 0)
                self.total_cost = data.get("total_cost", 0.0)
                self.total_requests = data.get("total_requests", 0)
                # Load daily usage and check if it needs reset
                saved_date = date.fromisoformat(data.get("last_reset", date.today().isoformat()))
                if saved_date == date.today():
                    self.daily_usage = data.get("daily_usage", 0.0)
                    self.last_reset = saved_date
                else:
                    # New day, reset daily usage
                    self.daily_usage = 0.0
                    self.last_reset = date.today()
                logger.info(f"Loaded usage stats: {self.total_requests} requests, ${self.total_cost:.4f} total")
        except Exception as e:
            logger.warning(f"Failed to load usage stats: {e}")


@dataclass
class Message:
    """A message in a conversation."""
    role: str  # "user" or "assistant"
    content: str


class ClaudeClient:
    """Client for interacting with Anthropic's Claude API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        max_retries: int = 3
    ):
        self.api_key = api_key or config.anthropic.api_key
        self.default_model = default_model or config.anthropic.default_model
        self.max_retries = max_retries
        self.cost_tracker = CostTracker()

        if not self.api_key:
            raise ValueError("Anthropic API key is required")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        logger.info(f"ClaudeClient initialized with model: {self.default_model}")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        messages: Optional[List[Message]] = None,
    ) -> str:
        """
        Generate a response from Claude.

        Args:
            prompt: The user prompt (ignored if messages provided)
            system_prompt: Optional system prompt for context
            model: Model to use (defaults to config)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            messages: Optional list of messages for multi-turn conversation

        Returns:
            Generated text response
        """
        model = model or self.default_model
        max_tokens = max_tokens or config.anthropic.max_tokens
        temperature = temperature if temperature is not None else config.anthropic.temperature

        # Build messages list
        if messages:
            api_messages = [{"role": m.role, "content": m.content} for m in messages]
        else:
            api_messages = [{"role": "user", "content": prompt}]

        # Make API call with retries
        for attempt in range(self.max_retries):
            try:
                kwargs: Dict[str, Any] = {
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": api_messages,
                }

                if system_prompt:
                    kwargs["system"] = system_prompt

                response = self.client.messages.create(**kwargs)

                # Track usage
                if hasattr(response, "usage"):
                    self.cost_tracker.record_usage(
                        input_tokens=response.usage.input_tokens,
                        output_tokens=response.usage.output_tokens,
                        model=model
                    )

                # Extract text content
                if response.content and len(response.content) > 0:
                    return response.content[0].text

                return ""

            except RateLimitError as e:
                logger.warning(f"Rate limited (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                import time
                time.sleep(2 ** attempt)  # Exponential backoff

            except APIConnectionError as e:
                logger.warning(f"Connection error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                import time
                time.sleep(1)

            except APIError as e:
                logger.error(f"API error: {e}")
                raise

        return ""

    def generate_with_budget_check(
        self,
        prompt: str,
        estimated_tokens: int = 1000,
        **kwargs
    ) -> Optional[str]:
        """Generate response only if within budget."""
        model = kwargs.get("model", self.default_model)
        pricing = config.cost.pricing.get(model, {"input": 0.003, "output": 0.015})
        estimated_cost = (estimated_tokens / 1000) * (pricing["input"] + pricing["output"])

        if not self.cost_tracker.check_budget(estimated_cost):
            logger.warning(
                f"Budget exceeded. Remaining: ${self.cost_tracker.get_remaining_budget():.2f}"
            )
            return None

        return self.generate(prompt, **kwargs)

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics (persisted across sessions)."""
        return {
            "daily_usage": self.cost_tracker.daily_usage,
            "daily_limit": self.cost_tracker.daily_limit,
            "remaining": self.cost_tracker.get_remaining_budget(),
            "request_count": self.cost_tracker.total_requests,
            # Fields expected by frontend (cumulative totals)
            "total_requests": self.cost_tracker.total_requests,
            "input_tokens": self.cost_tracker.total_input_tokens,
            "output_tokens": self.cost_tracker.total_output_tokens,
            "total_tokens": self.cost_tracker.total_input_tokens + self.cost_tracker.total_output_tokens,
            "total_cost": self.cost_tracker.total_cost,
        }

    def get_last_request_usage(self) -> Dict[str, Any]:
        """Get usage stats for the last request only."""
        if not self.cost_tracker.usage_history:
            return {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
            }

        last = self.cost_tracker.usage_history[-1]
        return {
            "input_tokens": last.input_tokens,
            "output_tokens": last.output_tokens,
            "total_tokens": last.input_tokens + last.output_tokens,
            "cost": last.total_cost,
        }


# Convenience function for quick generation
def generate(prompt: str, **kwargs) -> str:
    """Quick generation using default client."""
    client = ClaudeClient()
    return client.generate(prompt, **kwargs)
