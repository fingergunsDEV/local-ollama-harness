import time

import pytest

from app.safety.limits import LimitExceeded, RunBudget, ensure_read_size


def test_iteration_and_token_caps_are_hard_limits(settings):
    settings.max_iterations = 1; settings.max_output_tokens_per_turn = 64; settings.max_total_tokens_per_session = 64
    budget = RunBudget(settings)
    budget.take_iteration()
    with pytest.raises(LimitExceeded, match="MAX_ITERATIONS"): budget.take_iteration()
    budget = RunBudget(settings)
    with pytest.raises(LimitExceeded, match="MAX_OUTPUT_TOKENS_PER_TURN"): budget.record_output(65)


def test_wall_clock_and_file_read_caps(settings):
    settings.max_wall_clock_seconds = 1
    budget = RunBudget(settings, started_at=time.monotonic() - 2)
    with pytest.raises(LimitExceeded, match="MAX_WALL_CLOCK_SECONDS"): budget.check_time()
    settings.max_file_read_bytes = 4
    with pytest.raises(LimitExceeded, match="MAX_FILE_READ_BYTES"): ensure_read_size(5, settings)
