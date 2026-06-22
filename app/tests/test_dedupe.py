from app.adapters.base import NormalizedResult
from app.core.dedupe import dedupe_results, normalize_url


def _r(url, score=0.0, source="naver_blog"):
    """테스트용 NormalizedResult를 만든다."""
    return NormalizedResult(
        title="국회직 8급 합격후기",
        url=url,
        snippet="국회직 8급 합격수기",
        source=source,
        source_label="네이버 블로그",
        score=score,
    )


def test_normalize_url_tracking_scheme_slash_fragment():
    """Normalize url tracking scheme slash fragment 동작을 검증한다."""
    a = normalize_url("http://www.Blog.naver.com/u/1/?utm_source=x&a=2#frag")
    b = normalize_url("https://blog.naver.com/u/1?a=2")
    assert a == b == "https://blog.naver.com/u/1?a=2"


def test_normalize_url_empty():
    """Normalize url empty 동작을 검증한다."""
    assert normalize_url("") == ""


def test_dedupe_keeps_highest_score_and_merges_sources():
    """Dedupe keeps highest score and merges sources 동작을 검증한다."""
    out = dedupe_results([
        _r("https://x.com/a", score=1.0, source="naver_blog"),
        _r("https://x.com/a/", score=2.0, source="naver_cafe"),
    ])
    assert len(out) == 1
    assert out[0].score == 2.0
    assert set(out[0].extra["merged_sources"]) == {"naver_blog", "naver_cafe"}


def test_dedupe_distinct_urls_preserved():
    """Dedupe distinct urls preserved 동작을 검증한다."""
    out = dedupe_results([_r("https://x.com/a"), _r("https://x.com/b")])
    assert len(out) == 2
