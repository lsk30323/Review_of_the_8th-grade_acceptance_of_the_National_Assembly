from app.core.query_strategy import (
    build_query_variants,
    has_core_signal,
    has_intent_signal,
    site_restricted_variants,
)


def test_core_only_appends_intent():
    """Core only appends intent 동작을 검증한다."""
    v = build_query_variants("국회직 8급", max_variants=4)
    assert "국회직 8급" in v
    assert any("합격후기" in x for x in v)


def test_no_core_adds_core_term():
    """No core adds core term 동작을 검증한다."""
    v = build_query_variants("면접 분위기", max_variants=6)
    assert any("국회직 8급" in x for x in v)
    assert any("국회사무처 8급" in x for x in v)


def test_empty_query_uses_default_combo():
    """Empty query uses default combo 동작을 검증한다."""
    v = build_query_variants("", max_variants=3)
    assert "국회직 8급 합격후기" in v


def test_respects_max_variants():
    """Respects max variants 동작을 검증한다."""
    v = build_query_variants("국회직 8급", max_variants=2)
    assert len(v) == 2


def test_no_duplicates():
    """No duplicates 동작을 검증한다."""
    v = build_query_variants("국회직 8급 합격후기", max_variants=8)
    assert len(v) == len(set(v))


def test_signal_detection():
    """Signal detection 동작을 검증한다."""
    assert has_core_signal("국회사무처 8급 준비")
    assert has_core_signal("국회직 합격")
    assert not has_core_signal("서울시 7급 후기")
    assert has_intent_signal("최종합격 후기")
    assert not has_intent_signal("국회 도서관 위치")


def test_site_restriction():
    """Site restriction 동작을 검증한다."""
    out = site_restricted_variants("국회직 8급 합격후기")
    assert any("site:blog.naver.com" in x for x in out)
