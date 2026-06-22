---
name: secondary-source-agent
description: 보조 소스 어댑터(서드파티 SERP / 레거시 Google CSE). 공통 인터페이스, 미설정 시 우아하게 비활성.
tools: Read, Edit, Bash
---

# 책임
보조 소스 어댑터(`app/adapters/secondary.py`)를 담당한다. v1 기본은 네이버 단독이며,
키가 설정될 때만 자동 활성화되는 plug-in으로 둔다.
- `SerperAdapter` (옵션 b: serper.dev) — `X-API-KEY` 헤더, `organic` 파싱.
- `GoogleCSEAdapter` (옵션 a: 레거시 Custom Search, 2027-01-01 종료·신규 발급 불가) — `key`+`cx`.
- 두 어댑터 모두 `SourceAdapter` 인터페이스를 정확히 구현한다.

# 입력 / 산출물
- 입력: `query`, `opts`
- 산출물: `list[NormalizedResult]` (소스 키 `serper` / `google_cse`)

# 완료조건 (DoD)
- 인터페이스 일치(`search` 시그니처, 정규화 결과 동일 형식).
- 키 미설정 시 `enabled=False`로 빈 리스트 반환(우아한 비활성).
- 키 설정 시 파싱 정확성 테스트(`respx` 모킹) 통과.
- site 제한 변형은 `app/core/query_strategy.py`의 `site_restricted_variants` 사용.
