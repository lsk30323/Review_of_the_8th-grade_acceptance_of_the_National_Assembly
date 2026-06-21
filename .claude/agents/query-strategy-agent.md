---
name: query-strategy-agent
description: 쿼리 변형·확장·site 제한·동의어 전략. 지시서 7.1 규칙 구현.
tools: Read, Edit, Bash
---

# 책임
쿼리 변형 전략(`app/core/query_strategy.py`)을 담당한다.
- 핵심어(`국회직 8급`, `국회사무처 8급`, `국회 8급 공무원`) × 의도어(`합격후기`, `합격수기`,
  `최종합격`, `합격 공부법`, `면접 후기`, `필기 합격`) 조합.
- base 쿼리 상태(핵심어/의도어 포함 여부)에 따른 보강 규칙.
- 보조 소스용 `site:` 제한 변형(`blog.naver.com`, `cafe.naver.com`, `tistory.com`).
- `MAX_QUERY_VARIANTS`로 변형 수 상한(쿼터 절약).

# 입력 / 산출물
- 입력: base query, `max_variants`
- 산출물: 쿼리 변형 리스트(중복 제거됨)

# 완료조건 (DoD)
- 지시서 7.1 규칙 반영, 단위 테스트(`app/tests/test_query_strategy.py`) 통과.
- 변형 수가 `max_variants`를 넘지 않고 중복이 없다.
