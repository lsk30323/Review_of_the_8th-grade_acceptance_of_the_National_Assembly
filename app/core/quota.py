"""일일 호출 한도 가드.

외부 API 일일 무료 한도를 초과하기 전에 호출을 차단한다(자정 기준 일자 변경 시 리셋).
"""
from __future__ import annotations

import threading
from datetime import date
from typing import Callable


class QuotaExceededError(RuntimeError):
    """일일 호출 한도를 초과했을 때 발생."""


class QuotaGuard:
    """일일 호출 한도를 추적·예약하고 자정 경과 시 리셋한다 (스레드 안전)."""

    def __init__(self, daily_limit: int, *, today_fn: Callable[[], date] = date.today) -> None:
        """일일 한도와 날짜 제공 함수(테스트 주입용)로 초기화한다."""
        self._daily_limit = max(0, int(daily_limit))
        self._today_fn = today_fn
        self._lock = threading.Lock()
        self._day = today_fn()
        self._used = 0

    def _roll_over_if_needed(self) -> None:
        """Roll over if needed."""
        today = self._today_fn()
        if today != self._day:
            self._day = today
            self._used = 0

    def reserve(self, n: int = 1) -> None:
        """n건을 예약한다. 한도를 넘기면 QuotaExceededError."""
        if n <= 0:
            raise ValueError(f"예약 건수는 양수여야 합니다: {n}")
        with self._lock:
            self._roll_over_if_needed()
            if self._used + n > self._daily_limit:
                raise QuotaExceededError(
                    f"일일 호출 한도({self._daily_limit}) 초과: 사용 {self._used}, 요청 {n}"
                )
            self._used += n

    def try_reserve(self, n: int = 1) -> bool:
        """Try reserve."""
        try:
            self.reserve(n)
            return True
        except QuotaExceededError:
            return False

    @property
    def remaining(self) -> int:
        """Remaining."""
        with self._lock:
            self._roll_over_if_needed()
            return max(0, self._daily_limit - self._used)

    @property
    def used(self) -> int:
        """Used."""
        with self._lock:
            self._roll_over_if_needed()
            return self._used

    @property
    def daily_limit(self) -> int:
        """Daily limit."""
        return self._daily_limit
