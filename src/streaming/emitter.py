"""Event emitter for real-time processing status updates."""

import asyncio
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ProcessingStep(str, Enum):
    """Processing steps that can be tracked."""
    INTENT_CLASSIFICATION = "intent_classification"
    SEMANTIC_SEARCH = "semantic_search"
    RERANKING = "reranking"
    LLM_GENERATION = "llm_generation"
    POST_PROCESSING = "post_processing"


class EventType(str, Enum):
    """Types of streaming events."""
    STEP_START = "step_start"
    STEP_COMPLETE = "step_complete"
    STEP_PROGRESS = "step_progress"
    ERROR = "error"
    DONE = "done"


@dataclass
class StreamEvent:
    """A streaming event to be sent to the client."""
    type: EventType
    step: Optional[ProcessingStep]
    data: Dict[str, Any]
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "step": self.step.value if self.step else None,
            "data": self.data,
            "timestamp": self.timestamp
        }


class EventEmitter:
    """
    Event emitter for streaming processing status to clients.

    Uses an async queue to buffer events for consumption by SSE endpoints.
    """

    def __init__(self):
        """Initialize the event emitter."""
        self._queue: asyncio.Queue = asyncio.Queue()
        self._step_start_times: Dict[ProcessingStep, int] = {}
        self._closed = False

    def start_step(
        self,
        step: ProcessingStep,
        message: str,
        **kwargs: Any
    ) -> None:
        """
        Emit a step start event.

        Args:
            step: The processing step starting
            message: Human-readable message
            **kwargs: Additional data to include in the event
        """
        if self._closed:
            return

        self._step_start_times[step] = int(time.time() * 1000)
        event = StreamEvent(
            type=EventType.STEP_START,
            step=step,
            data={"message": message, **kwargs}
        )
        self._put_event(event)

    def complete_step(
        self,
        step: ProcessingStep,
        message: str,
        **kwargs: Any
    ) -> None:
        """
        Emit a step complete event.

        Args:
            step: The processing step completed
            message: Human-readable message
            **kwargs: Additional data to include in the event
        """
        if self._closed:
            return

        duration_ms = None
        if step in self._step_start_times:
            duration_ms = int(time.time() * 1000) - self._step_start_times[step]
            del self._step_start_times[step]

        event = StreamEvent(
            type=EventType.STEP_COMPLETE,
            step=step,
            data={"message": message, "duration_ms": duration_ms, **kwargs}
        )
        self._put_event(event)

    def progress(
        self,
        step: ProcessingStep,
        message: str,
        **kwargs: Any
    ) -> None:
        """
        Emit a step progress event.

        Args:
            step: The processing step in progress
            message: Human-readable progress message
            **kwargs: Additional data to include in the event
        """
        if self._closed:
            return

        event = StreamEvent(
            type=EventType.STEP_PROGRESS,
            step=step,
            data={"message": message, **kwargs}
        )
        self._put_event(event)

    def done(
        self,
        result: str,
        usage: Optional[Dict[str, Any]] = None,
        capability_used: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Emit a done event indicating processing is complete.

        Args:
            result: The final result
            usage: Token usage information
            capability_used: The capability that was used
            **kwargs: Additional data to include in the event
        """
        if self._closed:
            return

        event = StreamEvent(
            type=EventType.DONE,
            step=None,
            data={
                "result": result,
                "usage": usage or {},
                "capability_used": capability_used,
                **kwargs
            }
        )
        self._put_event(event)
        self._closed = True

    def error(
        self,
        message: str,
        step: Optional[ProcessingStep] = None,
        **kwargs: Any
    ) -> None:
        """
        Emit an error event.

        Args:
            message: Error message
            step: Optional step where error occurred
            **kwargs: Additional data to include in the event
        """
        if self._closed:
            return

        event = StreamEvent(
            type=EventType.ERROR,
            step=step,
            data={"message": message, **kwargs}
        )
        self._put_event(event)
        self._closed = True

    def _put_event(self, event: StreamEvent) -> None:
        """Put an event on the queue (thread-safe for sync code)."""
        try:
            # Try to get the running loop - if we're in async context
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(self._queue.put_nowait, event)
        except RuntimeError:
            # No running loop - we're in sync code, use thread-safe approach
            try:
                self._queue.put_nowait(event)
            except Exception:
                pass  # Queue might be full or closed

    async def get_event(self) -> StreamEvent:
        """
        Get the next event from the queue.

        Returns:
            The next StreamEvent
        """
        return await self._queue.get()

    def is_closed(self) -> bool:
        """Check if the emitter is closed."""
        return self._closed


# Context variable for the current event emitter
_event_emitter: ContextVar[Optional[EventEmitter]] = ContextVar(
    'event_emitter',
    default=None
)


def get_emitter() -> Optional[EventEmitter]:
    """Get the current event emitter from context."""
    return _event_emitter.get()


def set_emitter(emitter: Optional[EventEmitter]) -> None:
    """Set the event emitter in context."""
    _event_emitter.set(emitter)


# Convenience functions that use context variable
def emit_start(step: ProcessingStep, message: str, **kwargs: Any) -> None:
    """Emit a step start event using the context emitter."""
    emitter = get_emitter()
    if emitter:
        emitter.start_step(step, message, **kwargs)


def emit_complete(step: ProcessingStep, message: str, **kwargs: Any) -> None:
    """Emit a step complete event using the context emitter."""
    emitter = get_emitter()
    if emitter:
        emitter.complete_step(step, message, **kwargs)


def emit_progress(step: ProcessingStep, message: str, **kwargs: Any) -> None:
    """Emit a step progress event using the context emitter."""
    emitter = get_emitter()
    if emitter:
        emitter.progress(step, message, **kwargs)


def emit_done(
    result: str,
    usage: Optional[Dict[str, Any]] = None,
    capability_used: Optional[str] = None,
    **kwargs: Any
) -> None:
    """Emit a done event using the context emitter."""
    emitter = get_emitter()
    if emitter:
        emitter.done(result, usage, capability_used, **kwargs)


def emit_error(
    message: str,
    step: Optional[ProcessingStep] = None,
    **kwargs: Any
) -> None:
    """Emit an error event using the context emitter."""
    emitter = get_emitter()
    if emitter:
        emitter.error(message, step, **kwargs)
