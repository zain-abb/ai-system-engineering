"""Streaming module for real-time event emission."""

from src.streaming.emitter import (
    ProcessingStep,
    EventType,
    StreamEvent,
    EventEmitter,
    get_emitter,
    set_emitter,
    emit_start,
    emit_complete,
    emit_progress,
    emit_done,
    emit_error,
)

__all__ = [
    "ProcessingStep",
    "EventType",
    "StreamEvent",
    "EventEmitter",
    "get_emitter",
    "set_emitter",
    "emit_start",
    "emit_complete",
    "emit_progress",
    "emit_done",
    "emit_error",
]
