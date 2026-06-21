from app.core.text import strip_html


def test_strip_html_tags_and_entities():
    raw = "국회직 8급 <b>합격후기</b> &amp; 공부법 &lt;정리&gt;"
    assert strip_html(raw) == "국회직 8급 합격후기 & 공부법 <정리>"


def test_strip_html_collapses_whitespace():
    assert strip_html("  국회직   8급\n\t후기  ") == "국회직 8급 후기"


def test_strip_html_empty():
    assert strip_html("") == ""
    assert strip_html(None) == ""
