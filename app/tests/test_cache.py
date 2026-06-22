from app.core.cache import Cache, TTLCache


def test_set_get():
    """Set get 동작을 검증한다."""
    c = TTLCache(100)
    c.set("k", [1, 2, 3])
    assert c.get("k") == [1, 2, 3]
    assert c.get("missing") is None


def test_ttl_expiry():
    """Ttl expiry 동작을 검증한다."""
    now = [0.0]
    c = TTLCache(10, clock=lambda: now[0])
    c.set("k", "v")
    assert c.get("k") == "v"
    now[0] = 11.0
    assert c.get("k") is None


def test_lru_eviction():
    """Lru eviction 동작을 검증한다."""
    c = TTLCache(100, max_size=2)
    c.set("a", 1)
    c.set("b", 2)
    c.set("c", 3)  # a 가 밀려난다
    assert c.get("a") is None
    assert c.get("b") == 2
    assert c.get("c") == 3


def test_ttl_zero_disables_cache():
    """Ttl zero disables cache 동작을 검증한다."""
    c = TTLCache(0)
    c.set("k", "v")
    assert c.get("k") is None


def test_clear():
    """Clear 동작을 검증한다."""
    c = TTLCache(100)
    c.set("k", "v")
    c.clear()
    assert c.get("k") is None


def test_satisfies_cache_protocol():
    """Satisfies cache protocol 동작을 검증한다."""
    assert isinstance(TTLCache(10), Cache)
