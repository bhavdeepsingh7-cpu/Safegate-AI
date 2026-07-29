"""Hardware-independent gate commands and an in-memory simulator."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Optional


class GateState(str, Enum):
    """Safe gate states exposed to the operator dashboard."""

    OPEN = "OPEN"
    LOCKED = "LOCKED"
    REVIEW = "REVIEW"


class GateCommand(str, Enum):
    """Controller commands reserved for a future hardware adapter."""

    OPEN = "OPEN"
    LOCK = "LOCK"
    REVIEW = "REVIEW"


class GateController(ABC):
    """Small interface shared by the simulator and future hardware adapters."""

    @abstractmethod
    def command(self, command: GateCommand, reason: str = "") -> GateState:
        """Send one safe gate command and return the resulting state."""

    def open(self, reason: str = "") -> GateState:
        return self.command(GateCommand.OPEN, reason)

    def lock(self, reason: str = "") -> GateState:
        return self.command(GateCommand.LOCK, reason)

    def review(self, reason: str = "") -> GateState:
        return self.command(GateCommand.REVIEW, reason)

    def apply_decision(
        self,
        decision_status: Optional[str],
        reason: str = "",
    ) -> GateState:
        """Map a verification outcome to a safe gate command.

        Only a completed access grant can open the gate. Every unrecognised,
        incomplete, stopped, or error state remains locked.
        """

        if decision_status == "ACCESS GRANTED":
            return self.open(reason)
        if decision_status == "MANAGER REVIEW":
            return self.review(reason)
        if decision_status == "ACCESS DENIED":
            return self.lock(reason)

        state_label = decision_status or "no worker or decision"
        return self.lock(reason or f"Fail-safe lock: {state_label}.")

    @abstractmethod
    def get_status(self) -> dict[str, str]:
        """Return dashboard-compatible controller status."""


class SimulatedGateController(GateController):
    """In-memory, fail-safe controller used until hardware is connected."""

    _COMMAND_STATES = {
        GateCommand.OPEN: GateState.OPEN,
        GateCommand.LOCK: GateState.LOCKED,
        GateCommand.REVIEW: GateState.REVIEW,
    }

    def __init__(self) -> None:
        self._lock = Lock()
        self.state = GateState.LOCKED
        self.last_command = GateCommand.LOCK
        self.timestamp = self._timestamp()
        self.reason = "Simulator initialised in its fail-safe locked state."

    def command(self, command: GateCommand, reason: str = "") -> GateState:
        """Record a simulated command without communicating with hardware."""

        with self._lock:
            self.state = self._COMMAND_STATES[command]
            self.last_command = command
            self.timestamp = self._timestamp()
            self.reason = reason
            return self.state

    def get_status(self) -> dict[str, str]:
        """Return a copy of the simulator state for the live dashboard."""

        with self._lock:
            return {
                "state": self.state.value,
                "last_command": self.last_command.value,
                "timestamp": self.timestamp,
                "reason": self.reason,
                "mode": "SIMULATOR",
            }

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()
