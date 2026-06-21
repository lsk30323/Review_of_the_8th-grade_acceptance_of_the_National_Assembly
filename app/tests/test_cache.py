from app.core.cache import Cache, TTLCache


def test_set_get():
    c = TTLCache(100)
    c.set("k", [1, 2, 3])
    assert c.get("k") == [1, 2, 3]
    assert c.get("missing") is None


def test_ttl_expiry():
    now = [0.0]
    c = TTLCache(10, clock=lambda: now[0])
    c.set("k", "v")
    assert c.get("k") == "v"
    now[0] = 11.0
    assert c.get("k") is None


def test_lru_eviction():
    c = TTLCache(100, max_size=2)
    c.set("a", 1)
    c.set("b", 2)
    c.set("c", 3)  # a 가 밀려난다
    assert c.get("a") is None
    assert c.get("b") == 2
    assert c.get("c") == 3


def test_ttl_zero_disables_cache():
    c = TTLCache(0)
    c.set("k", "v")
    assert c.get("k") is None


def test_clear():
    c = TTLCache(100)
    c.set("k", "v")
    c.clear()
    assert c.get("k") is None


def test_satisfies_cache_protocol():
    assert isinstance(TTLCache(10), Cache)
