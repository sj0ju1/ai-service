# Agents README

## 아키텍처 선택 이유
이 프로젝트는 Distributed 구조가 아니라 **Supervisor 아키텍처**를 선택했습니다. 핵심 이유는 **검증-수정-보고서 생성 흐름을 중앙에서 통제하기 위해서**입니다.  
하위 에이전트끼리 직접 연결되지 않고, `Supervisor`가 각 에이전트를 호출한 뒤 결과를 검증하고, 필요하면 같은 에이전트 또는 다른 에이전트를 다시 호출합니다.

핵심 원칙:
- `Draft Agent`가 독단적으로 끝내지 않는다.
- `Supervisor`가 초안의 구조, 출처, 비교 균형, 전략적 시사점을 검토한다.
- 출처/링크/비교 근거가 부족하면 `Web Search Agent`부터 다시 호출한다.
- 최종 변환은 별도 Agent가 아니라 **`Formatting Node`** 로 처리한다.

## 에이전트 역할
- `Supervisor`: 전체 워크플로우를 통제하고 각 하위 에이전트의 산출물을 검증한 뒤 다음 단계를 결정한다.
- `Web Search Agent`: 최신 공개 신호를 다중 쿼리 기반으로 수집해 편향을 줄인 웹 근거를 확보한다.
- `RAG Agent`: JEDEC 문서와 논문, 기술 자료에서 질의 관련 근거를 검색해 구조화된 컨텍스트를 제공한다.
- `Draft Agent`: 수집된 근거를 바탕으로 TRL 기반 비교와 시사점을 포함한 보고서 초안을 작성한다.
- `Formatting Node`: 최종 승인된 Markdown 보고서를 PDF/문서 산출물로 변환한다.

## Supervisor 중심 흐름
1. `Supervisor`가 현재 state를 보고 다음 노드를 결정한다.
2. `Web Search Agent`와 `RAG Agent`가 각각 최신 웹 근거와 정적 기술 근거를 수집한다.
3. `Draft Agent`가 보고서 초안을 작성해 `Supervisor`에게 검토를 요청한다.
4. `Supervisor`는 반려 시 재작성 또는 재검색을 지시한다.
5. 승인된 초안만 `Formatting Node`로 전달된다.

## 구현 포인트
- 전달 로그를 명시적으로 출력해 `Supervisor -> Agent`, `Agent -> Supervisor` 흐름이 보이도록 설계
- `revision_count`를 기반으로 재시도 횟수 제한
- 구조 검증과 LLM 기반 품질 검증을 함께 사용
- 비교 균형, 출처 링크, 추가 조사 필요 영역 등 보고서 품질 기준을 rule-based로 먼저 검증
