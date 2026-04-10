# Core README

## State Key 설계

| 상태 그룹 | 주요 key | 설명 |
|---|---|---|
| `Global` | `messages`, `query`, `analysis_scope`, `final_report`, `workflow_status` | 사용자 요청, 전체 분석 범위, 대화 히스토리, 최종 결과를 저장하는 전역 상태 |
| `Supervisor` | `next_agent`, `revision_count`, `missing_info_log` | 다음 호출 대상, 재시도 횟수, 반려/보완 사유를 관리하는 제어 상태 |
| `Retrieval` | `web_raw_results`, `rag_raw_chunks` | 웹 검색 결과와 RAG 검색 결과를 분리 저장하는 검색 상태 |
| `Draft` | `current_draft`, `trl_justification` | 보고서 초안과 작성 관련 보조 정보를 담는 작성 상태 |

설계 이유:
- **에이전트 간 데이터 오염을 막기 위해 상태를 분리 설계했다.**
- **Supervisor 제어 정보와 Retrieval 결과, Draft 결과를 분리하여 워크플로우의 안정성과 추적 가능성을 높였다.**

추가 의도:
- `Global`은 사용자 요청과 최종 결과를 유지
- `Supervisor`는 제어 로직만 담당
- `Retrieval`은 외부/내부 근거를 분리 저장
- `Draft`는 초안 생성 결과를 별도로 유지해 검증 및 재작성을 쉽게 함
