import time
import pytest
from trend_rover.scrapers._utils import random_delay, USER_AGENTS, with_retry


def test_user_agents_non_empty():
    assert len(USER_AGENTS) >= 5
    for ua in USER_AGENTS:
        assert "Mozilla" in ua


def test_random_delay_within_bounds():
    for _ in range(20):
        start = time.monotonic()
        random_delay(min_s=0, max_s=0.01)
        elapsed = time.monotonic() - start
        assert elapsed < 0.1


def test_with_retry_succeeds_on_first_try():
    calls = []
    @with_retry(max_retries=3)
    def fn():
        calls.append(1)
        return "ok"
    assert fn() == "ok"
    assert len(calls) == 1


def test_with_retry_retries_on_exception():
    calls = []
    @with_retry(max_retries=3, base_delay=0)
    def fn():
        calls.append(1)
        if len(calls) < 3:
            raise ValueError("transient error")
        return "ok"
    assert fn() == "ok"
    assert len(calls) == 3


def test_with_retry_raises_after_max():
    @with_retry(max_retries=2, base_delay=0)
    def fn():
        raise RuntimeError("always fails")
    with pytest.raises(RuntimeError):
        fn()
