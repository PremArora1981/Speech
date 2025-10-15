"""Interrupt manager for barge-in handling across pipeline stages."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable, Optional

from backend.utils.logging import get_logger


class InterruptReason(str, Enum):
    """Reasons for interrupting pipeline execution."""

    USER_BARGE_IN = "user_barge_in"  # User started speaking
    TIMEOUT = "timeout"  # Operation exceeded time limit
    ERROR = "error"  # Error occurred
    MANUAL = "manual"  # Manual cancellation
    REPLACED = "replaced"  # Superseded by newer request


@dataclass
class InterruptEvent:
    """Event representing a pipeline interruption."""

    session_id: str
    turn_id: str
    reason: InterruptReason
    timestamp: datetime
    stage: Optional[str] = None  # asr, llm, translation, tts
    metadata: Optional[dict] = None


class InterruptManager:
    """
    Manages interrupt signals for barge-in handling across pipeline stages.

    Features:
    - Per-session, per-turn interrupt tracking
    - Graceful cancellation of async operations
    - Cleanup callbacks for resource release
    - Interrupt event logging

    Usage:
        manager = InterruptManager()

        # Start a turn
        turn_id = manager.start_turn(session_id)

        # Check if interrupted during processing
        if manager.is_interrupted(session_id, turn_id):
            return  # Exit early

        # Register cleanup callback
        manager.register_cleanup(session_id, turn_id, cleanup_fn)

        # Interrupt from another context (e.g., WebSocket)
        manager.interrupt(session_id, turn_id, InterruptReason.USER_BARGE_IN)
    """

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        # Track active turns: {session_id: {turn_id: InterruptState}}
        self._active_turns: dict[str, dict[str, "InterruptState"]] = {}
        # Global lock for thread-safe operations
        self._lock = asyncio.Lock()

    def start_turn(self, session_id: str, turn_id: Optional[str] = None) -> str:
        """
        Start tracking a new conversation turn.

        Args:
            session_id: Session identifier
            turn_id: Optional turn identifier (auto-generated if not provided)

        Returns:
            Turn ID for this conversation turn
        """
        if turn_id is None:
            turn_id = f"{session_id}_{datetime.utcnow().timestamp()}"

        if session_id not in self._active_turns:
            self._active_turns[session_id] = {}

        self._active_turns[session_id][turn_id] = InterruptState()

        self.logger.debug(
            "Started turn tracking",
            extra={"session_id": session_id, "turn_id": turn_id},
        )
        return turn_id

    def is_interrupted(self, session_id: str, turn_id: str) -> bool:
        """
        Check if a turn has been interrupted.

        Args:
            session_id: Session identifier
            turn_id: Turn identifier

        Returns:
            True if turn has been interrupted, False otherwise
        """
        state = self._get_state(session_id, turn_id)
        return state.interrupted if state else False

    def get_interrupt_event(
        self, session_id: str, turn_id: str
    ) -> Optional[InterruptEvent]:
        """
        Get interrupt event details for a turn.

        Args:
            session_id: Session identifier
            turn_id: Turn identifier

        Returns:
            InterruptEvent if interrupted, None otherwise
        """
        state = self._get_state(session_id, turn_id)
        return state.event if state else None

    async def interrupt(
        self,
        session_id: str,
        turn_id: str,
        reason: InterruptReason,
        stage: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Interrupt an active turn.

        Args:
            session_id: Session identifier
            turn_id: Turn identifier
            reason: Reason for interruption
            stage: Current pipeline stage (asr, llm, translation, tts)
            metadata: Additional metadata
        """
        async with self._lock:
            state = self._get_state(session_id, turn_id)
            if not state:
                self.logger.warning(
                    "Attempted to interrupt non-existent turn",
                    extra={"session_id": session_id, "turn_id": turn_id},
                )
                return

            if state.interrupted:
                self.logger.debug(
                    "Turn already interrupted",
                    extra={"session_id": session_id, "turn_id": turn_id},
                )
                return

            # Mark as interrupted
            state.interrupted = True
            state.event = InterruptEvent(
                session_id=session_id,
                turn_id=turn_id,
                reason=reason,
                timestamp=datetime.utcnow(),
                stage=stage,
                metadata=metadata,
            )

            self.logger.info(
                "Turn interrupted",
                extra={
                    "session_id": session_id,
                    "turn_id": turn_id,
                    "reason": reason.value,
                    "stage": stage,
                },
            )

            # Cancel async task if registered
            if state.task:
                state.task.cancel()

            # Execute cleanup callbacks
            for cleanup_fn in state.cleanup_callbacks:
                try:
                    if asyncio.iscoroutinefunction(cleanup_fn):
                        await cleanup_fn()
                    else:
                        cleanup_fn()
                except Exception as e:
                    self.logger.error(
                        f"Cleanup callback failed: {e}",
                        extra={"session_id": session_id, "turn_id": turn_id},
                    )

    def register_cleanup(
        self, session_id: str, turn_id: str, callback: Callable
    ) -> None:
        """
        Register a cleanup callback to execute on interrupt.

        Args:
            session_id: Session identifier
            turn_id: Turn identifier
            callback: Cleanup function (sync or async)
        """
        state = self._get_state(session_id, turn_id)
        if state:
            state.cleanup_callbacks.append(callback)

    def register_task(
        self, session_id: str, turn_id: str, task: asyncio.Task
    ) -> None:
        """
        Register an async task for automatic cancellation on interrupt.

        Args:
            session_id: Session identifier
            turn_id: Turn identifier
            task: Asyncio task to cancel on interrupt
        """
        state = self._get_state(session_id, turn_id)
        if state:
            state.task = task

    def finish_turn(self, session_id: str, turn_id: str) -> None:
        """
        Mark a turn as finished and clean up tracking.

        Args:
            session_id: Session identifier
            turn_id: Turn identifier
        """
        if session_id in self._active_turns:
            if turn_id in self._active_turns[session_id]:
                del self._active_turns[session_id][turn_id]
                self.logger.debug(
                    "Finished turn tracking",
                    extra={"session_id": session_id, "turn_id": turn_id},
                )

            # Clean up session if no active turns
            if not self._active_turns[session_id]:
                del self._active_turns[session_id]

    def interrupt_all_session_turns(
        self, session_id: str, reason: InterruptReason
    ) -> None:
        """
        Interrupt all active turns for a session.

        Args:
            session_id: Session identifier
            reason: Reason for interruption
        """
        if session_id not in self._active_turns:
            return

        turn_ids = list(self._active_turns[session_id].keys())
        for turn_id in turn_ids:
            asyncio.create_task(
                self.interrupt(session_id, turn_id, reason)
            )

    def _get_state(self, session_id: str, turn_id: str) -> Optional["InterruptState"]:
        """Get interrupt state for a turn."""
        if session_id not in self._active_turns:
            return None
        return self._active_turns[session_id].get(turn_id)

    def get_active_turns(self, session_id: str) -> list[str]:
        """Get list of active turn IDs for a session."""
        if session_id not in self._active_turns:
            return []
        return list(self._active_turns[session_id].keys())


