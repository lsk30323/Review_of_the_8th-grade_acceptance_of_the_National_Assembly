from app.core.text import strip_html


def test_strip_html_tags_and_entities():
    """Strip html tags and entities 동작을 검증한다."""
    raw = "국회직 8급 <b>합격후기</b> &amp; 공부법 &lt;정리&gt;"
    assert strip_html(raw) == "국회직 8급 합격후기 & 공부법 <정리>"


def test_strip_html_collapses_whitespace():
    """Strip html collapses whitespace 동작을 검증한다."""
    assert strip_html("  국회직   8급\n\t후기  ") == "국회직 8급 후기"


def test_strip_html_empty():
    """Strip html empty 동작을 검증한다."""
    assert strip_html("") == ""
    assert strip_html(None) == ""
