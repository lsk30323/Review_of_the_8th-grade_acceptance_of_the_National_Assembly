from datetime import date

import pytest

from app.core.quota import QuotaExceededError, QuotaGuard


def test_reserve_and_remaining():
    """Reserve and remaining 동작을 검증한다."""
    q = QuotaGuard(3)
    q.reserve(2)
    assert q.used == 2
    assert q.remaining == 1
    with pytest.raises(QuotaExceededError):
        q.reserve(2)
    # 실패한 예약은 사용량을 늘리지 않는다
    assert q.used == 2


def test_try_reserve():
    """Try reserve 동작을 검증한다."""
    q = QuotaGuard(1)
    assert q.try_reserve(1) is True
    assert q.try_reserve(1) is False


def test_daily_rollover():
    """Daily rollover 동작을 검증한다."""
    days = [date(2026, 1, 1)]
    q = QuotaGuard(2, today_fn=lambda: days[0])
    q.reserve(2)
    assert q.remaining == 0
    days[0] = date(2026, 1, 2)
    assert q.remaining == 2  # 자정 경과 후 리셋
    q.reserve(1)
    assert q.used == 1


def test_zero_limit_blocks_everything():
    """Zero limit blocks everything 동작을 검증한다."""
    q = QuotaGuard(0)
    with pytest.raises(QuotaExceededError):
        q.reserve(1)


def test_reserve_rejects_non_positive():
    """Reserve rejects non positive 동작을 검증한다."""
    q = QuotaGuard(5)
    for bad in (0, -1, -10):
        with pytest.raises(ValueError):
            q.reserve(bad)
    assert q.used == 0  # 잘못된 예약은 사용량에 영향 없음
