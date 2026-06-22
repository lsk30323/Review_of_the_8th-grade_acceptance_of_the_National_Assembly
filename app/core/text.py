"""텍스트 정규화 유틸.

네이버 검색 API의 title/description에는 <b> 태그와 HTML 엔티티가 섞여 온다.
정규화 단계에서 태그를 제거하고 엔티티를 디코드한다.
"""
from __future__ import annotations

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html(text: str | None) -> str:
    """HTML 태그 제거 + 엔티티 디코드 + 공백 정규화."""
    if not text:
        return ""
    no_tags = _TAG_RE.sub("", text)
    unescaped = html.unescape(no_tags)
    return _WS_RE.sub(" ", unescaped).strip()
