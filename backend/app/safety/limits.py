from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.config import Settings


class LimitExceeded(RuntimeError):
    """Raised immediately when a server-side resource cap is exceeded."""


@dataclass
class RunBudget:
    settings: Settings
    started_at: float = field(default_factory=time.monotonic)
    iterations: int = 0
    total_output_tokens: int = 0
    cancelled: bool = False

    def check_time(self) -> None:
        if self.cancelled:
            raise LimitExceeded("run cancelled by user")
        if time.monotonic() - self.started_at >= self.settings.max_wall_clock_seconds:
            raise LimitExceeded("MAX_WALL_CLOCK_SECONDS reached")

    def take_iteration(self) -> int:
        self.check_time()
        self.iterations += 1
        if self.iterations > self.settings.max_iterations:
            raise LimitExceeded("MAX_ITERATIONS reached")
        return self.settings.max_iterations - self.iterations

    def record_output(self, token_count: int) -> None:
        self.check_time()
        if token_count < 0:
            raise LimitExceeded("invalid negative output token count")
        if token_count > self.settings.max_output_tokens_per_turn:
            raise LimitExceeded("MAX_OUTPUT_TOKENS_PER_TURN reached")
        self.total_output_tokens += token_count
        if self.total_output_tokens > self.settings.max_total_tokens_per_session:
            raise LimitExceeded("MAX_TOTAL_TOKENS_PER_SESSION reached")

    @property
    def remaining_iterations(self) -> int:
        return max(0, self.settings.max_iterations - self.iterations)


def ensure_read_size(size: int, settings: Settings) -> None:
    if size > settings.max_file_read_bytes:
        raise LimitExceeded(f"file read is {size} bytes; MAX_FILE_READ_BYTES is {settings.max_file_read_bytes}")


def ensure_write_size(size: int, settings: Settings) -> None:
    if size > settings.max_file_write_bytes:
        raise LimitExceeded(f"file write is {size} bytes; MAX_FILE_WRITE_BYTES is {settings.max_file_write_bytes}")
