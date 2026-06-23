from datetime import date

from app.adapters.base import NormalizedResult
from app.core.ranking import is_noise, rank_results, score_result

TODAY = date(2026, 6, 21)


def _r(title, snippet, url="https://blog.naver.com/u/x", source="naver_blog", posted=None):
    """테스트용 NormalizedResult를 만든다."""
    return NormalizedResult(
        title=title, snippet=snippet, url=url,
        source=source, source_label="네이버 블로그", posted_at=posted,
    )


def test_noise_when_no_core_keyword():
    """Noise when no core keyword 동작을 검증한다."""
    assert is_noise(_r("서울시 7급 합격후기", "공부법 정리")) is True


def test_noise_ad_domain():
    """Noise ad domain 동작을 검증한다."""
    r = _r("국회직 8급 합격후기", "수강", url="https://eduwill.net/abc", source="naver_web")
    assert is_noise(r) is True


def test_noise_gated_cafe_domain():
    """회원 전용(게이트) 네이버 카페 URL은 공개 URL이 아니므로 제외한다."""
    r = _r("국회직 8급 합격후기", "국회직 8급 합격 공부법", url="https://cafe.naver.com/gosipass/123")
    assert is_noise(r) is True
    m = _r("국회직 8급 합격후기", "국회직 8급 합격 공부법", url="https://m.cafe.naver.com/gosipass/123")
    assert is_noise(m) is True


def test_rank_drops_gated_cafe_links():
    """랭킹 단계에서 카페(게이트) 링크가 제외되고 공개 URL만 남는다."""
    public = _r("국회직 8급 합격후기", "국회직 8급 합격 공부법", url="https://blog.naver.com/a", posted="2026-05-01")
    gated = _r("국회직 8급 합격후기", "국회직 8급 합격 공부법", url="https://cafe.naver.com/x/1", posted="2026-05-01")
    ranked = rank_results([public, gated], today=TODAY)
    urls = [x.url for x in ranked]
    assert "https://blog.naver.com/a" in urls
    assert all("cafe.naver.com" not in u for u in urls)


def test_allowlisted_cafe_not_noise():
    """허용목록(공개 카페) 글은 통과, 목록에 없는 카페는 계속 제외한다."""
    allow = frozenset({"goodcafe"})
    ok = _r("국회직 8급 합격후기", "국회직 8급 합격 공부법", url="https://cafe.naver.com/goodcafe/10")
    assert is_noise(ok, cafe_allowlist=allow) is False
    other = _r("국회직 8급 합격후기", "국회직 8급 합격 공부법", url="https://cafe.naver.com/other/10")
    assert is_noise(other, cafe_allowlist=allow) is True
    # 신형 ca-fe URL은 slug 식별 불가 → 게이트 처리
    cafe_new = _r("국회직 8급 합격후기", "국회직 8급 합격 공부법", url="https://cafe.naver.com/ca-fe/cafes/123/articles/1")
    assert is_noise(cafe_new, cafe_allowlist=allow) is True


def test_rank_keeps_allowlisted_cafe():
    """랭킹 단계에서 허용목록 카페 글은 남는다."""
    pub = _r("국회직 8급 합격후기", "국회직 8급 합격 공부법", url="https://cafe.naver.com/goodcafe/1", posted="2026-05-01")
    ranked = rank_results([pub], today=TODAY, cafe_allowlist=frozenset({"goodcafe"}))
    assert any("cafe.naver.com/goodcafe" in x.url for x in ranked)


def test_noise_heavy_ads_without_intent_title():
    """Noise heavy ads without intent title 동작을 검증한다."""
    r = _r("국회직 8급 대비반 안내", "수강료 할인 이벤트 등록금 환급")
    assert is_noise(r) is True


def test_good_post_not_noise():
    """Good post not noise 동작을 검증한다."""
    assert is_noise(_r("국회직 8급 합격후기", "국회직 8급 합격 공부법")) is False


def test_score_title_core_and_intent():
    """Score title core and intent 동작을 검증한다."""
    r = _r("국회직 8급 합격후기", "국회직 8급 합격 공부법", posted=TODAY.isoformat())
    s = score_result(r, today=TODAY)
    assert s >= 2.0
    assert "title_core_and_intent" in r.extra["score_breakdown"]


def test_recency_helps_score():
    """Recency helps score 동작을 검증한다."""
    recent = _r("국회직 8급 합격후기", "국회직 8급 합격", posted="2026-05-01")
    old = _r("국회직 8급 합격후기", "국회직 8급 합격", posted="2018-01-01")
    assert score_result(recent, today=TODAY) > score_result(old, today=TODAY)


def test_rank_filters_noise_and_sorts_by_score():
    """Rank filters noise and sorts by score 동작을 검증한다."""
    noise = _r("서울시 7급 후기", "공부")  # no core -> dropped
    strong = _r("국회직 8급 합격후기", "국회직 8급 합격 공부법", url="https://blog.naver.com/a", posted="2026-05-01")
    weak = _r("국회직 8급 정보", "국회직 8급 채용", url="https://blog.naver.com/b", posted="2019-01-01")
    ranked = rank_results([noise, weak, strong], today=TODAY)
    urls = [x.url for x in ranked]
    assert "https://blog.naver.com/a" in urls
    assert all("7급" not in x.title for x in ranked)
    assert ranked[0].score >= ranked[-1].score


def test_rank_sort_by_date():
    """Rank sort by date 동작을 검증한다."""
    a = _r("국회직 8급 합격후기", "국회직 8급 합격", url="https://blog.naver.com/a", posted="2024-01-01")
    b = _r("국회직 8급 합격후기", "국회직 8급 합격", url="https://blog.naver.com/b", posted="2026-01-01")
    ranked = rank_results([a, b], sort="date", today=TODAY)
    assert ranked[0].url == "https://blog.naver.com/b"
