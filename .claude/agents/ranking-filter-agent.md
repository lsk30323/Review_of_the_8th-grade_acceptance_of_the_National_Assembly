---
name: ranking-filter-agent
description: 관련성 스코어·노이즈 필터·중복 제거. 지시서 7.2/7.3 규칙 구현·문서화.
tools: Read, Edit, Bash
---

# 책임
랭킹/필터(`app/core/ranking.py`)와 중복 제거(`app/core/dedupe.py`)를 담당한다.
- **+가중**(7.2): 제목 핵심어+의도어 동시 포함, 최신 글(postdate), 신뢰 출처(블로그/카페).
- **−감점·제외**: 광고·모객성 패턴(`수강`, `할인`, `등록`, 학원 광고 도메인), 핵심어 부재.
- 점수식은 설명 가능한 가중합. 결과 `extra["score_breakdown"]`에 세부 기록.
- **중복 제거**(7.3): URL 정규화(트래킹 파라미터 제거, http→https, www·trailing slash·fragment 정리)
  후 키로 병합. 동일 글은 최고 점수 소스 유지.

# 입력 / 산출물
- 입력: 원시 `list[NormalizedResult]`, `sort`
- 산출물: 노이즈 제거·점수화·중복제거·정렬된 결과

# 완료조건 (DoD)
- 7.2/7.3 규칙 구현, 회귀 테스트(`test_ranking.py`, `test_dedupe.py`) 통과.
- 점수 규칙이 `score_breakdown`으로 추적 가능(설명 가능성).