@dataclass
class InterruptState:
    """Internal state for a conversation turn."""

    interrupted: bool = False
    event: Optional[InterruptEvent] = None
    task: Optional[asyncio.Task] = None
    cleanup_callbacks: list[Callable] = None

    def __post_init__(self):
        if self.cleanup_callbacks is None:
            self.cleanup_callbacks = []


class InterruptibleOperation:
    """
    Context manager for interruptible operations.

    Usage:
        async with InterruptibleOperation(manager, session_id, turn_id, "llm") as op:
            if op.should_continue():
                result = await long_running_operation()
    """

    def __init__(
        self,
        manager: InterruptManager,
        session_id: str,
        turn_id: str,
        stage: str,
    ):
        self.manager = manager
        self.session_id = session_id
        self.turn_id = turn_id
        self.stage = stage

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Check if interrupted during operation
        if self.manager.is_interrupted(self.session_id, self.turn_id):
            # Suppress exceptions if interrupted
            return True
        return False

    def should_continue(self) -> bool:
        """Check if operation should continue or exit early."""
        return not self.manager.is_interrupted(self.session_id, self.turn_id)

    def check_or_raise(self) -> None:
        """Raise InterruptedError if turn has been interrupted."""
        if self.manager.is_interrupted(self.session_id, self.turn_id):
            event = self.manager.get_interrupt_event(self.session_id, self.turn_id)
            raise InterruptedError(
                f"Operation interrupted: {event.reason if event else 'unknown'}"
            )


__all__ = [
    "InterruptManager",
    "InterruptReason",
    "InterruptEvent",
    "InterruptibleOperation",
]
