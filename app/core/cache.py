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
    def get(self, key: str) -> Optional[Any]: ...
    def set(self, key: str, value: Any) -> None: ...
    def clear(self) -> None: ...


class TTLCache:
    """TTL + LRU 상한을 가진 단순 인메모리 캐시 (스레드 안전)."""

    def __init__(
        self,
        ttl_seconds: int,
        *,
        max_size: int = 512,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = max(0, int(ttl_seconds))
        self._max_size = max(1, int(max_size))
        self._clock = clock
        self._lock = threading.Lock()
        self._store: "OrderedDict[str, tuple[float, Any]]" = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
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
        if self._ttl == 0:
            return
        with self._lock:
            self._store[key] = (self._clock() + self._ttl, value)
            self._store.move_to_end(key)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)
