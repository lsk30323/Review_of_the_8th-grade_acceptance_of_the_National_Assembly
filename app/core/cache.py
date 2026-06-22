"""인메모리 TTL 캐시 (쿼터 절약).

Cache 프로토콜만 충족하면 SQLite 등 영속 캐시로 교체할 수 있다(향후 옵션).
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Optional, Protocol, runtime_checkable


@runtime_checkable
class Cache(Protocol):
    """캐시 백엔드 인터페이스(이것만 충족하면 교체 가능)."""

    def get(self, key: str) -> Optional[Any]:
        """키로 값을 조회한다(없거나 만료면 None)."""

    def set(self, key: str, value: Any) -> None:
        """키-값을 저장한다."""

    def clear(self) -> None:
        """모든 항목을 비운다."""


class TTLCache:
    """TTL + LRU 상한을 가진 단순 인메모리 캐시 (스레드 안전)."""

    def __init__(
        self,
        ttl_seconds: int,
        *,
        max_size: int = 512,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """ttl_seconds(0이면 비활성)와 LRU 상한, 시계 함수로 초기화한다."""
        self._ttl = max(0, int(ttl_seconds))
        self._max_size = max(1, int(max_size))
        self._clock = clock
        self._lock = threading.Lock()
        self._store: "OrderedDict[str, tuple[float, Any]]" = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        """키로 값을 조회한다. 없거나 TTL 만료면 None."""
        if self._ttl == 0:
            return None
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            expires_at, value = item
            if self._clock() >= expires_at:
                self._store.pop(key, None)
                return None
            self._store.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        """키-값을 저장한다(TTL=0이면 무시, 상한 초과 시 LRU 축출)."""
        if self._ttl == 0:
            return
        with self._lock:
            self._store[key] = (self._clock() + self._ttl, value)
            self._store.move_to_end(key)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)

    def clear(self) -> None:
        """모든 항목을 제거한다."""
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        """현재 저장된 항목 수."""
        with self._lock:
            return len(self._store)
