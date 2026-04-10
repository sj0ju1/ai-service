# Output README

## TRL 기반 분석 및 한계
최종 보고서는 경쟁사 기술 성숙도와 위협 수준을 **TRL 기반으로 추정**합니다.  
다만 **TRL 4~6 구간은 영업 비밀 특성상 공개 정보가 부족하므로 확정 판정이 아니라 ‘추정’ 영역**으로 다룹니다.

적용 원칙:
- 특허, 학회 발표, 채용 공고, 제품 발표, 고객 검증 공개 등 **간접 지표**를 활용해 TRL 4~6을 추정
- 공개 정보 부족 시 `정보 부족`, `판단 불가`, `추정 보류`로 명시
- 비교표에는 TRL 수치뿐 아니라 판단 근거와 주요 출처를 함께 기록

## 보고서 산출물 구조
최종 보고서는 아래 구조로 생성됩니다.

- `SUMMARY`
- `분석 배경`
- `분석 대상 기술 현황`
- `경쟁사 동향 분석`
- `분석 한계`
- `전략적 시사점`
- `추가 조사 필요 영역`
- `REFERENCE`

대표 산출물:
- `ai-mini_output_3반_배수정+안가은.md`
- `ai-mini_output_3반_배수정+안가은.pdf`

## Retrieval 평가 결과 (Hit Rate@K, MRR)
최종 선정 Retrieval은 `evaluate_rag.py`로 평가합니다.

| Metric | Value |
|---|---:|
| Hit Rate@1 | 0.0% |
| MRR@1 | 0.000 |
| Hit Rate@3 | 60.0% |
| MRR@3 | 0.267 |
| Hit Rate@5 | 100.0% |
| MRR@5 | 0.357 |

관련 파일:
- `retrieval_metrics.json`
- `retrieval_metrics.md`
- `retrieval_query_results.json`
